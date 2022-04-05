import asyncio
import contextlib
import dataclasses
from abc import ABC, abstractmethod
from typing import (
    Callable,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.common.structs import CairoStructFactory, CairoStructProxy
from starkware.cairo.lang.compiler.ast.cairo_types import CairoType, TypeFelt, TypePointer
from starkware.cairo.lang.compiler.identifier_definition import StructDefinition
from starkware.cairo.lang.vm.memory_segments import MemorySegmentManager
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.python.utils import assert_exhausted, camel_to_snake_case, safe_zip
from starkware.starknet.business_logic.execution.execute_entry_point_base import (
    ExecuteEntryPointBase,
)
from starkware.starknet.business_logic.execution.objects import (
    CallInfo,
    OrderedEvent,
    OrderedL2ToL1Message,
    TransactionExecutionContext,
    TransactionExecutionInfo,
)
from starkware.starknet.business_logic.state.state import BlockInfo, CarriedState
from starkware.starknet.core.os.os_program import get_os_program
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.services.api.contract_definition import EntryPointType
from starkware.starknet.storage.starknet_storage import (
    BusinessLogicStarknetStorage,
    StarknetStorageInterface,
)
from starkware.starkware_utils.error_handling import StarkException, stark_assert

TCallable = TypeVar("TCallable", bound=Callable)


@dataclasses.dataclass
class SysCallInfo:
    selector: int
    syscall_request_struct: CairoStructProxy
    # The size of the system call struct including both the request and the response.
    syscall_size: int


@dataclasses.dataclass
class HandlerException(Exception):
    """
    Base class for exceptions thrown by the syscall handler.
    """

    called_contract_address: int
    stark_exception: StarkException


class SysCallHandlerBase(ABC):
    """
    base class for execution of system calls in the StarkNet OS.
    """

    def __init__(self, general_config: StarknetGeneralConfig):
        os_program = get_os_program()

        # StarkNet general configuration.
        self.general_config = general_config

        self.structs = CairoStructFactory.from_program(
            program=os_program,
            additional_imports=[
                "starkware.starknet.common.syscalls.CallContract",
                "starkware.starknet.common.syscalls.CallContractRequest",
                "starkware.starknet.common.syscalls.CallContractResponse",
                "starkware.starknet.common.syscalls.EmitEvent",
                "starkware.starknet.common.syscalls.GetCallerAddress",
                "starkware.starknet.common.syscalls.GetCallerAddressRequest",
                "starkware.starknet.common.syscalls.GetCallerAddressResponse",
                "starkware.starknet.common.syscalls.GetSequencerAddress",
                "starkware.starknet.common.syscalls.GetSequencerAddressRequest",
                "starkware.starknet.common.syscalls.GetSequencerAddressResponse",
                "starkware.starknet.common.syscalls.GetBlockNumber",
                "starkware.starknet.common.syscalls.GetBlockNumberRequest",
                "starkware.starknet.common.syscalls.GetBlockNumberResponse",
                "starkware.starknet.common.syscalls.GetBlockTimestamp",
                "starkware.starknet.common.syscalls.GetBlockTimestampRequest",
                "starkware.starknet.common.syscalls.GetBlockTimestampResponse",
                "starkware.starknet.common.syscalls.GetContractAddress",
                "starkware.starknet.common.syscalls.GetContractAddressRequest",
                "starkware.starknet.common.syscalls.GetContractAddressResponse",
                "starkware.starknet.common.syscalls.GetTxInfo",
                "starkware.starknet.common.syscalls.GetTxInfoRequest",
                "starkware.starknet.common.syscalls.GetTxInfoResponse",
                "starkware.starknet.common.syscalls.GetTxSignature",
                "starkware.starknet.common.syscalls.GetTxSignatureRequest",
                "starkware.starknet.common.syscalls.GetTxSignatureResponse",
                "starkware.starknet.common.syscalls.SendMessageToL1SysCall",
                "starkware.starknet.common.syscalls.StorageRead",
                "starkware.starknet.common.syscalls.StorageReadRequest",
                "starkware.starknet.common.syscalls.StorageReadResponse",
                "starkware.starknet.common.syscalls.StorageWrite",
                "starkware.starknet.common.syscalls.TxInfo",
            ],
        ).structs

        def get_selector(syscall_name: str):
            return os_program.get_const(
                name=f"starkware.starknet.common.syscalls.{syscall_name.upper()}_SELECTOR",
                full_name_lookup=True,
            )

        self.syscall_info = {
            "call_contract": SysCallInfo(
                selector=get_selector("call_contract"),
                syscall_request_struct=self.structs.CallContractRequest,
                syscall_size=self.structs.CallContract.size,
            ),
            "emit_event": SysCallInfo(
                selector=get_selector("emit_event"),
                syscall_request_struct=self.structs.EmitEvent,
                syscall_size=self.structs.EmitEvent.size,
            ),
            "delegate_call": SysCallInfo(
                selector=get_selector("delegate_call"),
                syscall_request_struct=self.structs.CallContractRequest,
                syscall_size=self.structs.CallContract.size,
            ),
            "delegate_l1_handler": SysCallInfo(
                selector=get_selector("delegate_l1_handler"),
                syscall_request_struct=self.structs.CallContractRequest,
                syscall_size=self.structs.CallContract.size,
            ),
            "get_caller_address": SysCallInfo(
                selector=get_selector("get_caller_address"),
                syscall_request_struct=self.structs.GetCallerAddressRequest,
                syscall_size=self.structs.GetCallerAddress.size,
            ),
            "get_sequencer_address": SysCallInfo(
                selector=get_selector("get_sequencer_address"),
                syscall_request_struct=self.structs.GetSequencerAddressRequest,
                syscall_size=self.structs.GetSequencerAddress.size,
            ),
            "get_block_number": SysCallInfo(
                selector=get_selector("get_block_number"),
                syscall_request_struct=self.structs.GetBlockNumberRequest,
                syscall_size=self.structs.GetBlockNumber.size,
            ),
            "get_block_timestamp": SysCallInfo(
                selector=get_selector("get_block_timestamp"),
                syscall_request_struct=self.structs.GetBlockTimestampRequest,
                syscall_size=self.structs.GetBlockTimestamp.size,
            ),
            "get_contract_address": SysCallInfo(
                selector=get_selector("get_contract_address"),
                syscall_request_struct=self.structs.GetContractAddressRequest,
                syscall_size=self.structs.GetContractAddress.size,
            ),
            "get_tx_info": SysCallInfo(
                selector=get_selector("get_tx_info"),
                syscall_request_struct=self.structs.GetTxInfoRequest,
                syscall_size=self.structs.GetTxInfo.size,
            ),
            "send_message_to_l1": SysCallInfo(
                selector=get_selector("send_message_to_l1"),
                syscall_request_struct=self.structs.SendMessageToL1SysCall,
                syscall_size=self.structs.SendMessageToL1SysCall.size,
            ),
            "get_tx_signature": SysCallInfo(
                selector=get_selector("get_tx_signature"),
                syscall_request_struct=self.structs.GetTxSignatureRequest,
                syscall_size=self.structs.GetTxSignature.size,
            ),
            "storage_read": SysCallInfo(
                selector=get_selector("storage_read"),
                syscall_request_struct=self.structs.StorageReadRequest,
                syscall_size=self.structs.StorageRead.size,
            ),
            "storage_write": SysCallInfo(
                selector=get_selector("storage_write"),
                syscall_request_struct=self.structs.StorageWrite,
                syscall_size=self.structs.StorageWrite.size,
            ),
        }

    # Public API.

    def call_contract(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        self._call_contract_and_write_response(
            syscall_name="call_contract",
            segments=segments,
            syscall_ptr=syscall_ptr,
        )

    def delegate_call(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        self._call_contract_and_write_response(
            syscall_name="delegate_call",
            segments=segments,
            syscall_ptr=syscall_ptr,
        )

    def delegate_l1_handler(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        self._call_contract_and_write_response(
            syscall_name="delegate_l1_handler",
            segments=segments,
            syscall_ptr=syscall_ptr,
        )

    def emit_event(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        return

    def get_caller_address(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the get_caller_address system call.
        """
        caller_address = self._get_caller_address(segments=segments, syscall_ptr=syscall_ptr)

        response = self.structs.GetCallerAddressResponse(caller_address=caller_address)
        self._write_syscall_response(
            syscall_name="GetCallerAddress",
            response=response,
            segments=segments,
            syscall_ptr=syscall_ptr,
        )

    def get_contract_address(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        contract_address = self._get_contract_address(segments=segments, syscall_ptr=syscall_ptr)

        response = self.structs.GetContractAddressResponse(contract_address=contract_address)
        self._write_syscall_response(
            syscall_name="GetContractAddress",
            response=response,
            segments=segments,
            syscall_ptr=syscall_ptr,
        )

    def get_block_number(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the get_block_number system call.
        """
        self._read_and_validate_syscall_request(
            syscall_name="get_block_number", segments=segments, syscall_ptr=syscall_ptr
        )

        block_number = self._get_block_number()

        response = self.structs.GetBlockNumberResponse(block_number=block_number)
        self._write_syscall_response(
            syscall_name="GetBlockNumber",
            response=response,
            segments=segments,
            syscall_ptr=syscall_ptr,
        )

    def get_sequencer_address(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the get_sequencer_address system call.
        """
        self._read_and_validate_syscall_request(
            syscall_name="get_sequencer_address", segments=segments, syscall_ptr=syscall_ptr
        )

        response = self.structs.GetSequencerAddressResponse(
            sequencer_address=self.general_config.sequencer_address
        )
        self._write_syscall_response(
            syscall_name="GetSequencerAddress",
            response=response,
            segments=segments,
            syscall_ptr=syscall_ptr,
        )

    def get_tx_info(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the get_tx_info system call.
        """
        self._read_and_validate_syscall_request(
            syscall_name="get_tx_info", segments=segments, syscall_ptr=syscall_ptr
        )

        response = self.structs.GetTxInfoResponse(tx_info=self._get_tx_info_ptr(segments=segments))
        self._write_syscall_response(
            syscall_name="GetTxInfo",
            response=response,
            segments=segments,
            syscall_ptr=syscall_ptr,
        )

    def send_message_to_l1(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        return

    def get_block_timestamp(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the get_block_timestamp system call.
        """
        self._read_and_validate_syscall_request(
            syscall_name="get_block_timestamp", segments=segments, syscall_ptr=syscall_ptr
        )

        block_timestamp = self._get_block_timestamp()

        response = self.structs.GetBlockTimestampResponse(block_timestamp=block_timestamp)
        self._write_syscall_response(
            syscall_name="GetBlockTimestamp",
            response=response,
            segments=segments,
            syscall_ptr=syscall_ptr,
        )

    def get_tx_signature(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the get_tx_signature system call.
        """
        self._read_and_validate_syscall_request(
            syscall_name="get_tx_signature", segments=segments, syscall_ptr=syscall_ptr
        )
        tx_info_ptr = self._get_tx_info_ptr(segments=segments)
        tx_info = self.structs.TxInfo.from_ptr(memory=segments.memory, addr=tx_info_ptr)
        response = self.structs.GetTxSignatureResponse(
            signature_len=tx_info.signature_len, signature=tx_info.signature
        )

        self._write_syscall_response(
            syscall_name="GetTxSignature",
            response=response,
            segments=segments,
            syscall_ptr=syscall_ptr,
        )

    @abstractmethod
    def _get_tx_info_ptr(self, segments: MemorySegmentManager):
        """
        Returns a pointer to the TxInfo struct.
        """

    def storage_read(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the storage_read system call.
        """
        request = self._read_and_validate_syscall_request(
            syscall_name="storage_read", segments=segments, syscall_ptr=syscall_ptr
        )

        value = self._storage_read(cast(int, request.address))
        response = self.structs.StorageReadResponse(value=value)

        self._write_syscall_response(
            syscall_name="StorageRead",
            response=response,
            segments=segments,
            syscall_ptr=syscall_ptr,
        )

    def storage_write(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the storage_write system call.
        """
        request = self._read_and_validate_syscall_request(
            syscall_name="storage_write", segments=segments, syscall_ptr=syscall_ptr
        )
        self._storage_write(address=cast(int, request.address), value=cast(int, request.value))

    def enter_call(self):
        raise NotImplementedError(f"{type(self).__name__} does not support enter_call.")

    def exit_call(self):
        raise NotImplementedError(f"{type(self).__name__} does not support exit_call.")

    # Private helpers.

    def _read_syscall_request(
        self, syscall_name: str, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> CairoStructProxy:
        """
        Returns the system call request written in the syscall segment, starting at syscall_ptr.
        """
        syscall_info = self.syscall_info[syscall_name]
        return syscall_info.syscall_request_struct.from_ptr(
            memory=segments.memory, addr=syscall_ptr
        )

    @abstractmethod
    def _read_and_validate_syscall_request(
        self, syscall_name: str, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> CairoStructProxy:
        """
        Returns the system call request written in the syscall segment, starting at syscall_ptr.
        Performs validations on the request.
        """

    def _write_syscall_response(
        self,
        syscall_name: str,
        response: CairoStructProxy,
        segments: MemorySegmentManager,
        syscall_ptr: RelocatableValue,
    ):
        assert (
            camel_to_snake_case(syscall_name) in self.syscall_info
        ), f"Illegal system call {syscall_name}."

        syscall_struct: CairoStructProxy = getattr(self.structs, syscall_name)
        response_offset = syscall_struct.struct_definition_.members["response"].offset
        segments.write_arg(ptr=syscall_ptr + response_offset, arg=response)

    @abstractmethod
    def _call_contract(
        self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue, syscall_name: str
    ) -> List[int]:
        """
        Returns the call retdata.

        syscall_name can be "call_contract", "delegate_call" or "delegate_l1_handler".
        """

    def _call_contract_and_write_response(
        self,
        syscall_name: str,
        segments: MemorySegmentManager,
        syscall_ptr: RelocatableValue,
    ):
        """
        Executes the contract call and fills the CallContractResponse struct.
        """
        retdata = self._call_contract(
            segments=segments, syscall_ptr=syscall_ptr, syscall_name=syscall_name
        )
        response = self.structs.CallContractResponse(
            retdata_size=len(retdata),
            retdata=self._allocate_segment(segments=segments, data=retdata),
        )
        self._write_syscall_response(
            syscall_name="CallContract",
            response=response,
            segments=segments,
            syscall_ptr=syscall_ptr,
        )

    @abstractmethod
    def _get_block_number(self) -> int:
        """
        Specific implementation of the get_block_number system call.
        """

    @abstractmethod
    def _get_block_timestamp(self) -> int:
        """
        Specific implementation of the get_block_timestamp system call.
        """

    @abstractmethod
    def _get_caller_address(
        self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> int:
        """
        Specific implementation of the get_caller_address system call.
        """

    @abstractmethod
    def _get_contract_address(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Specific implementation of the get_contract_address system call.
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
    def _allocate_segment(
        self, segments: MemorySegmentManager, data: Iterable[MaybeRelocatable]
    ) -> RelocatableValue:
        """
        Allocates and returns a new (read-only) segment with the given data.
        Note that unlike MemorySegmentManager.write_arg, this function doesn't work well with
        recursive input - call _allocate_segment for the inner items if needed.
        """


def get_runtime_type(cairo_type: CairoType) -> Union[Type[int], Type[RelocatableValue]]:
    """
    Given a CairoType returns the expected runtime type.
    """

    if isinstance(cairo_type, TypeFelt):
        return int
    if isinstance(cairo_type, TypePointer) and isinstance(cairo_type.pointee, TypeFelt):
        return RelocatableValue

    raise NotImplementedError(f"Unexpected type: {cairo_type.format()}.")


class BusinessLogicSysCallHandler(SysCallHandlerBase):
    """
    The SysCallHandler implementation that is used by the batcher.
    """

    def __init__(
        self,
        execute_entry_point_cls: Type[ExecuteEntryPointBase],
        tx_execution_context: TransactionExecutionContext,
        state: CarriedState,
        caller_address: int,
        contract_address: int,
        starknet_storage: BusinessLogicStarknetStorage,
        general_config: StarknetGeneralConfig,
        initial_syscall_ptr: RelocatableValue,
    ):
        super().__init__(general_config=general_config)

        self.execute_entry_point_cls = execute_entry_point_cls
        self.tx_execution_context = tx_execution_context
        self.state = state
        self.caller_address = caller_address
        self.contract_address = contract_address
        self.starknet_storage = starknet_storage
        self.loop = starknet_storage.loop

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

    def _allocate_segment(
        self, segments: MemorySegmentManager, data: Iterable[MaybeRelocatable]
    ) -> RelocatableValue:
        segment_start = segments.add()
        segment_end = segments.write_arg(ptr=segment_start, arg=data)
        self.read_only_segments.append((segment_start, segment_end - segment_start))
        return segment_start

    def _count_syscall(self, syscall_name: str):
        previous_syscall_count = self.state.syscall_counter.get(syscall_name, 0)
        self.state.syscall_counter[syscall_name] = previous_syscall_count + 1

    def _read_and_validate_syscall_request(
        self, syscall_name: str, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> CairoStructProxy:
        """
        Returns the system call request written in the syscall segment, starting at syscall_ptr.
        Performs validations on the request.
        """
        # Update syscall count.
        self._count_syscall(syscall_name=syscall_name)

        request = self._read_syscall_request(
            syscall_name=syscall_name, segments=segments, syscall_ptr=syscall_ptr
        )

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

        args_struct_def: StructDefinition = syscall_info.syscall_request_struct.struct_definition_
        for arg, (arg_name, arg_def) in safe_zip(request, args_struct_def.members.items()):
            expected_type = get_runtime_type(arg_def.cairo_type)
            assert isinstance(arg, expected_type), (
                f"Argument {arg_name} to syscall {syscall_name} is of unexpected type. "
                f"Expected: value of type {expected_type}; got: {arg}."
            )

        return request

    def _call_contract(
        self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue, syscall_name: str
    ) -> List[int]:
        # Parse request and prepare the call.
        request = self._read_and_validate_syscall_request(
            syscall_name=syscall_name, segments=segments, syscall_ptr=syscall_ptr
        )
        calldata = segments.memory.get_range_as_ints(
            addr=request.calldata, size=request.calldata_size
        )

        code_address = cast(int, request.contract_address)
        if syscall_name == "call_contract":
            contract_address = code_address
            caller_address = self.contract_address
            entry_point_type = EntryPointType.EXTERNAL
        elif syscall_name == "delegate_call":
            contract_address = self.contract_address
            caller_address = self.caller_address
            entry_point_type = EntryPointType.EXTERNAL
        elif syscall_name == "delegate_l1_handler":
            contract_address = self.contract_address
            caller_address = self.caller_address
            entry_point_type = EntryPointType.L1_HANDLER
        else:
            raise NotImplementedError(f"Unsupported call type {syscall_name}.")

        call = self.execute_entry_point_cls(
            contract_address=contract_address,
            code_address=code_address,
            entry_point_selector=cast(int, request.function_selector),
            entry_point_type=entry_point_type,
            calldata=calldata,
            caller_address=caller_address,
        )

        with self.contract_call_execution_context(
            call=call, called_contract_address=contract_address
        ):
            # Execute contract call.
            call_info = call.sync_execute(
                state=self.state,
                general_config=self.general_config,
                loop=self.loop,
                tx_execution_context=self.tx_execution_context,
            )

        # Update execution info.
        self.internal_calls.append(call_info)

        return call_info.retdata

    @contextlib.contextmanager
    def contract_call_execution_context(
        self, call: ExecuteEntryPointBase, called_contract_address: int
    ):
        # Pre-execution preperation and validations.
        self._enrich_state(call=call)

        try:
            yield
        except StarkException as exception:
            raise HandlerException(
                called_contract_address=called_contract_address, stark_exception=exception
            )
        except Exception as exception:
            # Exceptions caught here that are not StarkException, are necessarily caused due to
            # security issues, since every exception raised from a Cairo run (in _run) is already
            # wrapped with StarkException.
            stark_exception = StarkException(
                code=StarknetErrorCode.SECURITY_ERROR, message=str(exception)
            )
            raise HandlerException(
                called_contract_address=called_contract_address, stark_exception=stark_exception
            )

        # Post-execution updates.
        self._update_starknet_storage()

    def _enrich_state(self, call: ExecuteEntryPointBase):
        """
        Prepares the state for the execution of the given call.
        """
        # Apply current modifications to the origin contract storage, in case there will be
        # future nested calls to this contract.
        self.state.update_contract_storage(
            contract_address=self.contract_address,
            modifications=self.starknet_storage.get_modifications(),
        )

        # Fetch required information for the call (that is not already cached in the state).
        state_selector = call.get_call_state_selector()
        state_selector -= self.state.state_selector
        future_extra_state = asyncio.run_coroutine_threadsafe(
            coro=self.state.shared_state.get_filled_carried_state(
                ffc=self.state.ffc, state_selector=state_selector
            ),
            loop=self.loop,
        )
        self.state.fill_missing(other=future_extra_state.result())

    def _update_starknet_storage(self):
        """
        Updates the StarkNet storage of the current run after a contract call.
        """
        contract_storage_updates = self.state.contract_states[self.contract_address].storage_updates
        self.starknet_storage.reset_state(storage_updates=contract_storage_updates)

    def emit_event(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the emit_event system call.
        """
        request = self._read_and_validate_syscall_request(
            syscall_name="emit_event", segments=segments, syscall_ptr=syscall_ptr
        )

        self.events.append(
            OrderedEvent(
                order=self.tx_execution_context.n_emitted_events,
                keys=segments.memory.get_range_as_ints(
                    addr=cast(RelocatableValue, request.keys), size=cast(int, request.keys_len)
                ),
                data=segments.memory.get_range_as_ints(
                    addr=cast(RelocatableValue, request.data), size=cast(int, request.data_len)
                ),
            )
        )

        # Update events count.
        self.tx_execution_context.n_emitted_events += 1

    def _get_tx_info_ptr(self, segments: MemorySegmentManager) -> RelocatableValue:
        if self.tx_info_ptr is None:
            tx_info = self.structs.TxInfo(
                version=self.tx_execution_context.version,
                account_contract_address=self.tx_execution_context.account_contract_address,
                max_fee=self.tx_execution_context.max_fee,
                transaction_hash=self.tx_execution_context.transaction_hash,
                signature_len=len(self.tx_execution_context.signature),
                signature=self._allocate_segment(
                    segments=segments, data=self.tx_execution_context.signature
                ),
                chain_id=self.general_config.chain_id.value,
            )
            self.tx_info_ptr = self._allocate_segment(segments=segments, data=tx_info)

        return self.tx_info_ptr

    def send_message_to_l1(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        request = self._read_and_validate_syscall_request(
            syscall_name="send_message_to_l1", segments=segments, syscall_ptr=syscall_ptr
        )
        payload = segments.memory.get_range_as_ints(
            addr=cast(RelocatableValue, request.payload_ptr), size=cast(int, request.payload_size)
        )

        self.l2_to_l1_messages.append(
            # Note that the constructor of OrderedL2ToL1Message might fail as it is
            # more restrictive than the Cairo code.
            OrderedL2ToL1Message(
                order=self.tx_execution_context.n_sent_messages,
                to_address=cast(int, request.to_address),
                payload=payload,
            )
        )

        # Update messages count.
        self.tx_execution_context.n_sent_messages += 1

    def _get_block_number(self) -> int:
        return self.state.block_info.block_number

    def _get_block_timestamp(self) -> int:
        return self.state.block_info.block_timestamp

    def _get_caller_address(
        self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> int:
        self._read_and_validate_syscall_request(
            syscall_name="get_caller_address", segments=segments, syscall_ptr=syscall_ptr
        )

        return self.caller_address

    def _get_contract_address(
        self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> int:
        self._read_and_validate_syscall_request(
            syscall_name="get_contract_address", segments=segments, syscall_ptr=syscall_ptr
        )

        return self.contract_address

    def _storage_read(self, address: int) -> int:
        return self.starknet_storage.read(address=address)

    def _storage_write(self, address: int, value: int):
        # Read the value before the write operation in order to log it in the read_values list.
        # This value is needed to create the DictAccess while executing the corresponding
        # storage_write system call.
        self.starknet_storage.read(address=address)
        self.starknet_storage.write(address=address, value=value)

        # Update modified contracts (for the bouncer).
        # Note that this is a simplified update - we are considering every write
        # as a new change in storage (w.r.t. the state of the previous batch), but it could be that
        # a write actually cancles a change; e.g., 0 -> 5, 5 -> 0.
        self.state.modified_contracts[self.contract_address] = None

    def get_sequencer_address(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        return super().get_sequencer_address(segments=segments, syscall_ptr=syscall_ptr)

    def validate_read_only_segments(self, runner: CairoFunctionRunner):
        """
        Validates that there were no out of bounds writes to read-only segments and marks
        them as accessed.
        """
        segments = runner.segments

        for segment_ptr, segment_size in self.read_only_segments:
            used_size = segments.get_segment_used_size(segment_index=segment_ptr.segment_index)
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


class OsSysCallHandler(SysCallHandlerBase):
    """
    The SysCallHandler implementation that is used by the gps ambassador.
    """

    def __init__(
        self,
        tx_execution_infos: List[TransactionExecutionInfo],
        general_config: StarknetGeneralConfig,
        starknet_storage_by_address: Mapping[int, StarknetStorageInterface],
        block_info: BlockInfo,
    ):
        super().__init__(general_config=general_config)

        self.tx_execution_info_iterator: Iterator[TransactionExecutionInfo] = iter(
            tx_execution_infos
        )
        self.call_iterator: Iterator[CallInfo] = iter([])

        # The following members are stacks that represent the calls being executed now (the last
        # item is the current execution; the one before it, is the caller function; and so on).
        self.call_stack: List[CallInfo] = []
        # For each call an iterator to the retdata of its internal calls.
        self.retdata_iterators: List[Iterator[List[int]]] = []
        # For each call an iterator to the read_values array which is consumed when the transaction
        # code is executed.
        self.execute_code_read_iterators: List[Iterator[int]] = []
        # Same as execute_code_read_iterators except that the iterator is consumed when the
        # system calls are executed by the OS.
        # Namely, the former is used the guess the values during the contract execution
        # and the latter to fill the DictAccess array during the system call execution.
        self.execute_syscall_read_iterators: List[Iterator[int]] = []

        # StarkNet storage members.
        self.starknet_storage_by_address = starknet_storage_by_address

        self.block_info = block_info

        # A pointer to the Cairo TxInfo struct.
        # This pointer needs to match the TxInfo pointer that is going to be used during the system
        # call validation by the StarkNet OS.
        # Set during enter_tx.
        self.tx_info_ptr: Optional[RelocatableValue] = None

        # The TransactionExecutionInfo for the transaction currently being executed.
        self.tx_execution_info: Optional[TransactionExecutionInfo] = None

    def _read_and_validate_syscall_request(
        self, syscall_name: str, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> CairoStructProxy:
        """
        Returns the system call request written in the syscall segment, starting at syscall_ptr.
        Does not perform validations on the request, since it was validated in the BL.
        """
        return self._read_syscall_request(
            syscall_name=syscall_name, segments=segments, syscall_ptr=syscall_ptr
        )

    def _allocate_segment(
        self, segments: MemorySegmentManager, data: Iterable[MaybeRelocatable]
    ) -> RelocatableValue:
        """
        Allocates and returns a new temporary segment.
        """
        segment_start = segments.add_temp_segment()
        segments.write_arg(ptr=segment_start, arg=data)
        return segment_start

    def _call_contract(
        self,
        segments: MemorySegmentManager,
        syscall_ptr: RelocatableValue,
        syscall_name: str,
    ) -> List[int]:
        return next(self.retdata_iterators[-1])

    def _get_block_number(self) -> int:
        return self.block_info.block_number

    def _get_block_timestamp(self) -> int:
        return self.block_info.block_timestamp

    def _get_caller_address(
        self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> int:
        return self.call_stack[-1].caller_address

    def _get_contract_address(
        self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> int:
        return self.call_stack[-1].contract_address

    def _get_tx_info_ptr(self, segments: MemorySegmentManager) -> RelocatableValue:
        assert self.tx_info_ptr is not None
        return self.tx_info_ptr

    def _storage_read(self, address: int) -> int:
        return next(self.execute_code_read_iterators[-1])

    def _storage_write(self, address: int, value: int):
        # Advance execute_code_read_iterators since the previous storage value is written
        # in each write operation. See BusinessLogicSysCallHandler._storage_write().
        next(self.execute_code_read_iterators[-1])

    def execute_syscall_storage_read(self):
        """
        Advances execute_syscall_read_iterators.
        """
        next(self.execute_syscall_read_iterators[-1])

    def execute_syscall_storage_write(self) -> int:
        """
        Returns the storage value before the write operation.
        """
        return next(self.execute_syscall_read_iterators[-1])

    def start_tx(self, tx_info_ptr: RelocatableValue):
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
        assert self.tx_info_ptr is not None
        self.tx_info_ptr = None
        assert self.tx_execution_info is not None
        self.tx_execution_info = None

    def enter_call(self):
        call_info = next(self.call_iterator)
        self.call_stack.append(call_info)
        self.retdata_iterators.append(call.retdata for call in call_info.internal_calls)
        # Create two iterators for call_info.storage_read_values.
        self.execute_code_read_iterators.append(iter(call_info.storage_read_values))
        self.execute_syscall_read_iterators.append(iter(call_info.storage_read_values))

    def exit_call(self):
        self.call_stack.pop()
        # Remove the top iterators and make sure they are empty.
        assert_exhausted(iterator=self.retdata_iterators.pop())
        assert_exhausted(iterator=self.execute_code_read_iterators.pop())
        assert_exhausted(iterator=self.execute_syscall_read_iterators.pop())
