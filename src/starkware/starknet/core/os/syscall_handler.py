import dataclasses
import functools
from abc import ABC, abstractmethod
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Tuple,
    Type,
    cast,
)

import cachetools

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.common.structs import CairoStructProxy
from starkware.cairo.lang.vm.memory_segments import MemorySegmentManager
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.python.utils import as_non_optional, assert_exhausted, camel_to_snake_case
from starkware.starknet.business_logic.execution.execute_entry_point_base import (
    ExecuteEntryPointBase,
)
from starkware.starknet.business_logic.execution.objects import (
    CallInfo,
    CallResult,
    CallType,
    ExecutionResourcesManager,
    OrderedEvent,
    OrderedL2ToL1Message,
    TransactionExecutionContext,
    TransactionExecutionInfo,
)
from starkware.starknet.business_logic.state.state import ContractStorageState
from starkware.starknet.business_logic.state.state_api import SyncState
from starkware.starknet.business_logic.state.state_api_objects import BlockInfo
from starkware.starknet.core.os.contract_address.contract_address import (
    calculate_contract_address_from_hash,
)
from starkware.starknet.core.os.syscall_utils import (
    STARKNET_SYSCALLS_COMPILED_PATH,
    cast_to_int,
    get_deprecated_syscall_structs_and_info,
    get_selector_from_program,
    get_syscall_structs,
    load_program,
    validate_runtime_request_type,
    wrap_with_handler_exception,
)
from starkware.starknet.definitions.constants import GasCost
from starkware.starknet.definitions.error_codes import CairoErrorCode, StarknetErrorCode
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.public.abi import CONSTRUCTOR_ENTRY_POINT_SELECTOR
from starkware.starknet.services.api.contract_class.contract_class import EntryPointType
from starkware.starknet.storage.starknet_storage import OsSingleStarknetStorage
from starkware.starkware_utils.error_handling import stark_assert

SyscallFullResponse = Tuple[tuple, tuple]  # Response header + specific syscall response.
ExecuteSyscallCallback = Callable[
    ["SyscallHandlerBase", int, CairoStructProxy], SyscallFullResponse
]


@dataclasses.dataclass(frozen=True)
class SyscallInfo:
    name: str
    execute_callback: ExecuteSyscallCallback
    request_struct: CairoStructProxy


class SyscallHandlerBase(ABC):
    def __init__(
        self,
        segments: Optional[MemorySegmentManager],
        initial_syscall_ptr: Optional[RelocatableValue],
    ):
        # Static syscall information.
        self.structs = get_syscall_structs()
        self.selector_to_syscall_info = self.get_selector_to_syscall_info()

        # Memory segments of the running program.
        self._segments = segments
        # Current syscall pointer; updated internally during the call execution.
        self._syscall_ptr = initial_syscall_ptr

    @classmethod
    @cachetools.cached(cache={})
    def get_selector_to_syscall_info(cls) -> Dict[int, SyscallInfo]:
        structs = get_syscall_structs()
        syscalls_program = load_program(path=STARKNET_SYSCALLS_COMPILED_PATH)
        get_selector = functools.partial(
            get_selector_from_program, syscalls_program=syscalls_program
        )
        return {
            get_selector("call_contract"): SyscallInfo(
                name="call_contract",
                execute_callback=cls.call_contract,
                request_struct=structs.CallContractRequest,
            ),
            get_selector("deploy"): SyscallInfo(
                name="deploy",
                execute_callback=cls.deploy,
                request_struct=structs.DeployRequest,
            ),
            get_selector("get_execution_info"): SyscallInfo(
                name="get_execution_info",
                execute_callback=cls.get_execution_info,
                request_struct=structs.EmptyRequest,
            ),
            get_selector("library_call"): SyscallInfo(
                name="library_call",
                execute_callback=cls.library_call,
                request_struct=structs.LibraryCallRequest,
            ),
            get_selector("storage_read"): SyscallInfo(
                name="storage_read",
                execute_callback=cls.storage_read,
                request_struct=structs.StorageReadRequest,
            ),
            get_selector("storage_write"): SyscallInfo(
                name="storage_write",
                execute_callback=cls.storage_write,
                request_struct=structs.StorageWriteRequest,
            ),
            get_selector("emit_event"): SyscallInfo(
                name="emit_event",
                execute_callback=cls.emit_event,
                request_struct=structs.EmitEventRequest,
            ),
            get_selector("replace_class"): SyscallInfo(
                name="replace_class",
                execute_callback=cls.replace_class,
                request_struct=structs.ReplaceClassRequest,
            ),
            get_selector("send_message_to_l1"): SyscallInfo(
                name="send_message_to_l1",
                execute_callback=cls.send_message_to_l1,
                request_struct=structs.SendMessageToL1Request,
            ),
        }

    @property
    def segments(self) -> MemorySegmentManager:
        assert self._segments is not None, "segments must be set before using the SyscallHandler."
        return self._segments

    @property
    def syscall_ptr(self) -> RelocatableValue:
        assert (
            self._syscall_ptr is not None
        ), "syscall_ptr must be set before using the SyscallHandler."
        return self._syscall_ptr

    def syscall(self, syscall_ptr: RelocatableValue):
        """
        Executes the selected system call.
        """
        self._validate_syscall_ptr(actual_syscall_ptr=syscall_ptr)
        request_header = self._read_and_validate_request(request_struct=self.structs.RequestHeader)

        # Validate syscall selector and request.
        selector = cast_to_int(request_header.selector)
        syscall_info = self.selector_to_syscall_info.get(selector)
        assert syscall_info is not None, f"Unsupported syscall selector {selector}."
        request = self._read_and_validate_request(request_struct=syscall_info.request_struct)

        # Check and reduce gas (after validating the syscall selector for consistency with the OS).
        initial_gas = cast_to_int(request_header.gas)
        required_gas = self._get_required_gas(name=syscall_info.name)
        if initial_gas < required_gas:
            # Out of gas failure.
            response_header, response = self._handle_out_of_gas(initial_gas=initial_gas)
        else:
            # Execute.
            remaining_gas = initial_gas - required_gas
            response_header, response = syscall_info.execute_callback(self, remaining_gas, request)

        # Write response to the syscall segment.
        self._write_response(response=response_header)
        self._write_response(response=response)

    # Syscalls.

    def call_contract(self, remaining_gas: int, request: CairoStructProxy) -> SyscallFullResponse:
        return self.call_contract_helper(
            remaining_gas=remaining_gas, request=request, syscall_name="call_contract"
        )

    def library_call(self, remaining_gas: int, request: CairoStructProxy) -> SyscallFullResponse:
        return self.call_contract_helper(
            remaining_gas=remaining_gas, request=request, syscall_name="library_call"
        )

    def call_contract_helper(
        self, remaining_gas: int, request: CairoStructProxy, syscall_name: str
    ) -> SyscallFullResponse:
        result = self._call_contract_helper(
            remaining_gas=remaining_gas, request=request, syscall_name=syscall_name
        )

        remaining_gas -= result.gas_consumed
        response_header = self.structs.ResponseHeader(
            gas=remaining_gas, failure_flag=result.failure_flag
        )
        retdata_start = self._allocate_segment_for_retdata(retdata=result.retdata)
        retdata_end = retdata_start + len(result.retdata)
        if response_header.failure_flag == 0:
            response = self.structs.CallContractResponse(
                retdata_start=retdata_start, retdata_end=retdata_end
            )
        else:
            response = self.structs.FailureReason(start=retdata_start, end=retdata_end)

        return response_header, response

    def deploy(self, remaining_gas: int, request: CairoStructProxy) -> SyscallFullResponse:
        contract_address, result = self._deploy(remaining_gas=remaining_gas, request=request)

        remaining_gas -= result.gas_consumed
        response_header = self.structs.ResponseHeader(
            gas=remaining_gas, failure_flag=result.failure_flag
        )
        retdata_start = self._allocate_segment_for_retdata(retdata=result.retdata)
        retdata_end = retdata_start + len(result.retdata)
        if response_header.failure_flag == 0:
            response = self.structs.DeployResponse(
                contract_address=contract_address,
                constructor_retdata_start=retdata_start,
                constructor_retdata_end=retdata_end,
            )
        else:
            response = self.structs.FailureReason(start=retdata_start, end=retdata_end)

        return response_header, response

    def get_execution_info(
        self, remaining_gas: int, request: CairoStructProxy
    ) -> SyscallFullResponse:
        execution_info_ptr = self._get_execution_info_ptr()

        response_header = self.structs.ResponseHeader(gas=remaining_gas, failure_flag=0)
        response = self.structs.GetExecutionInfoResponse(execution_info=execution_info_ptr)
        return response_header, response

    def storage_read(self, remaining_gas: int, request: CairoStructProxy) -> SyscallFullResponse:
        assert request.reserved == 0, f"Unsupported address domain: {request.reserved}."
        value = self._storage_read(key=cast_to_int(request.key))

        response_header = self.structs.ResponseHeader(gas=remaining_gas, failure_flag=0)
        response = self.structs.StorageReadResponse(value=value)
        return response_header, response

    def storage_write(self, remaining_gas: int, request: CairoStructProxy) -> SyscallFullResponse:
        assert request.reserved == 0, f"Unsupported address domain: {request.reserved}."
        self._storage_write(key=cast_to_int(request.key), value=cast_to_int(request.value))

        response_header = self.structs.ResponseHeader(gas=remaining_gas, failure_flag=0)
        return response_header, tuple()

    def emit_event(self, remaining_gas: int, request: CairoStructProxy) -> SyscallFullResponse:
        keys = self._get_felt_range(start_addr=request.keys_start, end_addr=request.keys_end)
        data = self._get_felt_range(start_addr=request.data_start, end_addr=request.data_end)
        self._emit_event(keys=keys, data=data)

        response_header = self.structs.ResponseHeader(gas=remaining_gas, failure_flag=0)
        return response_header, tuple()

    def replace_class(self, remaining_gas: int, request: CairoStructProxy) -> SyscallFullResponse:
        self._replace_class(class_hash=cast_to_int(request.class_hash))

        response_header = self.structs.ResponseHeader(gas=remaining_gas, failure_flag=0)
        return response_header, tuple()

    def send_message_to_l1(
        self, remaining_gas: int, request: CairoStructProxy
    ) -> SyscallFullResponse:
        payload = self._get_felt_range(
            start_addr=cast(RelocatableValue, request.payload_start),
            end_addr=cast(RelocatableValue, request.payload_end),
        )
        self._send_message_to_l1(to_address=cast_to_int(request.to_address), payload=payload)

        response_header = self.structs.ResponseHeader(gas=remaining_gas, failure_flag=0)
        return response_header, tuple()

    # Application-specific syscall implementation.

    @abstractmethod
    def _call_contract_helper(
        self, remaining_gas: int, request: CairoStructProxy, syscall_name: str
    ) -> CallResult:
        """
        Returns the call's result.

        syscall_name can be "call_contract" or "library_call".
        """

    @abstractmethod
    def _deploy(self, remaining_gas: int, request: CairoStructProxy) -> Tuple[int, CallResult]:
        """
        Returns the address of the newly deployed contract and the constructor call's result.
        Note that the result may contain failures that preceded the constructor invocation, such
        as undeclared class.
        """

    @abstractmethod
    def _get_execution_info_ptr(self) -> RelocatableValue:
        """
        Returns a pointer to the ExecutionInfo struct.
        """

    @abstractmethod
    def _storage_read(self, key: int) -> int:
        """
        Returns the value of the contract's storage at the given key.
        """

    @abstractmethod
    def _storage_write(self, key: int, value: int):
        """
        Specific implementation of the storage_write syscall.
        """

    @abstractmethod
    def _emit_event(self, keys: List[int], data: List[int]):
        """
        Specific implementation of the emit_event syscall.
        """

    @abstractmethod
    def _replace_class(self, class_hash: int):
        """
        Specific implementation of the replace_class syscall.
        """

    @abstractmethod
    def _send_message_to_l1(self, to_address: int, payload: List[int]):
        """
        Specific implementation of the send_message_to_l1 syscall.
        """

    # Internal utilities.

    def _get_required_gas(self, name: str) -> int:
        """
        Returns the remaining required gas for the given syscall.
        """
        total_gas_cost = GasCost[name.upper()].int_value
        # Refund the base amount the was pre-charged.
        return total_gas_cost - GasCost.SYSCALL_BASE.value

    def _handle_out_of_gas(self, initial_gas: int) -> SyscallFullResponse:
        response_header = self.structs.ResponseHeader(gas=initial_gas, failure_flag=1)
        data = [CairoErrorCode.OUT_OF_GAS.to_felt()]
        start = self.allocate_segment(data=data)
        failure_reason = self.structs.FailureReason(start=start, end=start + len(data))

        return response_header, failure_reason

    def _get_felt_range(self, start_addr: Any, end_addr: Any) -> List[int]:
        assert isinstance(start_addr, RelocatableValue)
        assert isinstance(end_addr, RelocatableValue)
        assert start_addr.segment_index == end_addr.segment_index, (
            "Inconsistent start and end segment indices "
            f"({start_addr.segment_index} != {end_addr.segment_index})."
        )

        assert start_addr.offset <= end_addr.offset, (
            "The start offset cannot be greater than the end offset"
            f"({start_addr.offset} > {end_addr.offset})."
        )

        size = end_addr.offset - start_addr.offset
        return self.segments.memory.get_range_as_ints(addr=start_addr, size=size)

    @abstractmethod
    def allocate_segment(self, data: Iterable[MaybeRelocatable]) -> RelocatableValue:
        """
        Allocates and returns a new (read-only) segment with the given data.
        Note that unlike MemorySegmentManager.write_arg, this function doesn't work well with
        recursive input - call allocate_segment for the inner items if needed.
        """

    @abstractmethod
    def _allocate_segment_for_retdata(self, retdata: Iterable[int]) -> RelocatableValue:
        """
        Allocates and returns a new (read-only) segment with the given retdata.
        """

    def _validate_syscall_ptr(self, actual_syscall_ptr: RelocatableValue):
        assert (
            actual_syscall_ptr == self.syscall_ptr
        ), f"Bad syscall_ptr, Expected {self.syscall_ptr}, got {actual_syscall_ptr}."

    def _read_and_validate_request(self, request_struct: CairoStructProxy) -> CairoStructProxy:
        request = self._read_request(request_struct=request_struct)
        validate_runtime_request_type(request_values=request, request_struct=request_struct)
        return request

    def _read_request(self, request_struct: CairoStructProxy) -> CairoStructProxy:
        request = request_struct.from_ptr(memory=self.segments.memory, addr=self.syscall_ptr)
        # Advance syscall pointer.
        self._syscall_ptr = self.syscall_ptr + request_struct.size
        return request

    def _write_response(self, response: tuple):
        # Write response and update syscall pointer.
        self._syscall_ptr = self.segments.write_arg(ptr=self.syscall_ptr, arg=response)


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
        super().__init__(segments=segments, initial_syscall_ptr=initial_syscall_ptr)

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

    # Syscalls.

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
            call_type = CallType.CALL
        elif syscall_name == "library_call":
            contract_address = self.entry_point.contract_address
            caller_address = self.entry_point.caller_address
            call_type = CallType.DELEGATE
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

    def _get_execution_info_ptr(self) -> RelocatableValue:
        if self._execution_info_ptr is None:
            # Prepare block info.
            python_block_info = self.storage.state.block_info
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
            OrderedEvent(order=self.tx_execution_context.n_emitted_events, keys=keys, data=data)
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
            OrderedL2ToL1Message(
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
            call_type=CallType.CALL,
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


class OsExecutionHelper:
    """
    Maintains the information needed for executing transactions in the OS.
    """

    def __init__(
        self,
        tx_execution_infos: List[TransactionExecutionInfo],
        storage_by_address: Mapping[int, OsSingleStarknetStorage],
    ):
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

        # The TransactionExecutionInfo for the transaction currently being executed.
        self.tx_execution_info: Optional[TransactionExecutionInfo] = None

        # Starknet storage-related members.
        self.storage_by_address = storage_by_address

        # A pointer to the Cairo (deprecated) TxInfo struct.
        # This pointer needs to match the DeprecatedTxInfo pointer that is going to be used during
        # the system call validation by the Starknet OS.
        # Set during enter_tx.
        self.tx_info_ptr: Optional[RelocatableValue] = None

        # A pointer to the Cairo ExecutionInfo struct of the current call.
        # This pointer needs to match the ExecutionInfo pointer that is going to be used during the
        # system call validation by the StarkNet OS.
        # Set during enter_call.
        self.call_execution_info_ptr: Optional[RelocatableValue] = None

    @property
    def call_info(self) -> CallInfo:
        assert self._call_info is not None
        return self._call_info

    def start_tx(self, tx_info_ptr: Optional[RelocatableValue]):
        """
        Called when starting the execution of a transaction.

        'tx_info_ptr' is a pointer to the TxInfo struct corresponding to said transaction.
        """
        assert self.tx_info_ptr is None
        self.tx_info_ptr = tx_info_ptr

        assert self.tx_execution_info is None
        self.tx_execution_info = next(self.tx_execution_info_iterator)
        self.call_iterator = self.tx_execution_info.gen_call_iterator()

    def end_tx(self):
        """
        Called after the execution of the current transaction complete.
        """
        assert_exhausted(iterator=self.call_iterator)
        self.tx_info_ptr = None
        assert self.tx_execution_info is not None
        self.tx_execution_info = None

    def assert_interators_exhausted(self):
        assert_exhausted(iterator=self.deployed_contracts_iterator)
        assert_exhausted(iterator=self.result_iterator)
        assert_exhausted(iterator=self.execute_code_read_iterator)

    def enter_call(self, execution_info_ptr: Optional[RelocatableValue]):
        assert self.call_execution_info_ptr is None
        self.call_execution_info_ptr = execution_info_ptr

        self.assert_interators_exhausted()

        assert self._call_info is None
        self._call_info = next(self.call_iterator)

        self.deployed_contracts_iterator = (
            call.contract_address
            for call in self.call_info.internal_calls
            if call.entry_point_type is EntryPointType.CONSTRUCTOR
        )
        self.result_iterator = (call.result() for call in self.call_info.internal_calls)
        self.execute_code_read_iterator = iter(self.call_info.storage_read_values)

    def exit_call(self):
        self.call_execution_info_ptr = None

        self.assert_interators_exhausted()
        assert self._call_info is not None
        self._call_info = None

    def skip_call(self):
        """
        Called when skipping the execution of a call.
        It replaces a call to enter_call and exit_call.
        """
        self.enter_call(execution_info_ptr=None)
        self.exit_call()

    def skip_tx(self):
        """
        Called when skipping the execution of a transaction.
        It replaces a call to start_tx and end_tx.
        """
        self.start_tx(tx_info_ptr=None)
        self.end_tx()


class OsSyscallHandler(SyscallHandlerBase):
    """
    A handler for system calls; used by the GpsAmbassador in the OS run execution.
    """

    def __init__(
        self,
        execution_helper: OsExecutionHelper,
        # Note that a non-optional segments must be set before using the SyscallHandler.
        segments: Optional[MemorySegmentManager] = None,
    ):
        super().__init__(segments=segments, initial_syscall_ptr=None)
        self.execution_helper = execution_helper

    def set_segments(self, segments: MemorySegmentManager):
        assert self._segments is None, "segments is already set."
        self._segments = segments

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

    def _get_execution_info_ptr(self) -> RelocatableValue:
        assert (
            self.execution_helper.call_execution_info_ptr is not None
        ), "ExecutionInfo pointer is not set."
        return self.execution_helper.call_execution_info_ptr

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


# Deprecated handlers.


class DeprecatedSysCallHandlerBase(ABC):
    """
    Base class for execution of system calls in the StarkNet OS.
    """

    def __init__(self, block_info: BlockInfo, segments: Optional[MemorySegmentManager]):
        self._segments = segments
        self.block_info = block_info

        self.syscall_structs, self.syscall_info = get_deprecated_syscall_structs_and_info()

    def set_segments(self, segments: MemorySegmentManager):
        assert self._segments is None, "segments is already set."
        self._segments = segments

    @property
    def segments(self) -> MemorySegmentManager:
        assert self._segments is not None, "segments must be set before using the SysCallHandler."
        return self._segments

    # Public API.

    # Segments argument is kept in public API for backward compatibility.
    def call_contract(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        self._call_contract_and_write_response(
            syscall_name="call_contract", syscall_ptr=syscall_ptr
        )

    def delegate_call(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        self._call_contract_and_write_response(
            syscall_name="delegate_call", syscall_ptr=syscall_ptr
        )

    def delegate_l1_handler(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        self._call_contract_and_write_response(
            syscall_name="delegate_l1_handler", syscall_ptr=syscall_ptr
        )

    def deploy(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the deploy system call.
        """
        contract_address = self._deploy(syscall_ptr=syscall_ptr)
        response = self.syscall_structs.DeployResponse(
            contract_address=contract_address,
            constructor_retdata_size=0,
            constructor_retdata=0,
        )
        self._write_syscall_response(
            syscall_name="Deploy", response=response, syscall_ptr=syscall_ptr
        )

    def emit_event(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        return

    def get_caller_address(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the get_caller_address system call.
        """
        caller_address = self._get_caller_address(syscall_ptr=syscall_ptr)

        response = self.syscall_structs.GetCallerAddressResponse(caller_address=caller_address)
        self._write_syscall_response(
            syscall_name="GetCallerAddress", response=response, syscall_ptr=syscall_ptr
        )

    def get_contract_address(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        contract_address = self._get_contract_address(syscall_ptr=syscall_ptr)

        response = self.syscall_structs.GetContractAddressResponse(
            contract_address=contract_address
        )
        self._write_syscall_response(
            syscall_name="GetContractAddress", response=response, syscall_ptr=syscall_ptr
        )

    def get_block_number(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the get_block_number system call.
        """
        self._read_and_validate_syscall_request(
            syscall_name="get_block_number", syscall_ptr=syscall_ptr
        )

        block_number = self.block_info.block_number

        response = self.syscall_structs.GetBlockNumberResponse(block_number=block_number)
        self._write_syscall_response(
            syscall_name="GetBlockNumber", response=response, syscall_ptr=syscall_ptr
        )

    def get_sequencer_address(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the get_sequencer_address system call.
        """
        self._read_and_validate_syscall_request(
            syscall_name="get_sequencer_address", syscall_ptr=syscall_ptr
        )

        response = self.syscall_structs.GetSequencerAddressResponse(
            sequencer_address=0
            if self.block_info.sequencer_address is None
            else self.block_info.sequencer_address
        )
        self._write_syscall_response(
            syscall_name="GetSequencerAddress", response=response, syscall_ptr=syscall_ptr
        )

    def get_tx_info(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the get_tx_info system call.
        """
        self._read_and_validate_syscall_request(syscall_name="get_tx_info", syscall_ptr=syscall_ptr)

        response = self.syscall_structs.GetTxInfoResponse(tx_info=self._get_tx_info_ptr())
        self._write_syscall_response(
            syscall_name="GetTxInfo", response=response, syscall_ptr=syscall_ptr
        )

    def send_message_to_l1(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        return

    def get_block_timestamp(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the get_block_timestamp system call.
        """
        self._read_and_validate_syscall_request(
            syscall_name="get_block_timestamp", syscall_ptr=syscall_ptr
        )

        block_timestamp = self.block_info.block_timestamp

        response = self.syscall_structs.GetBlockTimestampResponse(block_timestamp=block_timestamp)
        self._write_syscall_response(
            syscall_name="GetBlockTimestamp", response=response, syscall_ptr=syscall_ptr
        )

    def get_tx_signature(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the get_tx_signature system call.
        """
        self._read_and_validate_syscall_request(
            syscall_name="get_tx_signature", syscall_ptr=syscall_ptr
        )
        tx_info_ptr = self._get_tx_info_ptr()
        tx_info = self.syscall_structs.TxInfo.from_ptr(
            memory=self.segments.memory, addr=tx_info_ptr
        )
        response = self.syscall_structs.GetTxSignatureResponse(
            signature_len=tx_info.signature_len, signature=tx_info.signature
        )

        self._write_syscall_response(
            syscall_name="GetTxSignature", response=response, syscall_ptr=syscall_ptr
        )

    def library_call(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        self._call_contract_and_write_response(syscall_name="library_call", syscall_ptr=syscall_ptr)

    def library_call_l1_handler(
        self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ):
        self._call_contract_and_write_response(
            syscall_name="library_call_l1_handler", syscall_ptr=syscall_ptr
        )

    def replace_class(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the replace_class system call.
        """
        request = self._read_and_validate_syscall_request(
            syscall_name="replace_class", syscall_ptr=syscall_ptr
        )
        self._replace_class(class_hash=cast_to_int(request.class_hash))

    def storage_read(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the storage_read system call.
        """
        request = self._read_and_validate_syscall_request(
            syscall_name="storage_read", syscall_ptr=syscall_ptr
        )

        value = self._storage_read(cast_to_int(request.address))
        response = self.syscall_structs.StorageReadResponse(value=value)

        self._write_syscall_response(
            syscall_name="StorageRead", response=response, syscall_ptr=syscall_ptr
        )

    def storage_write(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the storage_write system call.
        """
        request = self._read_and_validate_syscall_request(
            syscall_name="storage_write", syscall_ptr=syscall_ptr
        )
        self._storage_write(address=cast_to_int(request.address), value=cast_to_int(request.value))

    # Private helpers.

    @abstractmethod
    def _get_tx_info_ptr(self):
        """
        Returns a pointer to the TxInfo struct.
        """

    @abstractmethod
    def _deploy(self, syscall_ptr: RelocatableValue) -> int:
        """
        Returns the address of the newly deployed contract.
        """

    def _read_syscall_request(
        self, syscall_name: str, syscall_ptr: RelocatableValue
    ) -> CairoStructProxy:
        """
        Returns the system call request written in the syscall segment, starting at syscall_ptr.
        """
        syscall_info = self.syscall_info[syscall_name]
        return syscall_info.syscall_request_struct.from_ptr(
            memory=self.segments.memory, addr=syscall_ptr
        )

    @abstractmethod
    def _read_and_validate_syscall_request(
        self, syscall_name: str, syscall_ptr: RelocatableValue
    ) -> CairoStructProxy:
        """
        Returns the system call request written in the syscall segment, starting at syscall_ptr.
        Performs validations on the request.
        """

    def _write_syscall_response(
        self,
        syscall_name: str,
        response: CairoStructProxy,
        syscall_ptr: RelocatableValue,
    ):
        assert (
            camel_to_snake_case(syscall_name) in self.syscall_info
        ), f"Illegal system call {syscall_name}."

        syscall_struct: CairoStructProxy = getattr(self.syscall_structs, syscall_name)
        response_offset = syscall_struct.struct_definition_.members["response"].offset
        self.segments.write_arg(ptr=syscall_ptr + response_offset, arg=response)

    @abstractmethod
    def _call_contract(self, syscall_ptr: RelocatableValue, syscall_name: str) -> CallResult:
        """
        Returns the call's result.

        syscall_name can be "call_contract", "delegate_call", "delegate_l1_handler", "library_call"
        or "library_call_l1_handler".
        """

    def _call_contract_and_write_response(self, syscall_name: str, syscall_ptr: RelocatableValue):
        """
        Executes the contract call and fills the CallContractResponse struct.
        """
        result = self._call_contract(syscall_ptr=syscall_ptr, syscall_name=syscall_name)
        assert not result.failure_flag, "Unexpected reverted call."
        response = self.syscall_structs.CallContractResponse(
            retdata_size=len(result.retdata), retdata=self._allocate_segment(data=result.retdata)
        )
        self._write_syscall_response(
            syscall_name="CallContract", response=response, syscall_ptr=syscall_ptr
        )

    @abstractmethod
    def _get_caller_address(self, syscall_ptr: RelocatableValue) -> int:
        """
        Specific implementation of the get_caller_address system call.
        """

    @abstractmethod
    def _get_contract_address(self, syscall_ptr: RelocatableValue) -> int:
        """
        Specific implementation of the get_contract_address system call.
        """

    @abstractmethod
    def _replace_class(self, class_hash: int):
        """
        replaces the running contracts class hash with the given hash.
        """

    @abstractmethod
    def _storage_read(self, address: int) -> int:
        """
        Returns the value of the contract's storage at the given address.
        """

    @abstractmethod
    def _storage_write(self, address: int, value: int):
        """
        Write the value to the contract's storage at the given address.
        """

    @abstractmethod
    def _allocate_segment(self, data: Iterable[MaybeRelocatable]) -> RelocatableValue:
        """
        Allocates and returns a new (read-only) segment with the given data.
        Note that unlike MemorySegmentManager.write_arg, this function doesn't work well with
        recursive input - call _allocate_segment for the inner items if needed.
        """


class DeprecatedBlSyscallHandler(DeprecatedSysCallHandlerBase):
    """
    The SysCallHandler implementation that is used by the batcher.
    """

    def __init__(
        self,
        execute_entry_point_cls: Type[ExecuteEntryPointBase],
        tx_execution_context: TransactionExecutionContext,
        state: SyncState,
        resources_manager: ExecutionResourcesManager,
        caller_address: int,
        contract_address: int,
        general_config: StarknetGeneralConfig,
        initial_syscall_ptr: RelocatableValue,
        segments: MemorySegmentManager,
    ):
        super().__init__(block_info=state.block_info, segments=segments)

        # Configuration objects.
        self.general_config = general_config

        # Execution-related objects.
        self.execute_entry_point_cls = execute_entry_point_cls
        self.tx_execution_context = tx_execution_context
        self.sync_state = state
        self.resources_manager = resources_manager
        self.caller_address = caller_address
        self.contract_address = contract_address

        # Storage-related members.
        self.starknet_storage = ContractStorageState(
            state=self.sync_state, contract_address=contract_address
        )

        # Internal calls executed by the current contract call.
        self.internal_calls: List[CallInfo] = []
        # Events emitted by the current contract call.
        self.events: List[OrderedEvent] = []
        # Messages sent by the current contract call to L1.
        self.l2_to_l1_messages: List[OrderedL2ToL1Message] = []

        # Kept for validations during the run.
        self.expected_syscall_ptr = initial_syscall_ptr

        # A pointer to the Cairo TxInfo struct.
        self.tx_info_ptr: Optional[RelocatableValue] = None

        # A list of dynamically allocated segments that are expected to be read-only.
        self.read_only_segments: List[Tuple[RelocatableValue, int]] = []

    def _allocate_segment(self, data: Iterable[MaybeRelocatable]) -> RelocatableValue:
        segment_start = self.segments.add()
        segment_end = self.segments.write_arg(ptr=segment_start, arg=data)
        self.read_only_segments.append((segment_start, segment_end - segment_start))
        return segment_start

    def _count_syscall(self, syscall_name: str):
        previous_syscall_count = self.resources_manager.syscall_counter.get(syscall_name, 0)
        self.resources_manager.syscall_counter[syscall_name] = previous_syscall_count + 1

    def _read_and_validate_syscall_request(
        self, syscall_name: str, syscall_ptr: RelocatableValue
    ) -> CairoStructProxy:
        """
        Returns the system call request written in the syscall segment, starting at syscall_ptr.
        Performs validations on the request.
        """
        # Update syscall count.
        self._count_syscall(syscall_name=syscall_name)

        request = self._read_syscall_request(syscall_name=syscall_name, syscall_ptr=syscall_ptr)

        assert (
            syscall_ptr == self.expected_syscall_ptr
        ), f"Bad syscall_ptr, Expected {self.expected_syscall_ptr}, got {syscall_ptr}."

        syscall_info = self.syscall_info[syscall_name]
        self.expected_syscall_ptr += syscall_info.syscall_size

        selector = request.selector
        assert isinstance(selector, int), (
            f"The selector argument to syscall {syscall_name} is of unexpected type. "
            f"Expected: int; got: {type(selector).__name__}."
        )
        assert (
            selector == syscall_info.selector
        ), f"Bad syscall selector, expected {syscall_info.selector}. Got: {selector}"

        validate_runtime_request_type(
            request_values=request, request_struct=syscall_info.syscall_request_struct
        )

        return request

    def _call_contract(self, syscall_ptr: RelocatableValue, syscall_name: str) -> CallResult:
        # Parse request and prepare the call.
        request = self._read_and_validate_syscall_request(
            syscall_name=syscall_name, syscall_ptr=syscall_ptr
        )
        calldata = self.segments.memory.get_range_as_ints(
            addr=request.calldata, size=request.calldata_size
        )

        code_address: Optional[int] = None
        class_hash: Optional[int] = None
        if syscall_name == "call_contract":
            code_address = cast_to_int(request.contract_address)
            contract_address = code_address
            caller_address = self.contract_address
            entry_point_type = EntryPointType.EXTERNAL
            call_type = CallType.CALL
        elif syscall_name == "delegate_call":
            code_address = cast_to_int(request.contract_address)
            contract_address = self.contract_address
            caller_address = self.caller_address
            entry_point_type = EntryPointType.EXTERNAL
            call_type = CallType.DELEGATE
        elif syscall_name == "delegate_l1_handler":
            code_address = cast_to_int(request.contract_address)
            contract_address = self.contract_address
            caller_address = self.caller_address
            entry_point_type = EntryPointType.L1_HANDLER
            call_type = CallType.DELEGATE
        elif syscall_name == "library_call":
            class_hash = cast_to_int(request.class_hash)
            contract_address = self.contract_address
            caller_address = self.caller_address
            entry_point_type = EntryPointType.EXTERNAL
            call_type = CallType.DELEGATE
        elif syscall_name == "library_call_l1_handler":
            class_hash = cast_to_int(request.class_hash)
            contract_address = self.contract_address
            caller_address = self.caller_address
            entry_point_type = EntryPointType.L1_HANDLER
            call_type = CallType.DELEGATE
        else:
            raise NotImplementedError(f"Unsupported call type {syscall_name}.")

        call = self.execute_entry_point_cls(
            call_type=call_type,
            class_hash=class_hash,
            contract_address=contract_address,
            code_address=code_address,
            entry_point_selector=cast_to_int(request.function_selector),
            initial_gas=GasCost.INITIAL.value,
            entry_point_type=entry_point_type,
            calldata=calldata,
            caller_address=caller_address,
        )

        return self.execute_entry_point(call=call)

    def _deploy(self, syscall_ptr: RelocatableValue) -> int:
        """
        Initializes and runs the constructor of the new contract.
        Returns the address of the newly deployed contract.
        """
        request = self._read_and_validate_syscall_request(
            syscall_name="deploy", syscall_ptr=syscall_ptr
        )
        assert request.deploy_from_zero in [
            0,
            1,
        ], "The deploy_from_zero field in the deploy system call must be 0 or 1."
        constructor_calldata = self.segments.memory.get_range_as_ints(
            addr=cast(RelocatableValue, request.constructor_calldata),
            size=cast_to_int(request.constructor_calldata_size),
        )
        class_hash = cast_to_int(request.class_hash)

        deployer_address = self.contract_address if request.deploy_from_zero == 0 else 0
        contract_address = calculate_contract_address_from_hash(
            salt=cast_to_int(request.contract_address_salt),
            class_hash=class_hash,
            constructor_calldata=constructor_calldata,
            deployer_address=deployer_address,
        )

        # Instantiate the contract.
        self.sync_state.deploy_contract(contract_address=contract_address, class_hash=class_hash)

        self.execute_constructor_entry_point(
            contract_address=contract_address,
            class_hash=class_hash,
            constructor_calldata=constructor_calldata,
        )

        return contract_address

    def execute_constructor_entry_point(
        self, contract_address: int, class_hash: int, constructor_calldata: List[int]
    ):
        contract_class = self.sync_state.get_compiled_class_by_class_hash(class_hash=class_hash)
        constructor_entry_points = contract_class.entry_points_by_type[EntryPointType.CONSTRUCTOR]
        if len(constructor_entry_points) == 0:
            # Contract has no constructor.
            assert (
                len(constructor_calldata) == 0
            ), "Cannot pass calldata to a contract with no constructor."

            call_info = CallInfo.empty_constructor_call(
                contract_address=contract_address,
                caller_address=self.contract_address,
                class_hash=class_hash,
            )
            self.internal_calls.append(call_info)

            return

        call = self.execute_entry_point_cls(
            call_type=CallType.CALL,
            class_hash=None,
            contract_address=contract_address,
            code_address=contract_address,
            entry_point_selector=CONSTRUCTOR_ENTRY_POINT_SELECTOR,
            initial_gas=GasCost.INITIAL.value,
            entry_point_type=EntryPointType.CONSTRUCTOR,
            calldata=constructor_calldata,
            caller_address=self.contract_address,
        )
        self.execute_entry_point(call=call)

    def execute_entry_point(self, call: ExecuteEntryPointBase) -> CallResult:
        with wrap_with_handler_exception(call=call):
            # Execute contract call.
            call_info = call.execute(
                state=self.sync_state,
                resources_manager=self.resources_manager,
                tx_execution_context=self.tx_execution_context,
                general_config=self.general_config,
            )

        # Update execution info.
        self.internal_calls.append(call_info)

        return call_info.result()

    def emit_event(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the emit_event system call.
        """
        request = self._read_and_validate_syscall_request(
            syscall_name="emit_event", syscall_ptr=syscall_ptr
        )

        self.events.append(
            OrderedEvent(
                order=self.tx_execution_context.n_emitted_events,
                keys=self.segments.memory.get_range_as_ints(
                    addr=cast(RelocatableValue, request.keys), size=cast_to_int(request.keys_len)
                ),
                data=self.segments.memory.get_range_as_ints(
                    addr=cast(RelocatableValue, request.data), size=cast_to_int(request.data_len)
                ),
            )
        )

        # Update events count.
        self.tx_execution_context.n_emitted_events += 1

    def _get_tx_info_ptr(self) -> RelocatableValue:
        if self.tx_info_ptr is None:
            tx_info = self.syscall_structs.TxInfo(
                version=self.tx_execution_context.version,
                account_contract_address=self.tx_execution_context.account_contract_address,
                max_fee=self.tx_execution_context.max_fee,
                transaction_hash=self.tx_execution_context.transaction_hash,
                signature_len=len(self.tx_execution_context.signature),
                signature=self._allocate_segment(data=self.tx_execution_context.signature),
                chain_id=self.general_config.chain_id.value,
                nonce=self.tx_execution_context.nonce,
            )
            self.tx_info_ptr = self._allocate_segment(data=tx_info)

        return self.tx_info_ptr

    def send_message_to_l1(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        request = self._read_and_validate_syscall_request(
            syscall_name="send_message_to_l1", syscall_ptr=syscall_ptr
        )
        payload = self.segments.memory.get_range_as_ints(
            addr=cast(RelocatableValue, request.payload_ptr), size=cast_to_int(request.payload_size)
        )

        self.l2_to_l1_messages.append(
            # Note that the constructor of OrderedL2ToL1Message might fail as it is
            # more restrictive than the Cairo code.
            OrderedL2ToL1Message(
                order=self.tx_execution_context.n_sent_messages,
                to_address=cast_to_int(request.to_address),
                payload=payload,
            )
        )

        # Update messages count.
        self.tx_execution_context.n_sent_messages += 1

    def _get_caller_address(self, syscall_ptr: RelocatableValue) -> int:
        self._read_and_validate_syscall_request(
            syscall_name="get_caller_address", syscall_ptr=syscall_ptr
        )

        return self.caller_address

    def _get_contract_address(self, syscall_ptr: RelocatableValue) -> int:
        self._read_and_validate_syscall_request(
            syscall_name="get_contract_address", syscall_ptr=syscall_ptr
        )

        return self.contract_address

    def _replace_class(self, class_hash: int):
        # Assert the replacement class is valid (by reading it).
        self.sync_state.get_compiled_class_by_class_hash(class_hash=class_hash)

        # Replace the class.
        self.sync_state.set_class_hash_at(
            contract_address=self.contract_address, class_hash=class_hash
        )

    def _storage_read(self, address: int) -> int:
        return self.starknet_storage.read(address=address)

    def _storage_write(self, address: int, value: int):
        # Read the value before the write operation in order to log it in the read_values list.
        # This value is needed to create the DictAccess while executing the corresponding
        # storage_write system call.
        self.starknet_storage.read(address=address)

        self.starknet_storage.write(address=address, value=value)

    def validate_read_only_segments(self, runner: CairoFunctionRunner):
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

    def post_run(self, runner: CairoFunctionRunner, syscall_stop_ptr: MaybeRelocatable):
        """
        Performs post run syscall related tasks.
        """
        expected_stop_ptr = self.expected_syscall_ptr
        stark_assert(
            syscall_stop_ptr == expected_stop_ptr,
            code=StarknetErrorCode.SECURITY_ERROR,
            message=f"Bad syscall_stop_ptr, Expected {expected_stop_ptr}, got {syscall_stop_ptr}.",
        )

        self.validate_read_only_segments(runner=runner)


class DeprecatedOsSysCallHandler(DeprecatedSysCallHandlerBase):
    """
    The SysCallHandler implementation that is used by the gps ambassador.
    """

    def __init__(
        self,
        execution_helper: OsExecutionHelper,
        block_info: BlockInfo,
        # Note that a non-optional segments must be set before using the SysCallHandler.
        segments: Optional[MemorySegmentManager] = None,
    ):
        super().__init__(block_info=block_info, segments=segments)
        self.execution_helper = execution_helper

    def _read_and_validate_syscall_request(
        self, syscall_name: str, syscall_ptr: RelocatableValue
    ) -> CairoStructProxy:
        """
        Returns the system call request written in the syscall segment, starting at syscall_ptr.
        Does not perform validations on the request, since it was validated in the BL.
        """
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

    def _get_caller_address(self, syscall_ptr: RelocatableValue) -> int:
        return self.execution_helper.call_info.caller_address

    def _get_contract_address(self, syscall_ptr: RelocatableValue) -> int:
        return self.execution_helper.call_info.contract_address

    def _get_tx_info_ptr(self) -> RelocatableValue:
        assert self.execution_helper.tx_info_ptr is not None
        return self.execution_helper.tx_info_ptr

    def _replace_class(self, class_hash: int):
        return

    def _storage_read(self, address: int) -> int:
        return next(self.execution_helper.execute_code_read_iterator)

    def _storage_write(self, address: int, value: int):
        # Advance execute_code_read_iterators since the previous storage value is written
        # in each write operation. See DeprecatedBlSyscallHandler._storage_write().
        next(self.execution_helper.execute_code_read_iterator)
