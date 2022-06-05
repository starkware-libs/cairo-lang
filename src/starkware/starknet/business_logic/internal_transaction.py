import dataclasses
import logging
from abc import abstractmethod
from dataclasses import field
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type

import marshmallow
import marshmallow_dataclass
from marshmallow_oneofschema import OneOfSchema

from services.everest.api.gateway.transaction import EverestTransaction
from services.everest.business_logic.internal_transaction import EverestInternalTransaction
from services.everest.business_logic.state import CarriedStateBase
from starkware.cairo.lang.vm.cairo_pie import ExecutionResources
from starkware.python.utils import to_bytes
from starkware.starknet.business_logic.execution.execute_entry_point import ExecuteEntryPoint
from starkware.starknet.business_logic.execution.objects import (
    CallInfo,
    CallType,
    TransactionExecutionContext,
    TransactionExecutionInfo,
)
from starkware.starknet.business_logic.internal_transaction_interface import (
    InternalStateTransaction,
)
from starkware.starknet.business_logic.state.state import BlockInfo, CarriedState, StateSelector
from starkware.starknet.business_logic.transaction_fee import calculate_tx_fee, execute_fee_transfer
from starkware.starknet.business_logic.utils import (
    preprocess_invoke_function_fields,
    read_contract_class,
    validate_version,
    write_contract_class_fact,
)
from starkware.starknet.core.os.class_hash import compute_class_hash
from starkware.starknet.core.os.contract_address.contract_address import (
    calculate_contract_address_from_hash,
)
from starkware.starknet.core.os.syscall_utils import initialize_contract_state
from starkware.starknet.core.os.transaction_hash.transaction_hash import (
    calculate_declare_transaction_hash,
    calculate_deploy_transaction_hash,
    calculate_transaction_hash_common,
)
from starkware.starknet.definitions import constants, fields
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starknet.public import abi as starknet_abi
from starkware.starknet.services.api.contract_class import (
    CONSTRUCTOR_SELECTOR,
    ContractClass,
    EntryPointType,
)
from starkware.starknet.services.api.gateway.transaction import (
    DECLARE_SENDER_ADDRESS,
    Declare,
    Deploy,
    InvokeFunction,
    Transaction,
)
from starkware.starkware_utils.config_base import Config
from starkware.starkware_utils.error_handling import stark_assert, stark_assert_eq
from starkware.storage.storage import FactFetchingContext, Storage

logger = logging.getLogger(__name__)


# Mypy has a problem with dataclasses that contain unimplemented abstract methods.
# See https://github.com/python/mypy/issues/5374 for details on this problem.
@marshmallow_dataclass.dataclass(frozen=True)  # type: ignore[misc]
class InternalTransaction(InternalStateTransaction, EverestInternalTransaction):
    """
    StarkNet internal transaction base class.
    """

    # The version of the transaction. It is fixed (currently, 0) in the OS, and should be
    # signed by the account contract.
    # This field allows invalidating old transactions, whenever the meaning of the other
    # transaction fields is changed (in the OS).
    version: int = field(metadata=fields.tx_version_metadata)
    # A unique identifier of the transaction in the StarkNet network.
    hash_value: int = field(metadata=fields.transaction_hash_metadata)

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
            cls.related_external_cls, cls  # type: ignore[arg-type]
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
        state.block_info.validate_legal_progress(next_block_info=self.block_info)

        # Update entire block-related information.
        state.block_info = self.block_info

        return None

    def get_state_selector(self, general_config: Config) -> StateSelector:
        return StateSelector.empty()


@marshmallow_dataclass.dataclass(frozen=True)
class InternalDeclare(InternalTransaction):
    """
    Represents an internal transaction in the StarkNet network that is a declaration of a Cairo
    contract class.
    """

    class_hash: bytes = field(metadata=fields.class_hash_metadata)
    sender_address: int = field(metadata=fields.contract_address_metadata)
    max_fee: int = field(metadata=fields.fee_metadata)
    signature: List[int] = field(metadata=fields.signature_metadata)
    nonce: int = field(metadata=fields.nonce_metadata)

    # Class variables.
    tx_type: ClassVar[TransactionType] = TransactionType.DECLARE
    related_external_cls: ClassVar[Type[Transaction]] = Declare

    def __post_init__(self):
        super().__post_init__()

        stark_assert_eq(
            DECLARE_SENDER_ADDRESS,
            self.sender_address,
            code=StarknetErrorCode.OUT_OF_RANGE_CONTRACT_ADDRESS,
            message=(
                "The sender_address field in Declare transactions must be"
                f"{DECLARE_SENDER_ADDRESS}."
            ),
        )
        stark_assert_eq(
            0,
            self.max_fee,
            code=StarknetErrorCode.OUT_OF_RANGE_FEE,
            message="The max_fee field in Declare transactions must be 0.",
        )
        stark_assert_eq(
            0,
            self.nonce,
            code=StarknetErrorCode.OUT_OF_RANGE_NONCE,
            message="The nonce field in Declare transactions must be 0.",
        )

    @classmethod
    def create(
        cls,
        contract_class: ContractClass,
        chain_id: int,
        sender_address: int,
        max_fee: int,
        version: int,
        signature: List[int],
        nonce: int,
    ):
        validate_version(version=version, only_query=False)

        class_hash = compute_class_hash(contract_class=contract_class)
        return cls(
            class_hash=to_bytes(class_hash),
            sender_address=sender_address,
            max_fee=max_fee,
            version=version,
            signature=signature,
            nonce=nonce,
            hash_value=calculate_declare_transaction_hash(
                contract_class=contract_class,
                chain_id=chain_id,
                sender_address=sender_address,
                max_fee=max_fee,
                version=version,
            ),
        )

    @classmethod
    async def create_for_testing(
        cls,
        ffc: FactFetchingContext,
        contract_class: ContractClass,
        chain_id: Optional[int] = None,
    ) -> "InternalDeclare":
        """
        Creates an InternalDeclare transaction and writes its contract class to the DB.
        This constructor should only be used in tests.
        """
        await write_contract_class_fact(contract_class=contract_class, ffc=ffc)
        return InternalDeclare.create(
            contract_class=contract_class,
            chain_id=0 if chain_id is None else chain_id,
            sender_address=DECLARE_SENDER_ADDRESS,
            max_fee=0,
            version=constants.TRANSACTION_VERSION,
            signature=[],
            nonce=0,
        )

    @classmethod
    def _specific_from_external(
        cls, external_tx: Transaction, general_config: StarknetGeneralConfig
    ) -> "InternalDeclare":
        assert isinstance(external_tx, Declare)
        return cls.create(
            contract_class=external_tx.contract_class,
            chain_id=general_config.chain_id.value,
            sender_address=external_tx.sender_address,
            max_fee=external_tx.max_fee,
            version=external_tx.version,
            signature=external_tx.signature,
            nonce=external_tx.nonce,
        )

    def to_external(self) -> Declare:
        raise NotImplementedError("Cannot convert internal declare transaction to external object.")

    def get_state_selector(self, general_config: Config) -> StateSelector:
        return StateSelector.empty()

    async def _apply_specific_state_updates(
        self, state: CarriedState, general_config: StarknetGeneralConfig
    ) -> TransactionExecutionInfo:
        # Declare transaction does not change the state.
        return TransactionExecutionInfo(
            call_info=CallInfo.empty(
                contract_address=self.sender_address,
                caller_address=0,
                class_hash=self.class_hash,
            ),
            fee_transfer_info=None,
            actual_fee=0,
        )


@marshmallow_dataclass.dataclass(frozen=True)
class InternalDeploy(InternalTransaction):
    """
    Represents an internal transaction in the StarkNet network that is a deployment of a Cairo
    contract.
    """

    contract_address: int = field(metadata=fields.contract_address_metadata)
    contract_address_salt: int = field(metadata=fields.contract_address_salt_metadata)
    contract_hash: bytes = field(metadata=fields.non_required_class_hash_metadata)

    constructor_calldata: List[int] = field(metadata=fields.call_data_metadata)

    # Class variables.
    tx_type: ClassVar[TransactionType] = TransactionType.DEPLOY
    related_external_cls: ClassVar[Type[Transaction]] = Deploy
    n_cairo_steps_estimation: ClassVar[int] = 100

    @marshmallow.decorators.pre_load
    def replace_contract_definition_with_contract_hash(
        self, data: Dict[str, Any], many: bool, **kwargs
    ) -> Dict[str, Any]:
        if "contract_hash" in data:
            return data

        contract_definition_json = data.pop("contract_definition")
        contract_definition = ContractClass.load(data=contract_definition_json)
        class_hash = compute_class_hash(contract_class=contract_definition)
        data["contract_hash"] = to_bytes(class_hash).hex()

        return data

    @classmethod
    def create(
        cls,
        contract_address_salt: int,
        contract_definition: ContractClass,
        constructor_calldata: List[int],
        chain_id: int,
        version: int,
    ):
        validate_version(version=version, only_query=False)

        class_hash = compute_class_hash(contract_class=contract_definition)
        contract_address = calculate_contract_address_from_hash(
            salt=contract_address_salt,
            class_hash=class_hash,
            constructor_calldata=constructor_calldata,
            deployer_address=0,
        )
        return cls(
            contract_address=contract_address,
            contract_address_salt=contract_address_salt,
            contract_hash=to_bytes(class_hash),
            constructor_calldata=constructor_calldata,
            version=version,
            hash_value=calculate_deploy_transaction_hash(
                version=version,
                contract_address=contract_address,
                constructor_calldata=constructor_calldata,
                chain_id=chain_id,
            ),
        )

    @classmethod
    async def create_for_testing(
        cls,
        ffc: FactFetchingContext,
        contract_class: ContractClass,
        contract_address_salt: int,
        constructor_calldata: List[int],
        chain_id: Optional[int] = None,
    ) -> "InternalDeploy":
        """
        Creates an InternalDeploy transaction and writes its contract class to the DB.
        This constructor should only be used in tests.
        """
        await write_contract_class_fact(contract_class=contract_class, ffc=ffc)
        return InternalDeploy.create(
            contract_address_salt=contract_address_salt,
            contract_definition=contract_class,
            constructor_calldata=constructor_calldata,
            chain_id=0 if chain_id is None else chain_id,
            version=constants.TRANSACTION_VERSION,
        )

    async def get_contract_class(self, storage: Storage) -> ContractClass:
        return await read_contract_class(class_hash=self.contract_hash, storage=storage)

    @classmethod
    def _specific_from_external(
        cls, external_tx: Transaction, general_config: StarknetGeneralConfig
    ) -> "InternalDeploy":
        assert isinstance(external_tx, Deploy)
        return cls.create(
            contract_address_salt=external_tx.contract_address_salt,
            contract_definition=external_tx.contract_definition,
            constructor_calldata=external_tx.constructor_calldata,
            chain_id=general_config.chain_id.value,
            version=external_tx.version,
        )

    def to_external(self) -> Deploy:
        raise NotImplementedError("Cannot convert internal deploy transaction to external object.")

    def get_state_selector(self, general_config: Config) -> StateSelector:
        """
        Returns the state selector of the transaction (i.e., subset of state commitment tree leaves
        it affects).
        """
        return StateSelector(contract_addresses={self.contract_address}, class_hashes=set())

    async def _apply_specific_state_updates(
        self, state: CarriedState, general_config: StarknetGeneralConfig
    ) -> TransactionExecutionInfo:
        """
        Adds the deployed contract to the global commitment tree state.
        """
        allowed_versions = [constants.TRANSACTION_VERSION]
        assert self.version in allowed_versions, f"Invalid transaction version: {self.version}."

        await initialize_contract_state(
            state=state,
            class_hash=self.contract_hash,
            contract_address=self.contract_address,
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
        contract_class = await self.get_contract_class(storage=state.ffc.storage)
        if len(contract_class.entry_points_by_type[EntryPointType.CONSTRUCTOR]) == 0:
            stark_assert(
                len(self.constructor_calldata) == 0,
                code=StarknetErrorCode.TRANSACTION_FAILED,
                message="Cannot pass calldata to a contract with no constructor.",
            )
            return TransactionExecutionInfo(
                call_info=CallInfo.empty_constructor_call(
                    contract_address=self.contract_address,
                    caller_address=0,
                    class_hash=self.contract_hash,
                ),
                fee_transfer_info=None,
                actual_fee=0,
            )

        call = ExecuteEntryPoint(
            call_type=CallType.CALL,
            class_hash=None,
            contract_address=self.contract_address,
            code_address=None,
            entry_point_selector=CONSTRUCTOR_SELECTOR,
            entry_point_type=EntryPointType.CONSTRUCTOR,
            calldata=self.constructor_calldata,
            caller_address=0,
        )

        tx_execution_context = TransactionExecutionContext.create(
            account_contract_address=0,
            transaction_hash=self.hash_value,
            signature=[],
            max_fee=0,
            n_steps=general_config.invoke_tx_max_n_steps,
            version=self.version,
        )
        call_info = await call.execute(
            state=state, general_config=general_config, tx_execution_context=tx_execution_context
        )
        return TransactionExecutionInfo(call_info=call_info, fee_transfer_info=None, actual_fee=0)


@marshmallow_dataclass.dataclass(frozen=True)
class InternalInvokeFunction(InternalTransaction):
    """
    Represents an internal transaction in the StarkNet network that is an invocation of a Cairo
    contract function.
    """

    contract_address: int = field(metadata=fields.contract_address_metadata)
    entry_point_selector: int = field(metadata=fields.entry_point_selector_metadata)
    # The decorator type of the called function. Note that a single function may be decorated with
    # multiple decorators and this member specifies which one.
    entry_point_type: EntryPointType
    calldata: List[int] = field(metadata=fields.call_data_metadata)
    max_fee: int = field(metadata=fields.fee_metadata)
    signature: List[int] = field(metadata=fields.signature_metadata)
    # A unique nonce, added by the StarkNet core contract on L1.
    # This nonce is used to make the hash_value of transactions that service L1 messages unique.
    # This field may be set only when entry_point_type is EntryPointType.L1_HANDLER.
    nonce: Optional[int] = field(metadata=fields.optional_nonce_metadata)
    caller_address: int = field(metadata=fields.caller_address_metadata)

    # Class variables.
    tx_type: ClassVar[TransactionType] = TransactionType.INVOKE_FUNCTION
    related_external_cls: ClassVar[Type[Transaction]] = InvokeFunction

    @marshmallow.decorators.pre_load
    def remove_deprecated_fields(
        self, data: Dict[str, Any], many: bool, **kwargs
    ) -> Dict[str, Any]:
        if "code_address" in data:
            assert data["code_address"] == data["contract_address"]
            del data["code_address"]

        return data

    @classmethod
    def create_for_testing(
        cls,
        contract_address: int,
        calldata: List[int],
        entry_point_selector: int,
        max_fee: Optional[int] = None,
        entry_point_type: Optional[EntryPointType] = None,
        signature: Optional[List[int]] = None,
        caller_address: Optional[int] = None,
        nonce: Optional[int] = None,
        chain_id: Optional[int] = None,
    ):
        return cls.create(
            contract_address=contract_address,
            entry_point_selector=entry_point_selector,
            max_fee=0 if max_fee is None else max_fee,
            version=constants.TRANSACTION_VERSION,
            entry_point_type=(
                EntryPointType.EXTERNAL if entry_point_type is None else entry_point_type
            ),
            calldata=calldata,
            signature=[] if signature is None else signature,
            caller_address=0 if caller_address is None else caller_address,
            nonce=nonce,
            chain_id=0 if chain_id is None else chain_id,
            only_query=False,
        )

    @classmethod
    def _specific_from_external(
        cls, external_tx: Transaction, general_config: StarknetGeneralConfig
    ) -> "InternalInvokeFunction":
        assert isinstance(external_tx, InvokeFunction)
        return cls.create(
            contract_address=external_tx.contract_address,
            entry_point_selector=external_tx.entry_point_selector,
            max_fee=external_tx.max_fee,
            entry_point_type=EntryPointType.EXTERNAL,
            calldata=external_tx.calldata,
            signature=external_tx.signature,
            nonce=None,
            chain_id=general_config.chain_id.value,
            version=external_tx.version,
        )

    @classmethod
    def from_external_query_tx(
        cls,
        tx: InvokeFunction,
        general_config: StarknetGeneralConfig,
    ) -> "InternalInvokeFunction":
        return cls.create(
            contract_address=tx.contract_address,
            entry_point_selector=tx.entry_point_selector,
            max_fee=tx.max_fee,
            entry_point_type=EntryPointType.EXTERNAL,
            calldata=tx.calldata,
            signature=tx.signature,
            nonce=None,
            chain_id=general_config.chain_id.value,
            version=tx.version,
            only_query=True,
        )

    @classmethod
    def create(
        cls,
        contract_address: int,
        entry_point_selector: int,
        max_fee: int,
        entry_point_type: EntryPointType,
        calldata: List[int],
        signature: List[int],
        nonce: Optional[int],
        chain_id: int,
        version: int,
        # The caller_address of an external transaction or L1 handler is always 0.
        # The caller_address is passed as paramater to allow the testing framework to initiate
        # transactions with a user specified caller_address.
        caller_address: int = 0,
        # Used to distinguish between query and other transactions.
        only_query: bool = False,
    ) -> "InternalInvokeFunction":
        tx_hash_prefix, additional_data = preprocess_invoke_function_fields(
            entry_point_type=entry_point_type,
            entry_point_selector=entry_point_selector,
            message_from_l1_nonce=nonce,
            max_fee=max_fee,
            version=version,
            only_query=only_query,
        )

        hash_value = calculate_transaction_hash_common(
            tx_hash_prefix=tx_hash_prefix,
            version=version,
            contract_address=contract_address,
            entry_point_selector=entry_point_selector,
            calldata=calldata,
            max_fee=max_fee,
            chain_id=chain_id,
            additional_data=additional_data,
        )

        return cls(
            contract_address=contract_address,
            entry_point_selector=entry_point_selector,
            max_fee=max_fee,
            version=version,
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

        return InvokeFunction(
            contract_address=self.contract_address,
            entry_point_selector=self.entry_point_selector,
            calldata=self.calldata,
            max_fee=self.max_fee,
            version=self.version,
            signature=self.signature,
        )

    def get_state_selector(self, general_config: Config) -> StateSelector:
        """
        Returns the state selector of the transaction (i.e., subset of state commitment tree leaves
        it affects).
        """
        contract_addresses = {self.contract_address}
        if self.max_fee > 0:
            # Downcast arguments to application-specific types.
            assert isinstance(general_config, StarknetGeneralConfig)
            contract_addresses.add(general_config.fee_token_address)

        return StateSelector(contract_addresses=contract_addresses, class_hashes=set())

    async def _apply_specific_state_updates(
        self, state: CarriedState, general_config: StarknetGeneralConfig
    ) -> TransactionExecutionInfo:
        """
        Applies self to 'state' by executing the entry point and charging fee for it (if needed).
        """
        call_info = await self.execute(state=state, general_config=general_config)
        fee_transfer_info, actual_fee = await self.charge_fee(
            state=state, general_config=general_config, call_info=call_info
        )

        return TransactionExecutionInfo(
            call_info=call_info, fee_transfer_info=fee_transfer_info, actual_fee=actual_fee
        )

    async def execute(
        self, state: CarriedState, general_config: StarknetGeneralConfig, only_query: bool = False
    ) -> CallInfo:
        """
        Builds the transaction execution context and executes the entry point.
        Returns the CallInfo.
        """
        # Sanity check for query mode.
        validate_version(version=self.version, only_query=only_query)

        call = ExecuteEntryPoint(
            call_type=CallType.CALL,
            class_hash=None,
            contract_address=self.contract_address,
            code_address=None,
            entry_point_selector=self.entry_point_selector,
            entry_point_type=self.entry_point_type,
            calldata=self.calldata,
            caller_address=self.caller_address,
        )

        return await call.execute(
            state=state,
            general_config=general_config,
            tx_execution_context=self.get_execution_context(
                n_steps=general_config.invoke_tx_max_n_steps
            ),
        )

    async def charge_fee(
        self, state: CarriedState, general_config: StarknetGeneralConfig, call_info: CallInfo
    ) -> Tuple[Optional[CallInfo], int]:
        """
        Calculates and charges the actual fee.
        """
        if self.max_fee == 0:
            # Fee charging is not enforced in some tests.
            return None, 0

        # Should always pass on regular flows (verified in the create() method).
        assert self.entry_point_selector == starknet_abi.EXECUTE_ENTRY_POINT_SELECTOR
        assert self.entry_point_type is EntryPointType.EXTERNAL

        actual_fee = calculate_tx_fee(
            state=state,
            call_info=call_info,
            general_config=general_config,
        )
        fee_transfer_info = await execute_fee_transfer(
            general_config=general_config,
            state=state,
            tx_execution_context=self.get_execution_context(
                n_steps=general_config.invoke_tx_max_n_steps
            ),
            actual_fee=actual_fee,
        )

        return fee_transfer_info, actual_fee

    def get_execution_context(self, n_steps: int) -> TransactionExecutionContext:
        return TransactionExecutionContext.create(
            account_contract_address=self.contract_address,
            transaction_hash=self.hash_value,
            signature=self.signature,
            max_fee=self.max_fee,
            n_steps=n_steps,
            version=self.version,
        )

    def get_l1_handler_payload_size(self) -> Optional[int]:
        """
        Returns the payload size of the corresponding L1-to-L2 message if the transaction is an L1
        handler. Otherwise returns None.
        """
        if self.entry_point_type is not EntryPointType.L1_HANDLER:
            return None
        # The calldata includes the "from" field, which is not a part of the payload.
        # We thus subtract 1.
        return len(self.calldata) - 1


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
        TransactionType.DECLARE.name: InternalDeclare.Schema,
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
