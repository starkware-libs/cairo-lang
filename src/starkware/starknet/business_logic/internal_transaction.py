import asyncio
import dataclasses
import functools
import logging
from abc import abstractmethod
from dataclasses import field
from typing import ClassVar, Dict, List, Optional, Tuple, Type, cast

import marshmallow
import marshmallow_dataclass
from marshmallow_oneofschema import OneOfSchema

from services.everest.api.gateway.transaction import EverestTransaction
from services.everest.business_logic.internal_transaction import EverestInternalTransaction
from services.everest.business_logic.state import CarriedStateBase
from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.lang.vm.cairo_pie import ExecutionResources
from starkware.cairo.lang.vm.relocatable import RelocatableValue
from starkware.cairo.lang.vm.security import SecurityError
from starkware.cairo.lang.vm.utils import ResourcesError
from starkware.cairo.lang.vm.vm_exceptions import HintException, VmException, VmExceptionBase
from starkware.starknet.business_logic.internal_transaction_interface import (
    InternalStateTransaction,
)
from starkware.starknet.business_logic.state import BlockInfo, CarriedState, StateSelector
from starkware.starknet.business_logic.state_objects import (
    ContractCarriedState,
    ContractDefinitionFact,
    ContractState,
)
from starkware.starknet.business_logic.transaction_execution_objects import (
    ContractCall,
    TransactionExecutionContext,
    TransactionExecutionInfo,
)
from starkware.starknet.core.os import os_utils, syscall_utils
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starknet.public.abi import (
    DEFAULT_ENTRY_POINT_SELECTOR,
    SYSCALL_PTR_OFFSET,
    get_selector_from_name,
)
from starkware.starknet.services.api.contract_definition import (
    ContractDefinition,
    ContractEntryPoint,
    EntryPointType,
)
from starkware.starknet.services.api.gateway.contract_address import calculate_contract_address
from starkware.starknet.services.api.gateway.transaction import Deploy, InvokeFunction, Transaction
from starkware.starknet.services.api.gateway.transaction_hash import (
    TransactionHashPrefix,
    calculate_deploy_transaction_hash,
    calculate_transaction_hash_common,
)
from starkware.starknet.storage.starknet_storage import BusinessLogicStarknetStorage
from starkware.starkware_utils.config_base import Config
from starkware.starkware_utils.error_handling import (
    StarkException,
    stark_assert,
    wrap_with_stark_exception,
)

logger = logging.getLogger(__name__)


class InternalTransaction(InternalStateTransaction, EverestInternalTransaction):
    """
    StarkNet internal transaction base class.
    """

    hash_value: int

    # Class variables.

    # A mapping of external (cls.related_external_cls) to internal type.
    # Used for creating an internal transaction from an external one (and vice versa) using only
    # base classes.
    external_to_internal_cls: ClassVar[Dict[Type[Transaction], Type["InternalTransaction"]]] = {}

    @property
    @classmethod
    @abstractmethod
    def tx_type(cls) -> TransactionType:
        """
        Returns the corresponding TransactionType enum. Used in TransacactionSchema.
        Subclasses should define it as a class variable.
        """

    @property
    @classmethod
    @abstractmethod
    def related_external_cls(cls) -> Type[Transaction]:
        """
        Returns the corresponding external transaction class. Used in converting between
        external/internal types.
        Subclasses should define it as a class variable.
        """

    @property
    def external_name(self) -> str:
        return self.related_external_cls.__name__

    @classmethod
    def __init_subclass__(cls, **kwargs):
        """
        Registers the related external type class variable to the external-to-internal class
        mapping.
        """
        super().__init_subclass__(**kwargs)  # type: ignore[call-arg]

        # Record only the first class with this related_external_type.
        recorded_cls = InternalTransaction.external_to_internal_cls.setdefault(
            cls.related_external_cls, cls
        )

        # Check that this class is indeed that class or a subclass of it.
        assert issubclass(cls, recorded_cls)

    @abstractmethod
    def to_external(self) -> Transaction:
        """
        Returns an external transaction genearated based on an internal one.
        """

    @classmethod
    def from_external(
        cls, external_tx: EverestTransaction, general_config: Config
    ) -> "InternalTransaction":
        """
        Returns an internal transaction genearated based on an external one.
        """
        # Downcast arguments to application-specific types.
        assert isinstance(external_tx, Transaction)
        assert isinstance(general_config, StarknetGeneralConfig)

        internal_cls = InternalTransaction.external_to_internal_cls.get(type(external_tx))
        if internal_cls is None:
            raise NotImplementedError(f"Unsupported transaction type {type(external_tx).__name__}.")

        return internal_cls._specific_from_external(
            external_tx=external_tx, general_config=general_config
        )

    @classmethod
    @abstractmethod
    def _specific_from_external(
        cls, external_tx: Transaction, general_config: StarknetGeneralConfig
    ) -> "InternalTransaction":
        """
        Returns an internal transaction genearated based on an external one, where the input
        arguments are downcasted to application-specific types.
        """

    def verify_signatures(self):
        """
        Verifies the signatures in the transaction.
        Currently not implemented by StarkNet transactions.
        """

    async def apply_state_updates(
        self, state: CarriedStateBase, general_config: Config
    ) -> TransactionExecutionInfo:
        # super().apply_state_updates calls InternalStateTransaction.apply_state_updates
        # that calls self._apply_specific_state_updates and therefore does not return None.
        tx_execution_info = await super().apply_state_updates(
            state=state, general_config=general_config
        )
        assert isinstance(tx_execution_info, TransactionExecutionInfo)
        return tx_execution_info

    @abstractmethod
    async def _apply_specific_state_updates(
        self, state: CarriedState, general_config: StarknetGeneralConfig
    ) -> TransactionExecutionInfo:
        pass

    def _synchronous_apply_specific_state_updates(
        self,
        state: CarriedState,
        general_config: StarknetGeneralConfig,
        loop: asyncio.AbstractEventLoop,
        tx_execution_context: TransactionExecutionContext,
    ) -> TransactionExecutionInfo:
        pass


class SyntheticTransaction(InternalStateTransaction):
    """
    StarkNet synthetic transaction base class.
    These transactions appear in the beginning of a batch,
    and are used to update the state,
    in a way that is not initiated by the user.
    See for example, InitializeBlockInfo.
    """

    @property
    @classmethod
    @abstractmethod
    def tx_type(cls) -> TransactionType:
        """
        Returns the corresponding TransactionType enum. Used in TransacactionSchema.
        Subclasses should define it as a class variable.
        """


@marshmallow_dataclass.dataclass(frozen=True)
class InitializeBlockInfo(SyntheticTransaction):
    """
    A synthetic transaction that initializes entire block-related information.
    """

    block_info: BlockInfo
    tx_type: ClassVar[TransactionType] = TransactionType.INITIALIZE_BLOCK_INFO

    async def _apply_specific_state_updates(
        self, state: CarriedStateBase, general_config: Config
    ) -> Optional[TransactionExecutionInfo]:
        # Downcast arguments to application-specific types.
        assert isinstance(general_config, StarknetGeneralConfig)
        assert isinstance(state, CarriedState)

        # Validate progress is legal.
        next_block_info = self.block_info
        state.block_info.validate_legal_progress(next_block_info=next_block_info)

        # Update entire block-related information.
        state.block_info = next_block_info

        return None

    def get_state_selector(self, general_config: Config) -> StateSelector:
        return StateSelector.empty()

    def _synchronous_apply_specific_state_updates(
        self,
        state: CarriedState,
        general_config: StarknetGeneralConfig,
        loop: asyncio.AbstractEventLoop,
        tx_execution_context: TransactionExecutionContext,
    ) -> Optional[TransactionExecutionInfo]:
        """
        This method is not supported.
        """
        raise NotImplementedError


@marshmallow_dataclass.dataclass(frozen=True)
class InternalDeploy(InternalTransaction):
    """
    Represents an internal transaction in the StarkNet network that is a deployment of a Cairo
    contract.
    """

    contract_address: int = field(metadata=fields.contract_address_metadata)
    contract_address_salt: int = field(metadata=fields.contract_address_salt_metadata)
    contract_definition: ContractDefinition
    constructor_calldata: List[int] = field(metadata=fields.call_data_metadata)

    # A unique identifier of the transaction in the StarkNet network.
    hash_value: int = field(metadata=fields.transaction_hash_metadata)

    # Class variables.
    tx_type: ClassVar[TransactionType] = TransactionType.DEPLOY
    related_external_cls: ClassVar[Type[Transaction]] = Deploy
    n_cairo_steps_estimation: ClassVar[int] = 100
    # The size of the header of the deployment information that is outputted by the StarkNet OS.
    deployment_info_header_size: ClassVar[int] = 3

    @classmethod
    def create(
        cls,
        contract_address_salt: int,
        contract_definition: ContractDefinition,
        constructor_calldata: List[int],
        general_config,
    ):
        contract_address = calculate_contract_address(
            salt=contract_address_salt,
            contract_definition=contract_definition,
            constructor_calldata=constructor_calldata,
            caller_address=0,
        )
        return cls(
            contract_address=contract_address,
            contract_address_salt=contract_address_salt,
            contract_definition=contract_definition,
            constructor_calldata=constructor_calldata,
            hash_value=calculate_deploy_transaction_hash(
                contract_address=contract_address,
                constructor_calldata=constructor_calldata,
                chain_id=general_config.chain_id.value,
            ),
        )

    @classmethod
    def _specific_from_external(
        cls, external_tx: Transaction, general_config: StarknetGeneralConfig
    ) -> "InternalDeploy":
        assert isinstance(external_tx, Deploy)
        return cls.create(
            contract_address_salt=external_tx.contract_address_salt,
            contract_definition=external_tx.contract_definition,
            constructor_calldata=external_tx.constructor_calldata,
            general_config=general_config,
        )

    def to_external(self) -> Deploy:
        return Deploy(
            contract_address_salt=self.contract_address_salt,
            contract_definition=self.contract_definition,
            constructor_calldata=self.constructor_calldata,
        )

    def get_state_selector(self, general_config: Config) -> StateSelector:
        """
        Returns the state selector of the transaction (i.e., subset of state commitment tree leaves
        it affects).
        """
        # Downcast arguments to application-specific types.
        assert isinstance(general_config, StarknetGeneralConfig)

        return StateSelector(contract_addresses={self.contract_address})

    async def _apply_specific_state_updates(
        self, state: CarriedState, general_config: StarknetGeneralConfig
    ) -> TransactionExecutionInfo:
        """
        Adds the deployed contract to the global commitment tree state.
        """
        # Extract pre-fetched contract object from carried state.
        contract_carried_state = state.contract_states[self.contract_address]
        contract_state = contract_carried_state.state
        stark_assert(
            not contract_state.initialized,
            code=StarknetErrorCode.CONTRACT_ADDRESS_UNAVAILABLE,
            message=(
                f"Requested contract address {self.contract_address} is unavailable for "
                f"deployment."
            ),
        )

        self.contract_definition.validate()

        # Set contract definition fact to facts storage.
        contract_definition_fact = ContractDefinitionFact(
            contract_definition=self.contract_definition
        )
        contract_hash = await contract_definition_fact.set_fact(ffc=state.ffc)
        state.contract_definitions[contract_hash] = self.contract_definition

        # Create updated contract state.
        newly_deployed_contract_state = await ContractState.create(
            contract_hash=contract_hash,
            storage_commitment_tree=contract_state.storage_commitment_tree,
        )
        state.contract_states[self.contract_address] = ContractCarriedState(
            state=newly_deployed_contract_state, storage_updates={}
        )

        # Update Cairo usage.
        cairo_usage = dataclasses.replace(
            ExecutionResources.empty(), n_steps=self.n_cairo_steps_estimation
        )
        state.cairo_usage += cairo_usage

        return await self.invoke_constructor(state=state, general_config=general_config)

    async def invoke_constructor(
        self, state: CarriedState, general_config: StarknetGeneralConfig
    ) -> TransactionExecutionInfo:
        if len(self.contract_definition.entry_points_by_type[EntryPointType.CONSTRUCTOR]) == 0:
            stark_assert(
                len(self.constructor_calldata) == 0,
                code=StarknetErrorCode.TRANSACTION_FAILED,
                message="Cannot pass calldata to a contract with no constructor.",
            )
            return TransactionExecutionInfo.create(
                call_info=ContractCall.empty(to_address=self.contract_address)
            )

        tx = InternalInvokeFunction(
            contract_address=self.contract_address,
            code_address=self.contract_address,
            entry_point_selector=get_selector_from_name("constructor"),
            entry_point_type=EntryPointType.CONSTRUCTOR,
            calldata=self.constructor_calldata,
            signature=[],
            hash_value=0,
            caller_address=0,
        )

        return await tx._apply_specific_state_updates(state=state, general_config=general_config)

    def _synchronous_apply_specific_state_updates(
        self,
        state: CarriedState,
        general_config: StarknetGeneralConfig,
        loop: asyncio.AbstractEventLoop,
        tx_execution_context: TransactionExecutionContext,
    ) -> TransactionExecutionInfo:
        raise NotImplementedError


@marshmallow_dataclass.dataclass(frozen=True)
class InternalInvokeFunction(InternalTransaction):
    """
    Represents an internal transaction in the StarkNet network that is an invocation of a Cairo
    contract function.
    """

    # For fields that are shared with InvokeFunction, see documentation there.
    contract_address: int = field(metadata=fields.contract_address_metadata)
    # The address that holds the code to execute.
    # It may differ from contract_address in the case of delegate call.
    code_address: int = field(metadata=fields.contract_address_metadata)
    entry_point_selector: int = field(metadata=fields.entry_point_selector_metadata)
    # The decorator type of the called function. Note that a single function may be decorated with
    # multiple decorators and this member specifies which one.
    entry_point_type: EntryPointType
    calldata: List[int] = field(metadata=fields.call_data_metadata)
    signature: List[int] = field(metadata=fields.signature_metadata)
    # A unique identifier of the transaction in the StarkNet network.
    hash_value: int = field(metadata=fields.transaction_hash_metadata)
    # Caller address is zero for external calls and the caller (contract) address for composed ones.
    caller_address: int = field(metadata=fields.caller_address_metadata)

    # A unique nonce, added by the StarkNet core contract on L1.
    # This nonce is used to make the hash_value of transactions that service L1 messages unique.
    # This field may be set only when entry_point_type is EntryPointType.L1_HANDLER.
    nonce: Optional[int] = field(metadata=fields.optional_nonce_metadata, default=None)

    # Class variables.
    tx_type: ClassVar[TransactionType] = TransactionType.INVOKE_FUNCTION
    related_external_cls: ClassVar[Type[Transaction]] = InvokeFunction

    @classmethod
    def create_for_testing(
        cls,
        contract_address: int,
        calldata: List[int],
        entry_point_selector: int,
        code_address: Optional[int] = None,
        entry_point_type: Optional[EntryPointType] = None,
        signature: Optional[List[int]] = None,
        hash_value: Optional[int] = None,
        caller_address: Optional[int] = None,
        nonce: Optional[int] = None,
    ):
        return cls(
            contract_address=contract_address,
            code_address=contract_address if code_address is None else code_address,
            entry_point_selector=entry_point_selector,
            entry_point_type=(
                EntryPointType.EXTERNAL if entry_point_type is None else entry_point_type
            ),
            calldata=calldata,
            signature=[] if signature is None else signature,
            hash_value=0 if hash_value is None else hash_value,
            caller_address=0 if caller_address is None else caller_address,
            nonce=nonce,
        )

    @classmethod
    def _specific_from_external(
        cls, external_tx: Transaction, general_config: StarknetGeneralConfig
    ) -> "InternalInvokeFunction":
        assert isinstance(external_tx, InvokeFunction)
        return cls.create(
            general_config=general_config,
            contract_address=external_tx.contract_address,
            entry_point_selector=external_tx.entry_point_selector,
            entry_point_type=EntryPointType.EXTERNAL,
            calldata=external_tx.calldata,
            signature=external_tx.signature,
            nonce=None,
        )

    @classmethod
    def create(
        cls,
        general_config: StarknetGeneralConfig,
        contract_address: int,
        entry_point_selector: int,
        entry_point_type: EntryPointType,
        calldata: List[int],
        signature: List[int],
        nonce: Optional[int],
        # The caller_address of an external transaction or L1 handler is always 0.
        # The caller_address is passed as paramater to allow the testing framework to initiate
        # transactions with a user specified caller_address.
        caller_address: int = 0,
    ) -> "InternalInvokeFunction":
        if entry_point_type is EntryPointType.EXTERNAL:
            tx_hash_prefix = TransactionHashPrefix.INVOKE
            assert nonce is None, "An InvokeFunction transaction cannot have a nonce."
            additional_data = []
        elif entry_point_type is EntryPointType.L1_HANDLER:
            tx_hash_prefix = TransactionHashPrefix.L1_HANDLER
            assert nonce is not None, "An L1 handler transaction should must have a nonce."
            additional_data = [nonce]
        else:
            raise NotImplementedError(f"Entry point type {entry_point_type.name} is not supported.")

        hash_value = calculate_transaction_hash_common(
            tx_hash_prefix=tx_hash_prefix,
            contract_address=contract_address,
            entry_point_selector=entry_point_selector,
            calldata=calldata,
            chain_id=general_config.chain_id.value,
            additional_data=additional_data,
        )

        return cls(
            contract_address=contract_address,
            code_address=contract_address,
            entry_point_selector=entry_point_selector,
            entry_point_type=entry_point_type,
            calldata=calldata,
            signature=signature,
            hash_value=hash_value,
            caller_address=caller_address,
            nonce=nonce,
        )

    def to_external(self) -> InvokeFunction:
        assert self.entry_point_type is EntryPointType.EXTERNAL, (
            "It it illegal to convert to external an InternalInvokeFunction of a non-external "
            f"Cairo contract function; got: {self.entry_point_type.name}."
        )
        assert self.code_address == self.contract_address, (
            "It it illegal to convert to external an InternalInvokeFunction with "
            f"code_address ({self.code_address}) != contract_address ({self.contract_address})."
        )

        return InvokeFunction(
            contract_address=self.contract_address,
            entry_point_selector=self.entry_point_selector,
            calldata=self.calldata,
            signature=self.signature,
        )

    def get_state_selector(self, general_config: Config) -> StateSelector:
        """
        Returns the state selector of the transaction (i.e., subset of state commitment tree leaves
        it affects).
        """
        # Downcast arguments to application-specific types.
        assert isinstance(general_config, StarknetGeneralConfig)

        return StateSelector(contract_addresses={self.contract_address, self.code_address})

    async def _apply_specific_state_updates(
        self, state: CarriedState, general_config: StarknetGeneralConfig
    ) -> TransactionExecutionInfo:
        """
        Applies self to 'state' by running _synchronous_apply_specific_state_updates.
        This is the asynchronous version of the method below.
        """
        # Pass the running loop before entering to it. It will be used to run asynchronous
        # tasks, such as fetching data from storage.
        loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        _synchronous_apply_specific_state_updates = functools.partial(
            self._synchronous_apply_specific_state_updates,
            state=state,
            general_config=general_config,
            loop=loop,
            tx_execution_context=TransactionExecutionContext.create(
                n_steps=general_config.invoke_tx_max_n_steps
            ),
        )

        execution_info = await loop.run_in_executor(
            executor=None,  # Runs on the default executor.
            func=_synchronous_apply_specific_state_updates,
        )

        return execution_info

    def _synchronous_apply_specific_state_updates(
        self,
        state: CarriedState,
        general_config: StarknetGeneralConfig,
        loop: asyncio.AbstractEventLoop,
        tx_execution_context: TransactionExecutionContext,
    ) -> TransactionExecutionInfo:
        """
        Runs the selected entry point with the given calldata in the contract specified by the
        transaction.
        The information collected from this run (number of steps required, modifications to the
        contract storage, etc.) is saved on the carried state argument.
        In addition, builds and return the specific transaction execution information, to be used
        by the StarkNet OS run in the GpsAmbassador, and by the FeederGateway.

        This function also runs inside Cairo hints (when processing internal contract calls),
        thus must be synchronous.
        """
        previous_cairo_usage = state.cairo_usage

        runner, syscall_handler = self._run(
            state=state,
            general_config=general_config,
            loop=loop,
            caller_address=self.caller_address,
            tx_execution_context=tx_execution_context,
        )

        # Apply modifications to the contract storage.
        state.update_contract_storage(
            contract_address=self.contract_address,
            modifications=syscall_handler.starknet_storage.get_modifications(),
        )

        # Update resources usage (for bouncer).
        state.cairo_usage += runner.get_execution_resources()

        # Build transaction execution info.
        contract_call_cairo_usage = state.cairo_usage - previous_cairo_usage
        call_info = ContractCall(
            from_address=self.caller_address,
            to_address=self.contract_address,
            code_address=self.code_address,
            entry_point_selector=self.entry_point_selector,
            entry_point_type=self.entry_point_type,
            calldata=self.calldata,
            signature=self.signature,
            cairo_usage=contract_call_cairo_usage,
            events=syscall_handler.events,
            l2_to_l1_messages=[],
            internal_call_responses=syscall_handler.internal_call_responses,
            storage_read_values=syscall_handler.starknet_storage.read_values,
            storage_accessed_addresses=syscall_handler.starknet_storage.accessed_addresses,
        )

        return TransactionExecutionInfo(
            call_info=call_info,
            l2_to_l1_messages=syscall_handler.l2_to_l1_messages,
            retdata=self._get_return_values(runner=runner),
            internal_calls=syscall_handler.internal_calls,
        )

    def _run(
        self,
        state: CarriedState,
        general_config: StarknetGeneralConfig,
        loop: asyncio.AbstractEventLoop,
        caller_address: int,
        tx_execution_context: TransactionExecutionContext,
    ) -> Tuple[CairoFunctionRunner, syscall_utils.BusinessLogicSysCallHandler]:
        """
        Runs the selected entry point with the given calldata in the code of the contract deployed
        at self.code_address.
        The execution is done in the context (e.g., storage) of the contract at
        self.contract_address.
        Returns the corresponding CairoFunctionRunner and BusinessLogicSysCallHandler in order to
        retrieve the execution information.
        """
        # Extract pre-fetched contract code from carried state.
        code_contract_state = state.contract_states[self.code_address].state
        code_contract_state.assert_initialized(contract_address=self.code_address)

        # Prepare input for Cairo function runner.
        contract_definition = state.contract_definitions[code_contract_state.contract_hash]
        contract_definition.validate()
        entry_point = self._get_selected_entry_point(contract_definition=contract_definition)

        # Run the specified contract entry point with given calldata.
        with wrap_with_stark_exception(code=StarknetErrorCode.SECURITY_ERROR):
            runner = CairoFunctionRunner(program=contract_definition.program, layout="all")
        os_context = os_utils.prepare_os_context(runner=runner)

        # Extract pre-fetched contract state from carried state.
        pre_run_contract_carried_state = state.contract_states[self.contract_address]
        contract_state = pre_run_contract_carried_state.state
        contract_state.assert_initialized(contract_address=self.contract_address)

        starknet_storage = BusinessLogicStarknetStorage(
            commitment_tree=contract_state.storage_commitment_tree,
            ffc=state.ffc,
            # Note that pending_modifications might be modified during the run as a result of an
            # internal call.
            pending_modifications=pre_run_contract_carried_state.storage_updates.copy(),
            loop=loop,
        )

        initial_syscall_ptr = cast(RelocatableValue, os_context[SYSCALL_PTR_OFFSET])
        syscall_handler = syscall_utils.BusinessLogicSysCallHandler(
            tx_execution_context=tx_execution_context,
            state=state,
            caller_address=caller_address,
            contract_address=self.contract_address,
            signature=self.signature,
            starknet_storage=starknet_storage,
            general_config=general_config,
            initial_syscall_ptr=initial_syscall_ptr,
        )

        # Positional arguments are passed to *args in the 'run_from_entrypoint' function.

        entry_points_args = [
            self.entry_point_selector,
            os_context,
            len(self.calldata),
            self.calldata,
        ]

        try:
            runner.run_from_entrypoint(
                entry_point.offset,
                *entry_points_args,
                hint_locals={
                    "__storage": starknet_storage,
                    "syscall_handler": syscall_handler,
                },
                static_locals={
                    "__find_element_max_size": 2 ** 20,
                    "__squash_dict_max_size": 2 ** 20,
                    "__keccak_max_size": 2 ** 20,
                },
                run_resources=tx_execution_context.run_resources,
                verify_secure=True,
            )
        except VmException as exception:
            code = StarknetErrorCode.TRANSACTION_FAILED
            if isinstance(exception.inner_exc, HintException):
                hint_exception = exception.inner_exc

                if isinstance(hint_exception.inner_exc, syscall_utils.HandlerException):
                    stark_exception = hint_exception.inner_exc.stark_exception
                    code = stark_exception.code
                    called_contract_address = hint_exception.inner_exc.called_contract_address
                    message_prefix = (
                        f"Error in the called contract ({hex(called_contract_address)}):\n"
                    )
                    # Override python's traceback and keep the Cairo one of the inner exception.
                    exception.notes = [message_prefix + str(stark_exception.message)]

            if isinstance(exception.inner_exc, ResourcesError):
                code = StarknetErrorCode.OUT_OF_RESOURCES

            raise StarkException(code=code, message=str(exception))
        except VmExceptionBase as exception:
            raise StarkException(code=StarknetErrorCode.TRANSACTION_FAILED, message=str(exception))
        except SecurityError as exception:
            raise StarkException(code=StarknetErrorCode.SECURITY_ERROR, message=str(exception))
        except Exception:
            logger.error("Got an unexpected exception.", exc_info=True)
            raise StarkException(
                code=StarknetErrorCode.UNEXPECTED_FAILURE,
                message="Got an unexpected exception during the execution of the transaction.",
            )

        # Complete handler validations.
        os_utils.validate_and_process_os_context(
            runner=runner,
            syscall_handler=syscall_handler,
            initial_os_context=os_context,
        )

        # The OS touches all the arguments so they shouldn't be counted as holes.
        assert runner.accessed_addresses is not None
        # When execution starts the stack holds entry_points_args + [ret_fp, ret_pc].
        args_ptr = runner.initial_fp - (len(entry_points_args) + 2)
        for i in range(len(entry_points_args)):
            runner.accessed_addresses.add(args_ptr + i)

        return runner, syscall_handler

    def _get_selected_entry_point(
        self, contract_definition: ContractDefinition
    ) -> ContractEntryPoint:
        """
        Returns the entry point with selector corresponding with self.entry_point_selector.
        """

        entry_points = contract_definition.entry_points_by_type[self.entry_point_type]
        filtered_entry_points = list(
            filter(
                lambda ep: ep.selector == self.entry_point_selector,
                entry_points,
            )
        )

        if len(filtered_entry_points) == 0 and len(entry_points) > 0:
            ep0 = entry_points[0]
            if ep0.selector == DEFAULT_ENTRY_POINT_SELECTOR:
                return ep0

        # Non-unique entry points are not possible in a ContractDefinition object, thus
        # len(filtered_entry_points) <= 1.
        stark_assert(
            len(filtered_entry_points) == 1,
            code=StarknetErrorCode.ENTRY_POINT_NOT_FOUND_IN_CONTRACT,
            message=(
                f"Entry point {self.entry_point_selector} not found in contract with address "
                f"{self.contract_address}."
            ),
        )

        (entry_point,) = filtered_entry_points
        return entry_point

    async def call(self, state: CarriedState, general_config: StarknetGeneralConfig) -> List[int]:
        """
        Runs the selected entry point with the given calldata in the contract specified by the
        transaction.
        Returns the return data.
        Note that this function modifies the state.
        """
        # Pass the running loop before entering to it. It will be used to run asynchronous
        # tasks, such as fetching data from storage.
        loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        _run = functools.partial(
            self._run,
            state=state,
            general_config=general_config,
            loop=loop,
            caller_address=self.caller_address,
            tx_execution_context=TransactionExecutionContext.create(
                n_steps=general_config.invoke_tx_max_n_steps
            ),
        )

        runner, _ = await loop.run_in_executor(executor=None, func=_run)
        return self._get_return_values(runner=runner)

    def _get_return_values(self, runner: CairoFunctionRunner) -> List[int]:
        with wrap_with_stark_exception(
            code=StarknetErrorCode.INVALID_RETURN_DATA,
            message="Error extracting return data in call().",
            logger=logger,
            exception_types=[Exception],
        ):
            ret_data_size, ret_data_ptr = runner.get_return_values(2)
            values = runner.memory.get_range(ret_data_ptr, ret_data_size)

        stark_assert(
            all(isinstance(value, int) for value in values),
            code=StarknetErrorCode.INVALID_RETURN_DATA,
            message="Return data expected to be non-relocatable.",
        )

        return cast(List[int], values)


class InternalTransactionSchema(OneOfSchema):
    """
    Schema for transaction.
    OneOfSchema adds a "type" field.

    Allows the use of load / dump of different transaction type data directly via the
    Transaction class (e.g., InternalTransaction.load(invoke_function_dict), where
    {"type": "INVOKE_FUNCTION"} is in invoke_function_dict, will produce an InternalInvokeFunction
    object).
    """

    type_schemas: Dict[str, Type[marshmallow.Schema]] = {
        TransactionType.DEPLOY.name: InternalDeploy.Schema,
        TransactionType.INVOKE_FUNCTION.name: InternalInvokeFunction.Schema,
    }

    def get_obj_type(self, obj: Transaction) -> str:
        return obj.tx_type.name


InternalTransaction.Schema = InternalTransactionSchema


class SyntheticTransactionSchema(OneOfSchema):
    """
    Schema for synthetic transaction.
    OneOfSchema adds a "type" field.

    Allows the use of load / dump of different transaction type data directly via the
    Transaction class.
    """

    type_schemas: Dict[str, Type[marshmallow.Schema]] = {
        TransactionType.INITIALIZE_BLOCK_INFO.name: InitializeBlockInfo.Schema
    }

    def get_obj_type(self, obj: SyntheticTransaction) -> str:
        return obj.tx_type.name


SyntheticTransaction.Schema = SyntheticTransactionSchema
