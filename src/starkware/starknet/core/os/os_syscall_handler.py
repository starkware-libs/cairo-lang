from typing import Dict, Iterable, List, Tuple

from starkware.cairo.common.structs import CairoStructProxy
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.starknet.business_logic.execution.objects import CallResult
from starkware.starknet.business_logic.state.state_api_objects import BlockInfo
from starkware.starknet.core.os.execution.account_backward_compatibility import (
    get_data_gas_accounts,
    get_v1_bound_accounts_cairo1,
    get_v1_bound_accounts_max_tip,
)
from starkware.starknet.core.os.execution_helper import OsExecutionHelper
from starkware.starknet.core.os.syscall_handler import SyscallHandlerBase, safe_div
from starkware.starknet.definitions import constants


class OsSyscallHandler(SyscallHandlerBase):
    """
    A handler for system calls; used by the GpsAmbassador in the OS run execution.
    """

    def __init__(
        self,
        execution_helper: OsExecutionHelper,
        block_info: BlockInfo,
    ):
        super().__init__(segments=execution_helper.os_logger.segments, initial_syscall_ptr=None)
        self.execution_helper = execution_helper
        self.block_info = block_info
        self.syscall_counter: Dict[str, int] = {}

    @property
    def current_block_number(self) -> int:
        return self.block_info.block_number

    def set_syscall_ptr(self, syscall_ptr: RelocatableValue):
        assert self._syscall_ptr is None, "syscall_ptr is already set."
        self._syscall_ptr = syscall_ptr

    def validate_and_discard_syscall_ptr(self, syscall_ptr_end: RelocatableValue):
        assert self._syscall_ptr == syscall_ptr_end, "Bad syscall_ptr_end."
        self._syscall_ptr = None

    def allocate_segment(self, data: Iterable[MaybeRelocatable]) -> RelocatableValue:
        segment_start = self.segments.add()
        self.segments.write_arg(ptr=segment_start, arg=data)
        return segment_start

    def _allocate_segment_for_retdata(self, retdata: Iterable[int]) -> RelocatableValue:
        segment_start = self.segments.add_temp_segment()
        self.segments.write_arg(ptr=segment_start, arg=retdata)
        return segment_start

    # Syscalls.

    def _call_contract_helper(
        self, remaining_gas: int, request: CairoStructProxy, syscall_name: str
    ) -> CallResult:
        return next(self.execution_helper.result_iterator)

    def _deploy(self, remaining_gas: int, request: CairoStructProxy) -> Tuple[int, CallResult]:
        constructor_result = next(self.execution_helper.result_iterator)
        contract_address = next(self.execution_helper.deployed_contracts_iterator)
        return contract_address, constructor_result

    def _get_block_hash(self, block_number: int) -> int:
        # The syscall handler should not directly read from the storage during the execution of
        # transactions because the order in which reads and writes occur is not strictly linear.
        # However, for the "block hash contract," this rule does not apply. This contract is updated
        # only at the start of each block before other transactions are executed.
        return self.execution_helper.storage_by_address[constants.BLOCK_HASH_CONTRACT_ADDRESS].read(
            block_number
        )

    def _get_class_hash_at(self, contract_address: int) -> int:
        return next(self.execution_helper.execute_code_class_hash_read_iterator)

    def _get_execution_info_ptr(self) -> RelocatableValue:
        execution_info = self.execution_helper.call_cairo_execution_info
        tx_info = execution_info.tx_info
        class_hash = self.execution_helper.call_info.class_hash
        to_replace_in_tx_info = {}

        # Handle v1 bound accounts.
        if (
            tx_info.version == 3
            and class_hash in get_v1_bound_accounts_cairo1()
            and tx_info.tip <= get_v1_bound_accounts_max_tip()
        ):
            # Return version=1 for version-bound accounts.
            to_replace_in_tx_info["version"] = 1

        # Handle accounts that do not support `L1_DATA_GAS`.
        if class_hash in get_data_gas_accounts() and tx_info.version == 3:
            # Exclude l1_data_gas for data gas accounts.
            resource_bounds_start = tx_info.resource_bounds_start.address_
            resource_bounds_end = tx_info.resource_bounds_end.address_
            resource_bounds_len = safe_div(
                resource_bounds_end - resource_bounds_start, self.structs.ResourceBounds.size
            )
            assert resource_bounds_len == 3, "Resource bounds length must be 3 for V3 transactions."
            to_replace_in_tx_info["resource_bounds_end"] = (
                resource_bounds_end - self.structs.ResourceBounds.size
            )

        if len(to_replace_in_tx_info) == 0:
            # No need to replace anything - return the original pointer.
            return execution_info.address_

        modified_tx_info = self.structs.TxInfo.from_ptr(
            memory=self.segments.memory, addr=tx_info.address_
        )._replace(**to_replace_in_tx_info)
        res = self.segments.gen_arg(
            self.structs.ExecutionInfo.from_ptr(
                memory=self.segments.memory, addr=execution_info.address_
            )._replace(tx_info=modified_tx_info)
        )
        assert isinstance(res, RelocatableValue)
        return res

    def _storage_read(self, key: int) -> int:
        return next(self.execution_helper.execute_code_read_iterator)

    def _storage_write(self, key: int, value: int):
        return

    def _emit_event(self, keys: List[int], data: List[int]):
        return

    def _replace_class(self, class_hash: int):
        return

    def _send_message_to_l1(self, to_address: int, payload: List[int]):
        return

    def _keccak(self, n_rounds: int):
        return

    def _count_syscall(self, syscall_name: str):
        previous_syscall_count = self.syscall_counter.get(syscall_name, 0)
        self.syscall_counter[syscall_name] = previous_syscall_count + 1
