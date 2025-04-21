import asyncio
import dataclasses
import logging
from dataclasses import field
from typing import Dict, Iterable, Iterator, Mapping, Optional

from starkware.cairo.lang.vm.memory_segments import MemorySegmentManager
from starkware.cairo.lang.vm.relocatable import RelocatableValue
from starkware.cairo.lang.vm.vm_consts import VmConstsReference
from starkware.python.utils import (
    assert_exhausted,
    execute_coroutine_threadsafe,
    gather_in_chunks,
    safe_zip,
)
from starkware.starknet.business_logic.execution.objects import (
    CallInfo,
    CallResult,
    TransactionExecutionInfo,
)
from starkware.starknet.core.os.kzg_manager import KzgManager
from starkware.starknet.core.os.os_input import OsBlockInput
from starkware.starknet.core.os.os_logger import OptionalSegmentManager, OsLogger
from starkware.starknet.definitions import fields
from starkware.starknet.services.api.contract_class.contract_class import EntryPointType
from starkware.starknet.storage.starknet_storage import CommitmentInfo, OsSingleStarknetStorage
from starkware.storage.storage import FactFetchingContext

logger = logging.getLogger(__name__)

StateEntryAndStoragePtr = tuple[RelocatableValue, RelocatableValue]


class StateUpdatePointers:
    """
    Ensures that all state and class updates of each block in a Multi-Block
    are written continuously on the same segments.
    The `combine blocks` function assumes this continuity for creating the Multi-Block output.
    """

    def __init__(self, segments: MemorySegmentManager):
        self.segments = segments
        # Maintain the State entry and storage pointers of each contract to keep them continuous.
        self.contract_address_to_state_entry_and_storage_ptr: Dict[
            int, StateEntryAndStoragePtr
        ] = dict()
        self.state_tree_ptr = self.segments.add()
        self.class_tree_ptr = self.segments.add()

    def get_contract_state_entry_and_storage_ptr(
        self, contract_address: int
    ) -> tuple[RelocatableValue, RelocatableValue]:
        if contract_address not in self.contract_address_to_state_entry_and_storage_ptr:
            self.contract_address_to_state_entry_and_storage_ptr[contract_address] = (
                self.segments.add(),
                self.segments.add(),
            )
        return self.contract_address_to_state_entry_and_storage_ptr[contract_address]


@dataclasses.dataclass(frozen=True)
class TransactionExecutionInfoForExecutionHelper:
    # The actual fee that was charged in Wei.
    actual_fee: int = field(metadata=fields.FeeField.metadata(field_name="actual_fee"))
    # Whether the transaction was reverted.
    is_reverted: bool


class OsExecutionHelper:
    """
    Maintains the information needed for executing transactions in the OS.
    """

    def __init__(
        self,
        tx_execution_infos: Iterable[TransactionExecutionInfo],
        storage_by_address: Mapping[int, OsSingleStarknetStorage],
        storage_commitments: Mapping[int, CommitmentInfo],
        loop: asyncio.AbstractEventLoop,
        debug_mode: bool,
        dynamic_read_fallback: bool,
        segments: OptionalSegmentManager,
        kzg_manager: KzgManager,
    ):
        """
        Private constructor.
        """
        self.debug_mode = debug_mode

        self.dynamic_read_fallback = dynamic_read_fallback

        self.kzg_manager = kzg_manager

        self.tx_execution_info_iterator: Iterator[TransactionExecutionInfo] = iter(
            tx_execution_infos
        )
        self.call_iterator: Iterator[CallInfo] = iter([])

        # The CallInfo for the call currently being executed.
        self._call_info: Optional[CallInfo] = None

        # An iterator over contract addresses that were deployed during that call.
        self.deployed_contracts_iterator: Iterator[int] = iter([])

        # An iterator to the results of the current call's internal calls.
        self.result_iterator: Iterator[CallResult] = iter([])

        # An iterator to the read_values array which is consumed when the transaction
        # code is executed.
        self.execute_code_read_iterator: Iterator[int] = iter([])

        # An iterator to the read_class_hash_values array which is consumed when the transaction
        # code is executed.
        self.execute_code_class_hash_read_iterator: Iterator[int] = iter([])

        # The TransactionExecutionInfo for the transaction currently being executed.
        self.tx_execution_info: Optional[TransactionExecutionInfoForExecutionHelper] = None

        # Starknet storage-related members.
        self.storage_by_address = storage_by_address

        # The commitments of the storage by address.
        self.precomputed_storage_commitments = storage_commitments

        # A pointer to the deprecated TxInfo struct.
        # This pointer needs to match the DeprecatedTxInfo pointer that is going to be used during
        # the system call validation by the Starknet OS.
        # Set during enter_call.
        self._deprecated_tx_info_ptr: Optional[RelocatableValue] = None

        # The Cairo ExecutionInfo struct of the current call.
        # Should match the ExecutionInfo pointer that is going to be used during the
        # system call validation by the StarkNet OS.
        # Set during enter_call.
        self._call_cairo_execution_info: Optional[VmConstsReference] = None

        # Current running event loop; used for running async tasks in a synchronous context.
        self.loop = loop

        self.os_logger = OsLogger(debug=debug_mode, segments=segments)

    @classmethod
    def create(
        cls,
        block_input: OsBlockInput,
        loop: asyncio.AbstractEventLoop,
        segments: OptionalSegmentManager,
        kzg_manager: KzgManager,
        ffc: FactFetchingContext,
        dynamic_read_fallback: bool,
        debug_mode: bool,
    ) -> "OsExecutionHelper":
        storage_by_address = {
            address: OsSingleStarknetStorage(
                data=data, ffc=ffc, dynamic_read_fallback=dynamic_read_fallback, loop=loop
            )
            for address, data in block_input.storage_by_address.items()
        }
        return cls(
            tx_execution_infos=block_input.tx_execution_infos,
            storage_by_address=storage_by_address,
            storage_commitments=block_input.address_to_storage_commitment_info,
            loop=loop,
            debug_mode=debug_mode,
            dynamic_read_fallback=dynamic_read_fallback,
            segments=segments,
            kzg_manager=kzg_manager,
        )

    @property
    def call_cairo_execution_info(self) -> VmConstsReference:
        assert self._call_cairo_execution_info is not None, "ExecutionInfo is not set."
        return self._call_cairo_execution_info

    @property
    def deprecated_tx_info_ptr(self) -> RelocatableValue:
        assert self._deprecated_tx_info_ptr is not None, "deprecated_tx_info is not set."
        return self._deprecated_tx_info_ptr

    def compute_storage_commitments(self) -> Mapping[int, CommitmentInfo]:
        if not self.dynamic_read_fallback:
            return self.precomputed_storage_commitments

        # Compute the commitments dynamically, given storage data collected during the OS execution.
        coroutine = gather_in_chunks(
            awaitables=(
                storage.compute_commitment() for storage in self.storage_by_address.values()
            )
        )
        commitments = execute_coroutine_threadsafe(coroutine=coroutine, loop=self.loop)
        storage_commitments = dict(safe_zip(self.storage_by_address.keys(), commitments))
        if storage_commitments != self.precomputed_storage_commitments:
            logger.warning("Computed commitments not equal precomputed commitments.")
            if self.debug_mode:
                self.log_commitment_discrepancies(storage_commitments)
        return storage_commitments

    def log_commitment_discrepancies(self, storage_commitments: Dict[int, CommitmentInfo]):
        for commitment in set(self.precomputed_storage_commitments) - set(storage_commitments):
            logger.warning(
                f"Redundant precomputed commitment info: Key: {commitment}, "
                f"Commitment info: {self.precomputed_storage_commitments[commitment]}."
            )
        for commitment in set(storage_commitments) - set(self.precomputed_storage_commitments):
            logger.warning(
                f"Missing precomputed commitment info: Key: {commitment}, "
                f"Commitment info: {storage_commitments[commitment]}."
            )
        for commitment in set(storage_commitments) & set(self.precomputed_storage_commitments):
            if storage_commitments[commitment] != self.precomputed_storage_commitments[commitment]:
                logger.warning(
                    f"Precomputed commitment mismatch: "
                    f"Computed commitment: {storage_commitments[commitment]}, "
                    f"Precomputed commitment: {self.precomputed_storage_commitments[commitment]}."
                )

    @property
    def call_info(self) -> CallInfo:
        assert self._call_info is not None
        return self._call_info

    def start_tx(self):
        """
        Called when starting the execution of a transaction.
        """
        assert self.tx_execution_info is None
        tx_execution_info = next(self.tx_execution_info_iterator)
        self.tx_execution_info = TransactionExecutionInfoForExecutionHelper(
            actual_fee=tx_execution_info.actual_fee,
            is_reverted=tx_execution_info.is_reverted,
        )
        self.call_iterator = tx_execution_info.gen_call_iterator()

    def end_tx(self):
        """
        Called after the execution of the current transaction complete.
        """
        assert_exhausted(iterator=self.call_iterator)
        assert self.tx_execution_info is not None
        self.tx_execution_info = None

    def assert_interators_exhausted(self):
        assert_exhausted(iterator=self.deployed_contracts_iterator)
        assert_exhausted(iterator=self.result_iterator)
        assert_exhausted(iterator=self.execute_code_read_iterator)
        assert_exhausted(iterator=self.execute_code_class_hash_read_iterator)

    def enter_call(
        self,
        cairo_execution_info: Optional[VmConstsReference],
        deprecated_tx_info: VmConstsReference,
    ):
        """
        'deprecated_tx_info' is a pointer to the deprecated TxInfo struct.
        """
        assert self._deprecated_tx_info_ptr is None
        self._deprecated_tx_info_ptr = deprecated_tx_info.address_

        assert self._call_cairo_execution_info is None
        self._call_cairo_execution_info = cairo_execution_info

        self.assert_interators_exhausted()

        assert self._call_info is None
        self._call_info = next(self.call_iterator)

        self.deployed_contracts_iterator = (
            call.contract_address
            for call in self.call_info.internal_calls
            if call.entry_point_type is EntryPointType.CONSTRUCTOR
        )
        self.result_iterator = (call.syscall_result() for call in self.call_info.internal_calls)
        self.execute_code_read_iterator = iter(
            self.call_info.storage_access_tracker.storage_read_values
        )
        self.execute_code_class_hash_read_iterator = iter(
            self.call_info.storage_access_tracker.read_class_hash_values
        )

    def exit_call(self):
        self._deprecated_tx_info_ptr = None
        self._call_cairo_execution_info = None

        self.assert_interators_exhausted()
        assert self._call_info is not None
        self._call_info = None

    def skip_tx(self):
        """
        Called when skipping the execution of a transaction.
        It replaces a call to start_tx and end_tx.
        """
        self.start_tx()
        self.end_tx()
