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
from services.everest.business_logic.state_api import StateProxy
from starkware.python.utils import as_non_optional, from_bytes, to_bytes
from starkware.starknet.business_logic.execution.execute_entry_point import ExecuteEntryPoint
from starkware.starknet.business_logic.execution.objects import (
    CallInfo,
    ResourcesMapping,
    TransactionExecutionContext,
    TransactionExecutionInfo,
)
from starkware.starknet.business_logic.fact_state.contract_state_objects import StateSelector
from starkware.starknet.business_logic.fact_state.state import ExecutionResourcesManager
from starkware.starknet.business_logic.state.state import UpdatesTrackerState
from starkware.starknet.business_logic.state.state_api import SyncState
from starkware.starknet.business_logic.state.state_api_objects import BlockInfo
from starkware.starknet.business_logic.transaction.fee import calculate_tx_fee, execute_fee_transfer
from starkware.starknet.business_logic.transaction.state_objects import InternalStateTransaction
from starkware.starknet.business_logic.utils import (
    calculate_tx_resources,
    preprocess_invoke_function_fields,
    verify_no_calls_to_other_contracts,
    verify_version,
    write_contract_class_fact,
)
from starkware.starknet.core.os.class_hash import compute_class_hash
from starkware.starknet.core.os.contract_address.contract_address import (
    calculate_contract_address_from_hash,
)
from starkware.starknet.core.os.transaction_hash.transaction_hash import (
    TransactionHashPrefix,
    calculate_declare_transaction_hash,
    calculate_deploy_account_transaction_hash,
    calculate_deploy_transaction_hash,
    calculate_transaction_hash_common,
)
from starkware.starknet.definitions import constants, fields
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starknet.public import abi as starknet_abi
from starkware.starknet.services.api.contract_class import ContractClass, EntryPointType
from starkware.starknet.services.api.gateway.transaction import (
    DEFAULT_DECLARE_SENDER_ADDRESS,
    Declare,
    Deploy,
    DeployAccount,
    InvokeFunction,
    Transaction,
)
from starkware.starkware_utils.config_base import Config
from starkware.starkware_utils.error_handling import stark_assert, stark_assert_eq
from starkware.storage.storage import FactFetchingContext

logger = logging.getLogger(__name__)


# Mypy has a problem with dataclasses that contain unimplemented abstract methods.
# See https://github.com/python/mypy/issues/5374 for details on this problem.
# Do not use __post_init__ on internal transactions. An inconsistency may happen during upgrade.
# A transaction may pass the Gateway, then an upgrade happens, then reach the Batcher.
# When a transaction reaches the Batcher - we do not want it to fail while being built.
@marshmallow_dataclass.dataclass(frozen=True)  # type: ignore[misc]
class InternalTransaction(InternalStateTransaction, EverestInternalTransaction):
    """
    StarkNet internal transaction base class.
    """

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

        internal_cls = cls.external_to_internal_cls.get(type(external_tx))
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
        self, state: StateProxy, general_config: Config
    ) -> TransactionExecutionInfo:
        # super().apply_state_updates calls InternalStateTransaction.apply_state_updates
        # that calls self._apply_specific_state_updates and therefore does not return None.
        tx_execution_info = await super().apply_state_updates(
            state=state, general_config=general_config
        )
        assert isinstance(tx_execution_info, TransactionExecutionInfo)
        return tx_execution_info

    @abstractmethod
    def _apply_specific_sequential_changes(
        self,
        state: SyncState,
        general_config: StarknetGeneralConfig,
        concurrent_execution_info: TransactionExecutionInfo,
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

    def _apply_specific_sequential_changes(
        self,
        state: SyncState,
        general_config: StarknetGeneralConfig,
        concurrent_execution_info: TransactionExecutionInfo,
    ) -> Optional[TransactionExecutionInfo]:
        # Validate progress is legal.
        state.block_info.validate_legal_progress(next_block_info=self.block_info)

        # Update entire block-related information.
        state.update_block_info(block_info=self.block_info)

        return None

    def _apply_specific_concurrent_changes(
        self, state: UpdatesTrackerState, general_config: StarknetGeneralConfig
    ) -> TransactionExecutionInfo:
        return TransactionExecutionInfo.empty()

    def get_state_selector(self, general_config: Config) -> StateSelector:
        return StateSelector.empty()


@dataclasses.dataclass(frozen=True)  # type: ignore[misc]
class InternalAccountTransaction(InternalTransaction):
    """
    Represents a transaction that originated from an action of an account.
    """

    # The version of the transaction. It is fixed in the OS, and should be
    # signed by the account contract.
    # This field allows invalidating old transactions, whenever the meaning of the other
    # transaction fields is changed (in the OS).
    version: int = field(metadata=fields.non_required_tx_version_metadata)
    # The maximal fee to be paid in Wei for the execution.
    max_fee: int = field(metadata=fields.fee_metadata)
    signature: List[int] = field(metadata=fields.signature_metadata)
    # The nonce of the transaction, a sequential number attached to the account contract. Guarantees
    # a unique hash_value of transactions.
    nonce: Optional[int] = field(metadata=fields.optional_nonce_metadata)

    @property
    @abstractmethod
    def account_contract_address(self) -> int:
        """
        The address of the account contract initiating this transaction.
        """

    @property
    @abstractmethod
    def validate_entrypoint_calldata(self) -> List[int]:
        """
        The calldata input to the transaction-specific validation function.
        """

    # Class variables.

    @property
    @classmethod
    @abstractmethod
    def validate_entry_point_selector(cls) -> int:
        """
        The entry point selector of the transaction-specific validation function.
        """

    def verify_version(self):
        verify_version(version=self.version, only_query=False, old_supported_versions=[0])

    def run_validate_entrypoint(
        self,
        state: SyncState,
        resources_manager: ExecutionResourcesManager,
        general_config: StarknetGeneralConfig,
    ) -> Optional[CallInfo]:
        """
        Runs the transaction-specific validation function.
        """
        if self.version in [0, constants.QUERY_VERSION_BASE]:
            return None

        call = ExecuteEntryPoint.create(
            contract_address=self.account_contract_address,
            entry_point_selector=self.validate_entry_point_selector,
            entry_point_type=EntryPointType.EXTERNAL,
            calldata=self.validate_entrypoint_calldata,
            caller_address=0,
        )

        call_info = call.execute(
            state=state,
            resources_manager=resources_manager,
            general_config=general_config,
            tx_execution_context=self.get_execution_context(
                n_steps=general_config.validate_max_n_steps
            ),
        )
        verify_no_calls_to_other_contracts(call_info=call_info, function_name="'validate'")

        return call_info

    def get_execution_context(self, n_steps: int) -> TransactionExecutionContext:
        return TransactionExecutionContext.create(
            account_contract_address=self.account_contract_address,
            transaction_hash=self.hash_value,
            signature=self.signature,
            max_fee=self.max_fee,
            nonce=self.nonce,
            n_steps=n_steps,
            version=self.version,
        )

    def charge_fee(
        self, state: SyncState, resources: ResourcesMapping, general_config: StarknetGeneralConfig
    ) -> Tuple[Optional[CallInfo], int]:
        """
        Calculates and charges the actual fee.
        """
        if self.max_fee == 0:
            # Fee charging is not enforced in some tests.
            return None, 0

        actual_fee = calculate_tx_fee(
            gas_price=state.block_info.gas_price, general_config=general_config, resources=resources
        )
        fee_transfer_info = execute_fee_transfer(
            general_config=general_config,
            state=state,
            tx_execution_context=self.get_execution_context(
                n_steps=general_config.invoke_tx_max_n_steps
            ),
            actual_fee=actual_fee,
        )

        return fee_transfer_info, actual_fee

    def _handle_nonce(self, state: SyncState):
        """
        Verifies that the transaction's nonce matches the contract's nonce and increments the
        latter (modifies state).
        """
        # Don't handle nonce for version 0.
        if self.version in [0, constants.QUERY_VERSION_BASE]:
            return

        current_nonce = state.get_nonce_at(contract_address=self.account_contract_address)
        stark_assert(
            current_nonce == self.nonce,
            code=StarknetErrorCode.INVALID_TRANSACTION_NONCE,
            message=f"Invalid transaction nonce. Expected: {current_nonce}, got: {self.nonce}.",
        )

        # Increment nonce.
        # Note that changing contract_state.nonce directly will bypass the proxy used to revert
        # transactions.
        state.increment_nonce(contract_address=self.account_contract_address)

    def _apply_specific_sequential_changes(
        self,
        state: SyncState,
        general_config: StarknetGeneralConfig,
        concurrent_execution_info: TransactionExecutionInfo,
    ) -> TransactionExecutionInfo:
        self._handle_nonce(state=state)

        # Handle fee.
        fee_transfer_info, actual_fee = self.charge_fee(
            state=state,
            general_config=general_config,
            resources=concurrent_execution_info.actual_resources,
        )

        return TransactionExecutionInfo.from_concurrent_stage_execution_info(
            concurrent_execution_info=concurrent_execution_info,
            fee_transfer_info=fee_transfer_info,
            actual_fee=actual_fee,
        )


@marshmallow_dataclass.dataclass(frozen=True)
class InternalDeclare(InternalAccountTransaction):
    """
    Represents an internal transaction in the StarkNet network that is a declaration of a Cairo
    contract class.
    """

    # The hash of the declared class.
    class_hash: bytes = field(metadata=fields.class_hash_metadata)
    sender_address: int = field(metadata=fields.contract_address_metadata)

    # Class variables.
    tx_type: ClassVar[TransactionType] = TransactionType.DECLARE
    related_external_cls: ClassVar[Type[Transaction]] = Declare
    validate_entry_point_selector: ClassVar[
        int
    ] = starknet_abi.VALIDATE_DECLARE_ENTRY_POINT_SELECTOR

    @property
    def account_contract_address(self) -> int:
        return self.sender_address

    @property
    def validate_entrypoint_calldata(self) -> List[int]:
        # '__validate_declare__' is expected to get one parameter: 'class_hash'.
        return [from_bytes(self.class_hash)]

    def verify_version(self):
        super().verify_version()

        if self.version not in [0, constants.QUERY_VERSION_BASE]:
            return

        stark_assert_eq(
            DEFAULT_DECLARE_SENDER_ADDRESS,
            self.sender_address,
            code=StarknetErrorCode.OUT_OF_RANGE_CONTRACT_ADDRESS,
            message=(
                "The sender_address field in Declare transactions of version 0 "
                f"must be {DEFAULT_DECLARE_SENDER_ADDRESS}."
            ),
        )
        stark_assert_eq(
            0,
            self.max_fee,
            code=StarknetErrorCode.OUT_OF_RANGE_FEE,
            message="The max_fee field in Declare transactions of version 0 must be 0.",
        )
        stark_assert_eq(
            0,
            self.nonce,
            code=StarknetErrorCode.OUT_OF_RANGE_NONCE,
            message="The nonce field in Declare transactions of version 0 must be 0.",
        )
        stark_assert_eq(
            0,
            len(self.signature),
            code=StarknetErrorCode.NON_EMPTY_SIGNATURE,
            message="The signature field in Declare transactions must be an empty list.",
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
        class_hash = compute_class_hash(contract_class=contract_class)
        internal_declare = cls(
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
                nonce=nonce,
            ),
        )
        internal_declare.verify_version()
        return internal_declare

    @classmethod
    async def create_for_testing(
        cls,
        ffc: FactFetchingContext,
        contract_class: ContractClass,
        chain_id: Optional[int] = None,
        max_fee: int = 0,
        sender_address: Optional[int] = None,
        signature: Optional[List[int]] = None,
    ) -> "InternalDeclare":
        """
        Creates an InternalDeclare transaction and writes its contract class to the DB.
        This constructor should only be used in tests.
        """
        await write_contract_class_fact(contract_class=contract_class, ffc=ffc)
        if sender_address is None:
            version = 0
            sender_address = DEFAULT_DECLARE_SENDER_ADDRESS
        else:
            version = constants.TRANSACTION_VERSION

        return InternalDeclare.create(
            contract_class=contract_class,
            chain_id=0 if chain_id is None else chain_id,
            sender_address=sender_address,
            max_fee=max_fee,
            version=version,
            signature=[] if signature is None else signature,
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
        if self.version in [0, constants.QUERY_VERSION_BASE]:
            return StateSelector.empty()

        return StateSelector.create(
            contract_addresses=[self.sender_address],
            class_hashes=[self.class_hash],
        )

    def _apply_specific_concurrent_changes(
        self, state: UpdatesTrackerState, general_config: StarknetGeneralConfig
    ) -> TransactionExecutionInfo:
        # Reject unsupported versions. This is necessary (in addition to the gateway's check)
        # since an old transaction might still reach here, e.g., in case of a re-org.
        self.verify_version()

        # Validate transaction.
        resources_manager = ExecutionResourcesManager.empty()
        validate_info = self.run_validate_entrypoint(
            state=state,
            resources_manager=resources_manager,
            general_config=general_config,
        )

        # Handle fee.
        actual_resources = calculate_tx_resources(
            state=state,
            resources_manager=resources_manager,
            call_infos=[validate_info],
            tx_type=self.tx_type,
        )

        return TransactionExecutionInfo.create_concurrent_stage_execution_info(
            validate_info=validate_info,
            call_info=None,
            actual_resources=actual_resources,
            tx_type=self.tx_type,
        )


@marshmallow_dataclass.dataclass(frozen=True)
class InternalDeployAccount(InternalAccountTransaction):
    """
    Internal version of the DeployAccount transaction (deployment of StarkNet account contracts).
    """

    contract_address: int = field(metadata=fields.contract_address_metadata)
    contract_address_salt: int = field(metadata=fields.contract_address_salt_metadata)
    class_hash: bytes = field(metadata=fields.class_hash_metadata)
    constructor_calldata: List[int] = field(metadata=fields.call_data_metadata)
    version: int = field(metadata=fields.tx_version_metadata)
    # Repeat `nonce` to narrow its type to non-optional int.
    nonce: int = field(metadata=fields.nonce_metadata)

    # Class variables.
    tx_type: ClassVar[TransactionType] = TransactionType.DEPLOY_ACCOUNT
    related_external_cls: ClassVar[Type[Transaction]] = DeployAccount
    validate_entry_point_selector: ClassVar[int] = starknet_abi.VALIDATE_DEPLOY_ENTRY_POINT_SELECTOR

    @property
    def account_contract_address(self) -> int:
        return self.contract_address

    @property
    def validate_entrypoint_calldata(self) -> List[int]:
        # '__validate_deploy__' is expected to get the arguments:
        # class_hash, salt, constructor_calldata.
        return [
            from_bytes(self.class_hash),
            self.contract_address_salt,
            *self.constructor_calldata,
        ]

    def verify_version(self):
        verify_version(version=self.version, only_query=False, old_supported_versions=[])

    @classmethod
    def create(
        cls,
        class_hash: int,
        max_fee: int,
        version: int,
        nonce: int,
        constructor_calldata: List[int],
        signature: List[int],
        contract_address_salt: int,
        chain_id: int,
    ) -> "InternalDeployAccount":
        contract_address = calculate_contract_address_from_hash(
            salt=contract_address_salt,
            class_hash=class_hash,
            constructor_calldata=constructor_calldata,
            deployer_address=0,
        )
        internal_deploy_account = cls(
            contract_address=contract_address,
            contract_address_salt=contract_address_salt,
            constructor_calldata=constructor_calldata,
            class_hash=to_bytes(class_hash),
            version=version,
            max_fee=max_fee,
            signature=signature,
            nonce=nonce,
            hash_value=calculate_deploy_account_transaction_hash(
                version=version,
                contract_address=contract_address,
                class_hash=class_hash,
                constructor_calldata=constructor_calldata,
                max_fee=max_fee,
                nonce=nonce,
                salt=contract_address_salt,
                chain_id=chain_id,
            ),
        )
        internal_deploy_account.verify_version()
        return internal_deploy_account

    @classmethod
    async def create_for_testing(
        cls,
        contract_class: ContractClass,
        max_fee: int,
        contract_address_salt: int = 0,
        constructor_calldata: Optional[List[int]] = None,
        chain_id: int = 0,
        signature: Optional[List[int]] = None,
    ) -> "InternalDeployAccount":
        return InternalDeployAccount.create(
            class_hash=compute_class_hash(contract_class=contract_class),
            contract_address_salt=contract_address_salt,
            constructor_calldata=[] if constructor_calldata is None else constructor_calldata,
            nonce=0,
            max_fee=max_fee,
            version=constants.TRANSACTION_VERSION,
            signature=[] if signature is None else signature,
            chain_id=chain_id,
        )

    @classmethod
    def _specific_from_external(
        cls, external_tx: Transaction, general_config: StarknetGeneralConfig
    ) -> "InternalDeployAccount":
        assert isinstance(external_tx, DeployAccount)
        return cls.create(
            class_hash=external_tx.class_hash,
            max_fee=external_tx.max_fee,
            version=external_tx.version,
            nonce=external_tx.nonce,
            constructor_calldata=external_tx.constructor_calldata,
            signature=external_tx.signature,
            contract_address_salt=external_tx.contract_address_salt,
            chain_id=general_config.chain_id.value,
        )

    def to_external(self) -> DeployAccount:
        return DeployAccount(
            version=self.version,
            max_fee=self.max_fee,
            signature=self.signature,
            nonce=self.nonce,
            contract_address_salt=self.contract_address_salt,
            class_hash=from_bytes(self.class_hash),
            constructor_calldata=self.constructor_calldata,
        )

    def get_state_selector(self, general_config: Config) -> StateSelector:
        """
        Returns the state selector of the transaction (i.e., subset of state commitment tree leaves
        it affects).
        """
        return StateSelector.create(
            contract_addresses=[self.contract_address], class_hashes=[self.class_hash]
        )

    def _apply_specific_concurrent_changes(
        self, state: UpdatesTrackerState, general_config: StarknetGeneralConfig
    ) -> TransactionExecutionInfo:
        """
        Adds the deployed contract to the global commitment tree state.
        """
        # Reject unsupported versions. This is necessary (in addition to the gateway's check)
        # since an old transaction might still reach here, e.g., in case of a re-org.
        self.verify_version()

        # Ensure the class is declared (by reading it).
        contract_class = state.get_contract_class(class_hash=self.class_hash)

        # Deploy.
        state.deploy_contract(contract_address=self.contract_address, class_hash=self.class_hash)

        # Run the constructor.
        resources_manager = ExecutionResourcesManager.empty()
        constructor_call_info = self.handle_constructor(
            contract_class=contract_class,
            state=state,
            general_config=general_config,
            resources_manager=resources_manager,
        )

        # Validate transaction.
        validate_info = self.run_validate_entrypoint(
            state=state, resources_manager=resources_manager, general_config=general_config
        )

        actual_resources = calculate_tx_resources(
            state=state,
            resources_manager=resources_manager,
            call_infos=[constructor_call_info, validate_info],
            tx_type=self.tx_type,
        )

        return TransactionExecutionInfo.create_concurrent_stage_execution_info(
            validate_info=validate_info,
            call_info=constructor_call_info,
            actual_resources=actual_resources,
            tx_type=self.tx_type,
        )

    def handle_constructor(
        self,
        contract_class: ContractClass,
        state: UpdatesTrackerState,
        general_config: StarknetGeneralConfig,
        resources_manager: ExecutionResourcesManager,
    ) -> CallInfo:
        n_ctors = len(contract_class.entry_points_by_type[EntryPointType.CONSTRUCTOR])
        if n_ctors == 0:
            stark_assert(
                len(self.constructor_calldata) == 0,
                code=StarknetErrorCode.TRANSACTION_FAILED,
                message="Cannot pass calldata to a contract with no constructor.",
            )
            return CallInfo.empty_constructor_call(
                contract_address=self.contract_address,
                caller_address=0,
                class_hash=self.class_hash,
            )
        else:
            return self.run_constructor_entrypoint(
                state=state, general_config=general_config, resources_manager=resources_manager
            )

    def run_constructor_entrypoint(
        self,
        state: UpdatesTrackerState,
        general_config: StarknetGeneralConfig,
        resources_manager: ExecutionResourcesManager,
    ) -> CallInfo:
        call = ExecuteEntryPoint.create(
            contract_address=self.contract_address,
            entry_point_selector=starknet_abi.CONSTRUCTOR_ENTRY_POINT_SELECTOR,
            entry_point_type=EntryPointType.CONSTRUCTOR,
            calldata=self.constructor_calldata,
            caller_address=0,
        )
        constructor_call_info = call.execute(
            state=state,
            resources_manager=resources_manager,
            general_config=general_config,
            tx_execution_context=self.get_execution_context(
                n_steps=general_config.validate_max_n_steps
            ),
        )
        verify_no_calls_to_other_contracts(
            call_info=constructor_call_info, function_name="DeployAccount's constructor"
        )

        return constructor_call_info


@marshmallow_dataclass.dataclass(frozen=True)
class InternalDeploy(InternalTransaction):
    """
    Represents an internal transaction in the StarkNet network that is a deployment of a Cairo
    contract.
    """

    # The version of the transaction. It is fixed (currently, 1) in the OS, and should be
    # signed by the account contract.
    # This field allows invalidating old transactions, whenever the meaning of the other
    # transaction fields is changed (in the OS).
    version: int = field(metadata=fields.non_required_tx_version_metadata)
    contract_address: int = field(metadata=fields.contract_address_metadata)
    contract_address_salt: int = field(metadata=fields.contract_address_salt_metadata)
    contract_hash: bytes = field(metadata=fields.non_required_class_hash_metadata)

    constructor_calldata: List[int] = field(metadata=fields.call_data_metadata)

    # Class variables.
    tx_type: ClassVar[TransactionType] = TransactionType.DEPLOY
    related_external_cls: ClassVar[Type[Transaction]] = Deploy

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
        contract_class: ContractClass,
        constructor_calldata: List[int],
        chain_id: int,
        version: int,
    ):
        verify_version(version=version, only_query=False, old_supported_versions=[0])

        class_hash = compute_class_hash(contract_class=contract_class)
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
            contract_class=contract_class,
            constructor_calldata=constructor_calldata,
            chain_id=0 if chain_id is None else chain_id,
            version=constants.TRANSACTION_VERSION,
        )

    @classmethod
    def _specific_from_external(
        cls, external_tx: Transaction, general_config: StarknetGeneralConfig
    ) -> "InternalDeploy":
        assert isinstance(external_tx, Deploy)
        return cls.create(
            contract_address_salt=external_tx.contract_address_salt,
            contract_class=external_tx.contract_definition,
            constructor_calldata=external_tx.constructor_calldata,
            chain_id=general_config.chain_id.value,
            version=external_tx.version,
        )

    @property
    def class_hash(self) -> bytes:
        return self.contract_hash

    def to_external(self) -> Deploy:
        raise NotImplementedError("Cannot convert internal deploy transaction to external object.")

    def get_state_selector(self, general_config: Config) -> StateSelector:
        """
        Returns the state selector of the transaction (i.e., subset of state commitment tree leaves
        it affects).
        """
        return StateSelector.create(contract_addresses=[self.contract_address], class_hashes=[])

    def _apply_specific_concurrent_changes(
        self, state: UpdatesTrackerState, general_config: StarknetGeneralConfig
    ) -> TransactionExecutionInfo:
        """
        Adds the deployed contract to the global commitment tree state.
        """
        # Reject unsupported versions. This is necessary (in addition to the gateway's check)
        # since an old transaction might still reach here, e.g., in case of a re-org.
        verify_version(version=self.version, only_query=False, old_supported_versions=[0])

        # Execute transaction.
        state.deploy_contract(contract_address=self.contract_address, class_hash=self.contract_hash)
        contract_class = state.get_contract_class(class_hash=self.contract_hash)
        n_ctors = len(contract_class.entry_points_by_type[EntryPointType.CONSTRUCTOR])
        if n_ctors == 0:
            return self.handle_empty_constructor(state=state)
        else:
            return self.invoke_constructor(state=state, general_config=general_config)

    def _apply_specific_sequential_changes(
        self,
        state: SyncState,
        general_config: StarknetGeneralConfig,
        concurrent_execution_info: TransactionExecutionInfo,
    ) -> TransactionExecutionInfo:
        return concurrent_execution_info

    def handle_empty_constructor(self, state: UpdatesTrackerState) -> TransactionExecutionInfo:
        stark_assert(
            len(self.constructor_calldata) == 0,
            code=StarknetErrorCode.TRANSACTION_FAILED,
            message="Cannot pass calldata to a contract with no constructor.",
        )

        call_info = CallInfo.empty_constructor_call(
            contract_address=self.contract_address,
            caller_address=0,
            class_hash=self.contract_hash,
        )
        resources_manager = ExecutionResourcesManager.empty()
        actual_resources = calculate_tx_resources(
            state=state,
            resources_manager=resources_manager,
            call_infos=[call_info],
            tx_type=self.tx_type,
        )

        return TransactionExecutionInfo.create_concurrent_stage_execution_info(
            validate_info=None,
            call_info=call_info,
            actual_resources=actual_resources,
            tx_type=self.tx_type,
        )

    def invoke_constructor(
        self, state: UpdatesTrackerState, general_config: StarknetGeneralConfig
    ) -> TransactionExecutionInfo:
        call = ExecuteEntryPoint.create(
            contract_address=self.contract_address,
            entry_point_selector=starknet_abi.CONSTRUCTOR_ENTRY_POINT_SELECTOR,
            entry_point_type=EntryPointType.CONSTRUCTOR,
            calldata=self.constructor_calldata,
            caller_address=0,
        )
        tx_execution_context = TransactionExecutionContext.create(
            account_contract_address=0,
            transaction_hash=self.hash_value,
            signature=[],
            max_fee=0,
            nonce=0,
            n_steps=general_config.invoke_tx_max_n_steps,
            version=self.version,
        )

        resources_manager = ExecutionResourcesManager.empty()
        call_info = call.execute(
            state=state,
            resources_manager=resources_manager,
            general_config=general_config,
            tx_execution_context=tx_execution_context,
        )
        actual_resources = calculate_tx_resources(
            state=state,
            resources_manager=resources_manager,
            call_infos=[call_info],
            tx_type=self.tx_type,
        )

        return TransactionExecutionInfo.create_concurrent_stage_execution_info(
            validate_info=None,
            call_info=call_info,
            actual_resources=actual_resources,
            tx_type=self.tx_type,
        )


@marshmallow_dataclass.dataclass(frozen=True)
class InternalInvokeFunction(InternalAccountTransaction):
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

    # Class variables.
    tx_type: ClassVar[TransactionType] = TransactionType.INVOKE_FUNCTION
    related_external_cls: ClassVar[Type[Transaction]] = InvokeFunction
    validate_entry_point_selector: ClassVar[int] = starknet_abi.VALIDATE_ENTRY_POINT_SELECTOR

    @property
    def account_contract_address(self) -> int:
        return self.contract_address

    @property
    def validate_entrypoint_calldata(self) -> List[int]:
        # '__validate__' is expected to get the same calldata as '__execute__'.
        return self.calldata

    def verify_version(self):
        super().verify_version()

        if self.version not in [0, constants.QUERY_VERSION_BASE]:
            stark_assert_eq(
                self.entry_point_selector,
                starknet_abi.EXECUTE_ENTRY_POINT_SELECTOR,
                code=StarknetErrorCode.UNAUTHORIZED_ENTRY_POINT_FOR_INVOKE,
                message=(
                    "The entry_point_selector field in InvokeFunction transactions "
                    f"must be {starknet_abi.EXECUTE_ENTRY_POINT_NAME}."
                ),
            )

    @marshmallow.decorators.pre_load
    def remove_deprecated_fields(
        self, data: Dict[str, Any], many: bool, **kwargs
    ) -> Dict[str, Any]:
        if "code_address" in data:
            assert data["code_address"] == data["contract_address"]
            del data["code_address"]

        if "caller_address" in data:
            assert data["caller_address"] == fields.AddressField.format(
                0
            ), "The `caller_address` of an external transaction must be 0."
            del data["caller_address"]

        return data

    @classmethod
    def create_for_testing(
        cls,
        contract_address: int,
        calldata: List[int],
        nonce: int,
        signature: Optional[List[int]] = None,
        max_fee: Optional[int] = None,
        chain_id: Optional[int] = None,
    ):
        return cls.create(
            contract_address=contract_address,
            entry_point_selector=starknet_abi.EXECUTE_ENTRY_POINT_SELECTOR,
            max_fee=0 if max_fee is None else max_fee,
            version=constants.TRANSACTION_VERSION,
            calldata=calldata,
            nonce=nonce,
            signature=[] if signature is None else signature,
            chain_id=0 if chain_id is None else chain_id,
        )

    @classmethod
    def create_wrapped_with_account(
        cls,
        account_address: int,
        contract_address: int,
        calldata: List[int],
        entry_point_selector: int,
        nonce: Optional[int],
        signature: Optional[List[int]] = None,
        max_fee: Optional[int] = None,
        chain_id: Optional[int] = None,
        version: Optional[int] = None,
    ):
        """
        Creates an account contract invocation to the 'dummy_account'
        test contract at address 'account_address'; should only be used in tests.
        """

        return cls.create(
            contract_address=account_address,
            entry_point_selector=starknet_abi.EXECUTE_ENTRY_POINT_SELECTOR,
            max_fee=0 if max_fee is None else max_fee,
            version=constants.TRANSACTION_VERSION if version is None else version,
            calldata=[contract_address, entry_point_selector, len(calldata), *calldata],
            nonce=nonce,
            signature=[] if signature is None else signature,
            chain_id=0 if chain_id is None else chain_id,
        )

    @classmethod
    def _specific_from_external(
        cls, external_tx: Transaction, general_config: StarknetGeneralConfig
    ) -> "InternalInvokeFunction":
        assert isinstance(external_tx, InvokeFunction)

        return cls.create(
            contract_address=external_tx.contract_address,
            entry_point_selector=cls._get_selector_from_external_tx(tx=external_tx),
            max_fee=external_tx.max_fee,
            calldata=external_tx.calldata,
            nonce=external_tx.nonce,
            signature=external_tx.signature,
            chain_id=general_config.chain_id.value,
            version=external_tx.version,
        )

    @classmethod
    def _get_selector_from_external_tx(cls, tx: InvokeFunction) -> int:
        if tx.version in [0, constants.QUERY_VERSION_BASE]:
            stark_assert(
                tx.entry_point_selector is not None,
                code=StarknetErrorCode.MISSING_ENTRY_POINT_FOR_INVOKE,
                message="Entry point selector must be specified for version 0.",
            )
            return as_non_optional(tx.entry_point_selector)

        stark_assert(
            tx.entry_point_selector is None,
            code=StarknetErrorCode.UNAUTHORIZED_ENTRY_POINT_FOR_INVOKE,
            message="Entry point selector must not be specified for version 1 one and above.",
        )
        return starknet_abi.EXECUTE_ENTRY_POINT_SELECTOR

    @classmethod
    def create(
        cls,
        contract_address: int,
        entry_point_selector: int,
        max_fee: int,
        calldata: List[int],
        signature: List[int],
        nonce: Optional[int],
        chain_id: int,
        version: int,
    ) -> "InternalInvokeFunction":
        (entry_point_selector_field, additional_data) = preprocess_invoke_function_fields(
            entry_point_selector=entry_point_selector,
            nonce=nonce,
            max_fee=max_fee,
            version=version,
        )

        hash_value = calculate_transaction_hash_common(
            tx_hash_prefix=TransactionHashPrefix.INVOKE,
            version=version,
            contract_address=contract_address,
            entry_point_selector=entry_point_selector_field,
            calldata=calldata,
            max_fee=max_fee,
            chain_id=chain_id,
            additional_data=additional_data,
        )

        internal_invoke = cls(
            contract_address=contract_address,
            entry_point_selector=entry_point_selector,
            max_fee=max_fee,
            version=version,
            entry_point_type=EntryPointType.EXTERNAL,
            calldata=calldata,
            nonce=nonce,
            signature=signature,
            hash_value=hash_value,
        )
        internal_invoke.verify_version()
        return internal_invoke

    def to_external(self) -> InvokeFunction:
        assert self.entry_point_type is EntryPointType.EXTERNAL, (
            "It it illegal to convert to external an InternalInvokeFunction of a non-external "
            f"Cairo contract function; got: {self.entry_point_type.name}."
        )

        return InvokeFunction(
            contract_address=self.contract_address,
            entry_point_selector=self.entry_point_selector
            if self.version in [0, constants.QUERY_VERSION_BASE]
            else None,
            calldata=self.calldata,
            max_fee=self.max_fee,
            version=self.version,
            nonce=self.nonce,
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

        return StateSelector.create(contract_addresses=contract_addresses, class_hashes=[])

    def _apply_specific_concurrent_changes(
        self, state: UpdatesTrackerState, general_config: StarknetGeneralConfig
    ) -> TransactionExecutionInfo:
        """
        Applies self to 'state' by executing the entry point and charging fee for it (if needed).
        """
        # Reject unsupported versions. This is necessary (in addition to the gateway's check)
        # since an old transaction might still reach here, e.g., in case of a re-org.
        self.verify_version()

        # Validate transaction.
        resources_manager = ExecutionResourcesManager.empty()
        validate_info = self.run_validate_entrypoint(
            state=state,
            resources_manager=resources_manager,
            general_config=general_config,
        )

        # Execute transaction.
        call_info = self.run_execute_entrypoint(
            state=state,
            resources_manager=resources_manager,
            general_config=general_config,
        )

        # Handle fee.
        actual_resources = calculate_tx_resources(
            state=state,
            resources_manager=resources_manager,
            call_infos=[call_info, validate_info],
            tx_type=self.tx_type,
        )

        return TransactionExecutionInfo.create_concurrent_stage_execution_info(
            validate_info=validate_info,
            call_info=call_info,
            actual_resources=actual_resources,
            tx_type=self.tx_type,
        )

    def run_validate_entrypoint(
        self,
        state: SyncState,
        resources_manager: ExecutionResourcesManager,
        general_config: StarknetGeneralConfig,
    ) -> Optional[CallInfo]:
        """
        Runs the '__validate__' entry point.
        """
        if self.entry_point_selector != starknet_abi.EXECUTE_ENTRY_POINT_SELECTOR:
            return None

        return super().run_validate_entrypoint(
            state=state, resources_manager=resources_manager, general_config=general_config
        )

    def run_execute_entrypoint(
        self,
        state: SyncState,
        resources_manager: ExecutionResourcesManager,
        general_config: StarknetGeneralConfig,
    ) -> CallInfo:
        """
        Builds the transaction execution context and executes the entry point.
        Returns the CallInfo.
        """
        call = ExecuteEntryPoint.create(
            contract_address=self.contract_address,
            entry_point_selector=self.entry_point_selector,
            entry_point_type=EntryPointType.EXTERNAL,
            calldata=self.calldata,
            caller_address=0,
        )

        return call.execute(
            state=state,
            resources_manager=resources_manager,
            general_config=general_config,
            tx_execution_context=self.get_execution_context(
                n_steps=general_config.invoke_tx_max_n_steps
            ),
        )


@marshmallow_dataclass.dataclass(frozen=True)
class InternalL1Handler(InternalTransaction):
    """
    Represents an internal transaction in the StarkNet network that is an invocation of a Cairo
    contract L1 handler.
    """

    contract_address: int = field(metadata=fields.contract_address_metadata)
    entry_point_selector: int = field(metadata=fields.entry_point_selector_metadata)
    calldata: List[int] = field(metadata=fields.call_data_metadata)
    # A unique nonce, added by the StarkNet core contract on L1. Guarantees a unique
    # hash_value of transactions.
    nonce: Optional[int] = field(metadata=fields.optional_nonce_metadata)

    # Class variables.
    tx_type: ClassVar[TransactionType] = TransactionType.L1_HANDLER

    @property
    @classmethod
    def related_external_cls(cls) -> Type[Transaction]:
        raise NotImplementedError("InternalL1Handler does not have a corresponding external class.")

    @marshmallow.decorators.pre_load
    def remove_deprecated_fields(
        self, data: Dict[str, Any], many: bool, **kwargs
    ) -> Dict[str, Any]:
        for deprecated_field in (
            "entry_point_type",
            "max_fee",
            "signature",
            "version",
            "caller_address",
            "code_address",
        ):
            data.pop(deprecated_field, None)

        return data

    @classmethod
    def _specific_from_external(
        cls, external_tx: Transaction, general_config: StarknetGeneralConfig
    ) -> "InternalTransaction":
        raise NotImplementedError("InternalL1Handler does not have a corresponding external class.")

    def to_external(self) -> Transaction:
        raise NotImplementedError("InternalL1Handler does not have a corresponding external class.")

    @classmethod
    def create_for_testing(
        cls,
        contract_address: int,
        calldata: List[int],
        entry_point_selector: int,
        nonce: int,
        chain_id: Optional[int] = None,
    ):
        return cls.create(
            contract_address=contract_address,
            entry_point_selector=entry_point_selector,
            calldata=calldata,
            nonce=nonce,
            chain_id=0 if chain_id is None else chain_id,
        )

    @classmethod
    def create(
        cls,
        contract_address: int,
        entry_point_selector: int,
        calldata: List[int],
        nonce: int,
        chain_id: int,
    ) -> "InternalL1Handler":
        hash_value = calculate_transaction_hash_common(
            tx_hash_prefix=TransactionHashPrefix.L1_HANDLER,
            version=constants.L1_HANDLER_VERSION,
            contract_address=contract_address,
            entry_point_selector=entry_point_selector,
            calldata=calldata,
            max_fee=0,
            chain_id=chain_id,
            additional_data=[nonce],
        )

        return cls(
            contract_address=contract_address,
            entry_point_selector=entry_point_selector,
            calldata=calldata,
            nonce=nonce,
            hash_value=hash_value,
        )

    def get_state_selector(self, general_config: Config) -> StateSelector:
        """
        Returns the state selector of the transaction (i.e., subset of state commitment tree leaves
        it affects).
        """
        return StateSelector.create(contract_addresses=[self.contract_address], class_hashes=[])

    def _apply_specific_concurrent_changes(
        self, state: UpdatesTrackerState, general_config: StarknetGeneralConfig
    ) -> TransactionExecutionInfo:
        """
        Applies self to 'state' by executing the L1-handler entry point.
        """
        call = ExecuteEntryPoint.create(
            contract_address=self.contract_address,
            entry_point_selector=self.entry_point_selector,
            entry_point_type=EntryPointType.L1_HANDLER,
            calldata=self.calldata,
            caller_address=0,
        )

        # Execute transaction.
        resources_manager = ExecutionResourcesManager.empty()
        call_info = call.execute(
            state=state,
            resources_manager=resources_manager,
            general_config=general_config,
            tx_execution_context=self.get_execution_context(
                n_steps=general_config.invoke_tx_max_n_steps
            ),
        )

        actual_resources = calculate_tx_resources(
            state=state,
            resources_manager=resources_manager,
            call_infos=[call_info],
            tx_type=self.tx_type,
            l1_handler_payload_size=self.get_payload_size(),
        )

        return TransactionExecutionInfo.create_concurrent_stage_execution_info(
            validate_info=None,
            call_info=call_info,
            actual_resources=actual_resources,
            tx_type=self.tx_type,
        )

    def _apply_specific_sequential_changes(
        self,
        state: SyncState,
        general_config: StarknetGeneralConfig,
        concurrent_execution_info: TransactionExecutionInfo,
    ) -> TransactionExecutionInfo:
        return concurrent_execution_info

    def get_execution_context(self, n_steps: int) -> TransactionExecutionContext:
        return TransactionExecutionContext.create(
            account_contract_address=self.contract_address,
            transaction_hash=self.hash_value,
            signature=[],
            max_fee=0,
            nonce=as_non_optional(self.nonce),
            n_steps=n_steps,
            version=constants.L1_HANDLER_VERSION,
        )

    def get_payload_size(self) -> int:
        """
        Returns the payload size of the corresponding L1-to-L2 message.
        """
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
        TransactionType.DEPLOY_ACCOUNT.name: InternalDeployAccount.Schema,
        TransactionType.INVOKE_FUNCTION.name: InternalInvokeFunction.Schema,
        TransactionType.L1_HANDLER.name: InternalL1Handler.Schema,
    }

    def get_obj_type(self, obj: InternalTransaction) -> str:
        return obj.tx_type.name

    def get_data_type(self, data: Dict[str, Any]) -> str:
        data_type = data.get(self.type_field)
        if (
            data_type == TransactionType.INVOKE_FUNCTION.name
            and data.get("entry_point_type") == TransactionType.L1_HANDLER.name
        ):
            data.pop(self.type_field)
            return TransactionType.L1_HANDLER.name

        return super().get_data_type(data=data)


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
