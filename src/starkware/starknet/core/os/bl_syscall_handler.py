from typing import Iterable, List, Optional, Tuple, Type

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.common.structs import CairoStructProxy
from starkware.cairo.lang.vm.memory_segments import MemorySegmentManager
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.python.utils import as_non_optional
from starkware.starknet.business_logic.execution.deprecated_objects import ExecutionResourcesManager
from starkware.starknet.business_logic.execution.execute_entry_point_base import (
    ExecuteEntryPointBase,
)
from starkware.starknet.business_logic.execution.objects import (
    CallInfo,
    CallResult,
    CallType,
    OrderedEvent,
    OrderedL2ToL1Message,
    TransactionExecutionContext,
)
from starkware.starknet.business_logic.state.state import ContractStorageState
from starkware.starknet.business_logic.state.state_api import SyncState
from starkware.starknet.core.os.contract_address.contract_address import (
    calculate_contract_address_from_hash,
)
from starkware.starknet.core.os.os_logger import OptionalSegmentManager
from starkware.starknet.core.os.syscall_handler import SyscallFullResponse, SyscallHandlerBase
from starkware.starknet.core.os.syscall_utils import cast_to_int, wrap_with_handler_exception
from starkware.starknet.definitions import constants
from starkware.starknet.definitions.data_availability_mode import DataAvailabilityMode
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.execution_mode import ExecutionMode
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.public.abi import CONSTRUCTOR_ENTRY_POINT_SELECTOR
from starkware.starknet.services.api.contract_class.contract_class import EntryPointType
from starkware.starkware_utils.error_handling import stark_assert


class BusinessLogicSyscallHandler(SyscallHandlerBase):
    """
    A handler for system calls; used by the BusinessLogic entry point execution.
    """

    def __init__(
        self,
        state: SyncState,
        resources_manager: ExecutionResourcesManager,
        segments: MemorySegmentManager,
        tx_execution_context: TransactionExecutionContext,
        initial_syscall_ptr: RelocatableValue,
        general_config: StarknetGeneralConfig,
        entry_point: ExecuteEntryPointBase,
        support_reverted: bool,
    ):
        super().__init__(
            segments=OptionalSegmentManager(segments=segments),
            initial_syscall_ptr=initial_syscall_ptr,
        )

        # Entry point info.
        self.entry_point = entry_point
        self.execute_entry_point_cls: Type[ExecuteEntryPointBase] = type(entry_point)

        # Configuration objects.
        self.general_config = general_config

        # Execution-related objects.
        self.tx_execution_context = tx_execution_context
        self.resources_manager = resources_manager
        self.state = state
        self.support_reverted = support_reverted

        # The storage which the current call acts on.
        self.storage = ContractStorageState(
            state=state, contract_address=self.entry_point.contract_address
        )

        # A list of dynamically allocated segments that are expected to be read-only.
        self.read_only_segments: List[Tuple[RelocatableValue, int]] = []

        # Internal calls executed by the current contract call.
        self.internal_calls: List[CallInfo] = []

        # Events emitted by the current contract call.
        self.events: List[OrderedEvent] = []

        # Messages sent by the current contract call to L1.
        self.l2_to_l1_messages: List[OrderedL2ToL1Message] = []

        # A pointer to the Cairo ExecutionInfo struct.
        self._execution_info_ptr: Optional[RelocatableValue] = None

    @property
    def current_block_number(self) -> int:
        return self.state.block_info.block_number

    # Syscalls.

    def get_block_hash(self, remaining_gas: int, request: CairoStructProxy) -> SyscallFullResponse:
        syscall_name = "get_block_hash"
        stark_assert(
            not self._is_validate_execution_mode(),
            code=StarknetErrorCode.UNAUTHORIZED_ACTION_ON_VALIDATE,
            message=(
                f"Unauthorized syscall {syscall_name} "
                f"in execution mode {self.tx_execution_context.execution_mode.name}."
            ),
        )
        return super().get_block_hash(remaining_gas=remaining_gas, request=request)

    def _call_contract_helper(
        self, remaining_gas: int, request: CairoStructProxy, syscall_name: str
    ) -> CallResult:
        calldata = self._get_felt_range(
            start_addr=request.calldata_start, end_addr=request.calldata_end
        )
        class_hash: Optional[int] = None
        if syscall_name == "call_contract":
            contract_address = cast_to_int(request.contract_address)
            caller_address = self.entry_point.contract_address
            call_type = CallType.Call
            if self._is_validate_execution_mode():
                stark_assert(
                    self.entry_point.contract_address == contract_address,
                    code=StarknetErrorCode.UNAUTHORIZED_ACTION_ON_VALIDATE,
                    message=(
                        f"Unauthorized syscall {syscall_name} "
                        f"in execution mode {self.tx_execution_context.execution_mode.name}."
                    ),
                )
        elif syscall_name == "library_call":
            contract_address = self.entry_point.contract_address
            caller_address = self.entry_point.caller_address
            call_type = CallType.Delegate
            class_hash = cast_to_int(request.class_hash)
        else:
            raise NotImplementedError(f"Unsupported call type {syscall_name}.")

        call = self.execute_entry_point_cls(
            call_type=call_type,
            contract_address=contract_address,
            entry_point_selector=cast_to_int(request.selector),
            entry_point_type=EntryPointType.EXTERNAL,
            calldata=calldata,
            caller_address=caller_address,
            initial_gas=remaining_gas,
            class_hash=class_hash,
            code_address=None,
        )

        return self.execute_entry_point(call=call)

    def _deploy(self, remaining_gas: int, request: CairoStructProxy) -> Tuple[int, CallResult]:
        assert request.deploy_from_zero in [0, 1], "The deploy_from_zero field must be 0 or 1."
        constructor_calldata = self._get_felt_range(
            start_addr=request.constructor_calldata_start, end_addr=request.constructor_calldata_end
        )
        class_hash = cast_to_int(request.class_hash)

        # Calculate contract address.
        deployer_address = self.entry_point.contract_address if request.deploy_from_zero == 0 else 0
        contract_address = calculate_contract_address_from_hash(
            salt=cast_to_int(request.contract_address_salt),
            class_hash=class_hash,
            constructor_calldata=constructor_calldata,
            deployer_address=deployer_address,
        )
        # Instantiate the contract (may raise UNDECLARED_CLASS and CONTRACT_ADDRESS_UNAVAILABLE).
        self.state.deploy_contract(contract_address=contract_address, class_hash=class_hash)

        # Invoke constructor.
        result = self.execute_constructor_entry_point(
            contract_address=contract_address,
            class_hash=class_hash,
            constructor_calldata=constructor_calldata,
            remaining_gas=remaining_gas,
        )
        return contract_address, result

    def _get_block_hash(self, block_number: int) -> int:
        return self.state.get_storage_at(
            data_availability_mode=DataAvailabilityMode.L1,
            contract_address=constants.BLOCK_HASH_CONTRACT_ADDRESS,
            key=block_number,
        )

    def _get_class_hash_at(self, contract_address: int) -> int:
        raise NotImplementedError(
            "get_class_hash_at is not implemented for BusinessLogicSyscallHandler."
        )

    def _get_execution_info_ptr(self) -> RelocatableValue:
        if self._execution_info_ptr is None:
            # Prepare block info.
            python_block_info = self.storage.state.block_info
            if self._is_validate_execution_mode():
                block_number_for_validate = (
                    python_block_info.block_number // constants.VALIDATE_BLOCK_NUMBER_ROUNDING
                ) * constants.VALIDATE_BLOCK_NUMBER_ROUNDING
                block_timestamp_for_validate = (
                    python_block_info.block_timestamp // constants.VALIDATE_TIMESTAMP_ROUNDING
                ) * constants.VALIDATE_TIMESTAMP_ROUNDING
                block_info = self.structs.BlockInfo(
                    block_number=block_number_for_validate,
                    block_timestamp=block_timestamp_for_validate,
                    sequencer_address=0,
                )
            else:
                block_info = self.structs.BlockInfo(
                    block_number=python_block_info.block_number,
                    block_timestamp=python_block_info.block_timestamp,
                    sequencer_address=as_non_optional(python_block_info.sequencer_address),
                )

            # Prepare transaction info.
            signature = self.tx_execution_context.signature
            signature_start = self.allocate_segment(data=signature)
            tx_info = self.structs.TxInfo(
                version=self.tx_execution_context.version,
                account_contract_address=self.tx_execution_context.account_contract_address,
                max_fee=self.tx_execution_context.max_fee,
                signature_start=signature_start,
                signature_end=signature_start + len(signature),
                transaction_hash=self.tx_execution_context.transaction_hash,
                chain_id=self.general_config.chain_id.value,
                nonce=self.tx_execution_context.nonce,
                # We only support execution of transactions with version < 3, hence we set the new
                # additional fields to zero.
                resource_bounds_start=0,
                resource_bounds_end=0,
                tip=0,
                paymaster_data_start=0,
                paymaster_data_end=0,
                nonce_data_availability_mode=0,
                fee_data_availability_mode=0,
                account_deployment_data_start=0,
                account_deployment_data_end=0,
            )
            # Gather all info.
            execution_info = self.structs.ExecutionInfo(
                block_info=self.allocate_segment(data=block_info),
                tx_info=self.allocate_segment(data=tx_info),
                caller_address=self.entry_point.caller_address,
                contract_address=self.entry_point.contract_address,
                selector=self.entry_point.entry_point_selector,
            )
            self._execution_info_ptr = self.allocate_segment(data=execution_info)

        return self._execution_info_ptr

    def _storage_read(self, key: int) -> int:
        return self.storage.read(address=key)

    def _storage_write(self, key: int, value: int):
        self.storage.write(address=key, value=value)

    def _emit_event(self, keys: List[int], data: List[int]):
        self.events.append(
            OrderedEvent.create(
                order=self.tx_execution_context.n_emitted_events, keys=keys, data=data
            )
        )

        # Update events count.
        self.tx_execution_context.n_emitted_events += 1

    def _replace_class(self, class_hash: int):
        compiled_class_hash = self.storage.state.get_compiled_class_hash(class_hash=class_hash)
        stark_assert(
            compiled_class_hash != 0,
            code=StarknetErrorCode.UNDECLARED_CLASS,
            message=f"Class with hash {class_hash} is not declared.",
        )

        # Replace the class.
        self.state.set_class_hash_at(
            contract_address=self.entry_point.contract_address, class_hash=class_hash
        )

    def _send_message_to_l1(self, to_address: int, payload: List[int]):
        self.l2_to_l1_messages.append(
            # Note that the constructor of OrderedL2ToL1Message might fail as it is
            # more restrictive than the Cairo code.
            OrderedL2ToL1Message.create(
                order=self.tx_execution_context.n_sent_messages,
                to_address=to_address,
                payload=payload,
            )
        )

        # Update messages count.
        self.tx_execution_context.n_sent_messages += 1

    # Utilities.

    def execute_entry_point(self, call: ExecuteEntryPointBase) -> CallResult:
        with wrap_with_handler_exception(call=call):
            call_info = call.execute(
                state=self.state,
                resources_manager=self.resources_manager,
                tx_execution_context=self.tx_execution_context,
                general_config=self.general_config,
                support_reverted=self.support_reverted,
            )

        self.internal_calls.append(call_info)
        return call_info.result()

    def execute_constructor_entry_point(
        self,
        contract_address: int,
        class_hash: int,
        constructor_calldata: List[int],
        remaining_gas: int,
    ) -> CallResult:
        contract_class = self.state.get_compiled_class_by_class_hash(class_hash=class_hash)
        constructor_entry_points = contract_class.entry_points_by_type[EntryPointType.CONSTRUCTOR]
        if len(constructor_entry_points) == 0:
            # Contract has no constructor.
            assert (
                len(constructor_calldata) == 0
            ), "Cannot pass calldata to a contract with no constructor."

            call_info = CallInfo.empty_constructor_call(
                contract_address=contract_address,
                caller_address=self.entry_point.contract_address,
                class_hash=class_hash,
            )
            self.internal_calls.append(call_info)

            return call_info.result()

        call = self.execute_entry_point_cls(
            call_type=CallType.Call,
            contract_address=contract_address,
            entry_point_selector=CONSTRUCTOR_ENTRY_POINT_SELECTOR,
            entry_point_type=EntryPointType.CONSTRUCTOR,
            calldata=constructor_calldata,
            caller_address=self.entry_point.contract_address,
            initial_gas=remaining_gas,
            class_hash=None,
            code_address=None,
        )

        return self.execute_entry_point(call=call)

    def allocate_segment(self, data: Iterable[MaybeRelocatable]) -> RelocatableValue:
        segment_start = self.segments.add()
        segment_end = self.segments.write_arg(ptr=segment_start, arg=data)
        self.read_only_segments.append((segment_start, segment_end - segment_start))
        return segment_start

    def _allocate_segment_for_retdata(self, retdata: Iterable[int]) -> RelocatableValue:
        return self.allocate_segment(data=retdata)

    def post_run(self, runner: CairoFunctionRunner, syscall_end_ptr: MaybeRelocatable):
        """
        Performs post-run syscall-related tasks.
        """
        expected_syscall_end_ptr = self.syscall_ptr
        stark_assert(
            syscall_end_ptr == expected_syscall_end_ptr,
            code=StarknetErrorCode.SECURITY_ERROR,
            message=(
                f"Bad syscall_stop_ptr, Expected {expected_syscall_end_ptr}, "
                f"got {syscall_end_ptr}."
            ),
        )

        self._validate_read_only_segments(runner=runner)

    def _validate_read_only_segments(self, runner: CairoFunctionRunner):
        """
        Validates that there were no out of bounds writes to read-only segments and marks
        them as accessed.
        """
        assert self.segments is runner.segments, "Inconsistent segments."
        for segment_ptr, segment_size in self.read_only_segments:
            used_size = self.segments.get_segment_used_size(segment_index=segment_ptr.segment_index)
            stark_assert(
                used_size == segment_size,
                code=StarknetErrorCode.SECURITY_ERROR,
                message="Out of bounds write to a read-only segment.",
            )

            runner.mark_as_accessed(address=segment_ptr, size=segment_size)

    def _keccak(self, n_rounds: int):
        # For the keccak system call we want to count the number of rounds,
        # rather than the number of syscall invocations.
        self._count_syscall(syscall_name="keccak", count=n_rounds)

    def _count_syscall(self, syscall_name: str, count: int = 1):
        previous_syscall_count = self.resources_manager.syscall_counter.get(syscall_name, 0)
        self.resources_manager.syscall_counter[syscall_name] = previous_syscall_count + count

    def _is_validate_execution_mode(self):
        return self.tx_execution_context.execution_mode is ExecutionMode.VALIDATE
