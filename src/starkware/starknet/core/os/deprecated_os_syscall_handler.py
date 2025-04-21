from typing import Dict, Iterable

from starkware.cairo.common.structs import CairoStructProxy
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.starknet.business_logic.execution.objects import CallResult
from starkware.starknet.business_logic.state.state_api_objects import BlockInfo
from starkware.starknet.core.os.deprecated_syscall_handler import DeprecatedSysCallHandlerBase
from starkware.starknet.core.os.execution.account_backward_compatibility import (
    get_v1_bound_accounts_cairo0,
    get_v1_bound_accounts_max_tip,
)
from starkware.starknet.core.os.execution_helper import OsExecutionHelper


class DeprecatedOsSysCallHandler(DeprecatedSysCallHandlerBase):
    """
    The SysCallHandler implementation that is used by the gps ambassador.
    """

    def __init__(self, execution_helper: OsExecutionHelper, block_info: BlockInfo):
        super().__init__(block_info=block_info, segments=execution_helper.os_logger.segments)
        self.execution_helper = execution_helper
        self.syscall_counter: Dict[str, int] = {}

    def _count_syscall(self, syscall_name: str):
        previous_syscall_count = self.syscall_counter.get(syscall_name, 0)
        self.syscall_counter[syscall_name] = previous_syscall_count + 1

    def _read_and_validate_syscall_request(
        self, syscall_name: str, syscall_ptr: RelocatableValue
    ) -> CairoStructProxy:
        """
        Returns the system call request written in the syscall segment, starting at syscall_ptr.
        Does not perform validations on the request, since it was validated in the BL.
        """
        self._count_syscall(syscall_name)
        return self._read_syscall_request(syscall_name=syscall_name, syscall_ptr=syscall_ptr)

    def _allocate_segment(self, data: Iterable[MaybeRelocatable]) -> RelocatableValue:
        """
        Allocates and returns a new temporary segment.
        """
        segment_start = self.segments.add_temp_segment()
        self.segments.write_arg(ptr=segment_start, arg=data)
        return segment_start

    def _call_contract(self, syscall_ptr: RelocatableValue, syscall_name: str) -> CallResult:
        return next(self.execution_helper.result_iterator)

    def _deploy(self, syscall_ptr: RelocatableValue) -> int:
        next(self.execution_helper.result_iterator)
        return next(self.execution_helper.deployed_contracts_iterator)

    def _get_block_number(self) -> int:
        return self.execution_helper.call_cairo_execution_info.block_info.block_number

    def _get_block_timestamp(self) -> int:
        return self.execution_helper.call_cairo_execution_info.block_info.block_timestamp

    def _get_sequencer_address(self) -> int:
        return self.execution_helper.call_cairo_execution_info.block_info.sequencer_address

    def _get_caller_address(self, syscall_ptr: RelocatableValue) -> int:
        return self.execution_helper.call_info.caller_address

    def _get_contract_address(self, syscall_ptr: RelocatableValue) -> int:
        return self.execution_helper.call_info.contract_address

    def _get_tx_info_ptr(self) -> RelocatableValue:
        tx_info = self.syscall_structs.TxInfo.from_ptr(
            memory=self.segments.memory, addr=self.execution_helper.deprecated_tx_info_ptr
        )
        class_hash = self.execution_helper.call_info.class_hash
        tip = self.execution_helper.call_cairo_execution_info.tx_info.tip
        if (
            tx_info.version == 3
            and class_hash in get_v1_bound_accounts_cairo0()
            and tip <= get_v1_bound_accounts_max_tip()
        ):
            # Return version=1 for version-bound accounts.
            res = self.segments.gen_arg(arg=tx_info._replace(version=1))
            assert isinstance(res, RelocatableValue)
            return res
        else:
            return self.execution_helper.deprecated_tx_info_ptr

    def _replace_class(self, class_hash: int):
        return

    def _storage_read(self, address: int) -> int:
        return next(self.execution_helper.execute_code_read_iterator)

    def _storage_write(self, address: int, value: int):
        return
