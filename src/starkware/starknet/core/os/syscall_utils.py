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
from starkware.python.utils import assert_exhausted, camel_to_snake_case, safe_zip, to_bytes
from starkware.starknet.business_logic.execution.execute_entry_point_base import (
    ExecuteEntryPointBase,
)
from starkware.starknet.business_logic.execution.objects import (
    CallInfo,
    CallType,
    OrderedEvent,
    OrderedL2ToL1Message,
    TransactionExecutionContext,
    TransactionExecutionInfo,
)
from starkware.starknet.business_logic.fact_state.state import ExecutionResourcesManager
from starkware.starknet.business_logic.state.state import ContractStorageState
from starkware.starknet.business_logic.state.state_api import SyncState
from starkware.starknet.business_logic.state.state_api_objects import BlockInfo
from starkware.starknet.core.os.contract_address.contract_address import (
    calculate_contract_address_from_hash,
)
from starkware.starknet.core.os.os_program import get_os_program
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.public.abi import CONSTRUCTOR_ENTRY_POINT_SELECTOR
from starkware.starknet.services.api.contract_class import EntryPointType
from starkware.starknet.storage.starknet_storage import OsSingleStarknetStorage
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

    def __init__(self, block_info: BlockInfo):
        os_program = get_os_program()

        self.block_info = block_info

        self.structs = CairoStructFactory.from_program(
            program=os_program,
            additional_imports=[
                "starkware.starknet.common.syscalls.CallContract",
                "starkware.starknet.common.syscalls.CallContractRequest",
                "starkware.starknet.common.syscalls.CallContractResponse",
                "starkware.starknet.common.syscalls.Deploy",
                "starkware.starknet.common.syscalls.DeployRequest",
                "starkware.starknet.common.syscalls.DeployResponse",
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
                "starkware.starknet.common.syscalls.LibraryCall",
                "starkware.starknet.common.syscalls.LibraryCallRequest",
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
            "deploy": SysCallInfo(
                selector=get_selector("deploy"),
                syscall_request_struct=self.structs.DeployRequest,
                syscall_size=self.structs.Deploy.size,
            ),
            "emit_event": SysCallInfo(
                selector=get_selector("emit_event"),
                syscall_request_struct=self.structs.EmitEvent,
                syscall_size=self.structs.EmitEvent.size,
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
            "get_tx_signature": SysCallInfo(
                selector=get_selector("get_tx_signature"),
                syscall_request_struct=self.structs.GetTxSignatureRequest,
                syscall_size=self.structs.GetTxSignature.size,
            ),
            "library_call": SysCallInfo(
                selector=get_selector("library_call"),
                syscall_request_struct=self.structs.LibraryCallRequest,
                syscall_size=self.structs.LibraryCall.size,
            ),
            "library_call_l1_handler": SysCallInfo(
                selector=get_selector("library_call_l1_handler"),
                syscall_request_struct=self.structs.LibraryCallRequest,
                syscall_size=self.structs.LibraryCall.size,
            ),
            "send_message_to_l1": SysCallInfo(
                selector=get_selector("send_message_to_l1"),
                syscall_request_struct=self.structs.SendMessageToL1SysCall,
                syscall_size=self.structs.SendMessageToL1SysCall.size,
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

    def deploy(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the deploy system call.
        """
        contract_address = self._deploy(segments=segments, syscall_ptr=syscall_ptr)
        response = self.structs.DeployResponse(
            contract_address=contract_address,
            constructor_retdata_size=0,
            constructor_retdata=0,
        )
        self._write_syscall_response(
            syscall_name="Deploy",
            response=response,
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

        block_number = self.block_info.block_number

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
            sequencer_address=0
            if self.block_info.sequencer_address is None
            else self.block_info.sequencer_address
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

        block_timestamp = self.block_info.block_timestamp

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

    def library_call(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        self._call_contract_and_write_response(
            syscall_name="library_call",
            segments=segments,
            syscall_ptr=syscall_ptr,
        )

    def library_call_l1_handler(
        self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ):
        self._call_contract_and_write_response(
            syscall_name="library_call_l1_handler",
            segments=segments,
            syscall_ptr=syscall_ptr,
        )

    @abstractmethod
    def _get_tx_info_ptr(self, segments: MemorySegmentManager):
        """
        Returns a pointer to the TxInfo struct.
        """

    @abstractmethod
    def _deploy(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue) -> int:
        """
        Returns the address of the newly deployed contract.
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

        syscall_name can be "call_contract", "delegate_call", "delegate_l1_handler", "library_call"
        or "library_call_l1_handler".
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
        state: SyncState,
        resources_manager: ExecutionResourcesManager,
        caller_address: int,
        contract_address: int,
        general_config: StarknetGeneralConfig,
        initial_syscall_ptr: RelocatableValue,
    ):
        super().__init__(block_info=state.block_info)

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

    def _allocate_segment(
        self, segments: MemorySegmentManager, data: Iterable[MaybeRelocatable]
    ) -> RelocatableValue:
        segment_start = segments.add()
        segment_end = segments.write_arg(ptr=segment_start, arg=data)
        self.read_only_segments.append((segment_start, segment_end - segment_start))
        return segment_start

    def _count_syscall(self, syscall_name: str):
        previous_syscall_count = self.resources_manager.syscall_counter.get(syscall_name, 0)
        self.resources_manager.syscall_counter[syscall_name] = previous_syscall_count + 1

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

        code_address: Optional[int] = None
        class_hash: Optional[bytes] = None
        if syscall_name == "call_contract":
            code_address = cast(int, request.contract_address)
            contract_address = code_address
            caller_address = self.contract_address
            entry_point_type = EntryPointType.EXTERNAL
            call_type = CallType.CALL
        elif syscall_name == "delegate_call":
            code_address = cast(int, request.contract_address)
            contract_address = self.contract_address
            caller_address = self.caller_address
            entry_point_type = EntryPointType.EXTERNAL
            call_type = CallType.DELEGATE
        elif syscall_name == "delegate_l1_handler":
            code_address = cast(int, request.contract_address)
            contract_address = self.contract_address
            caller_address = self.caller_address
            entry_point_type = EntryPointType.L1_HANDLER
            call_type = CallType.DELEGATE
        elif syscall_name == "library_call":
            class_hash = to_bytes(cast(int, request.class_hash))
            contract_address = self.contract_address
            caller_address = self.caller_address
            entry_point_type = EntryPointType.EXTERNAL
            call_type = CallType.DELEGATE
        elif syscall_name == "library_call_l1_handler":
            class_hash = to_bytes(cast(int, request.class_hash))
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
            entry_point_selector=cast(int, request.function_selector),
            entry_point_type=entry_point_type,
            calldata=calldata,
            caller_address=caller_address,
        )

        return self.execute_entry_point(call=call)

    def _deploy(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue) -> int:
        """
        Initializes and runs the constructor of the new contract.
        Returns the address of the newly deployed contract.
        """
        request = self._read_and_validate_syscall_request(
            syscall_name="deploy", segments=segments, syscall_ptr=syscall_ptr
        )
        assert request.deploy_from_zero in [
            0,
            1,
        ], "The deploy_from_zero field in the deploy system call must be 0 or 1."
        constructor_calldata = segments.memory.get_range_as_ints(
            addr=cast(RelocatableValue, request.constructor_calldata),
            size=cast(int, request.constructor_calldata_size),
        )
        class_hash = cast(int, request.class_hash)

        deployer_address = self.contract_address if request.deploy_from_zero == 0 else 0
        contract_address = calculate_contract_address_from_hash(
            salt=cast(int, request.contract_address_salt),
            class_hash=class_hash,
            constructor_calldata=constructor_calldata,
            deployer_address=deployer_address,
        )

        # Initialize the contract.
        class_hash_bytes = to_bytes(class_hash)
        self.sync_state.deploy_contract(
            contract_address=contract_address, class_hash=class_hash_bytes
        )

        self.execute_constructor_entry_point(
            contract_address=contract_address,
            class_hash_bytes=class_hash_bytes,
            constructor_calldata=constructor_calldata,
        )

        return contract_address

    def execute_constructor_entry_point(
        self, contract_address: int, class_hash_bytes: bytes, constructor_calldata: List[int]
    ):
        contract_class = self.sync_state.get_contract_class(class_hash=class_hash_bytes)
        constructor_entry_points = contract_class.entry_points_by_type[EntryPointType.CONSTRUCTOR]
        if len(constructor_entry_points) == 0:
            # Contract has no constructor.
            assert (
                len(constructor_calldata) == 0
            ), "Cannot pass calldata to a contract with no constructor."

            call_info = CallInfo.empty_constructor_call(
                contract_address=contract_address,
                caller_address=self.contract_address,
                class_hash=class_hash_bytes,
            )
            self.internal_calls.append(call_info)

            return

        call = self.execute_entry_point_cls(
            call_type=CallType.CALL,
            class_hash=None,
            contract_address=contract_address,
            code_address=contract_address,
            entry_point_selector=CONSTRUCTOR_ENTRY_POINT_SELECTOR,
            entry_point_type=EntryPointType.CONSTRUCTOR,
            calldata=constructor_calldata,
            caller_address=self.contract_address,
        )
        self.execute_entry_point(call=call)

    def execute_entry_point(self, call: ExecuteEntryPointBase) -> List[int]:
        with self.entry_point_execution_context(call=call):
            # Execute contract call.
            call_info = call.execute(
                state=self.sync_state,
                resources_manager=self.resources_manager,
                general_config=self.general_config,
                tx_execution_context=self.tx_execution_context,
            )

        # Update execution info.
        self.internal_calls.append(call_info)

        return call_info.retdata

    @contextlib.contextmanager
    def entry_point_execution_context(self, call: ExecuteEntryPointBase):
        try:
            yield
        except StarkException as exception:
            raise HandlerException(
                called_contract_address=call.contract_address, stark_exception=exception
            ) from exception
        except Exception as exception:
            # Exceptions caught here that are not StarkException, are necessarily caused due to
            # security issues, since every exception raised from a Cairo run (in _run) is already
            # wrapped with StarkException.
            stark_exception = StarkException(
                code=StarknetErrorCode.SECURITY_ERROR, message=str(exception)
            )
            raise HandlerException(
                called_contract_address=call.contract_address, stark_exception=stark_exception
            ) from exception

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
                nonce=self.tx_execution_context.nonce,
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
        starknet_storage_by_address: Mapping[int, OsSingleStarknetStorage],
        block_info: BlockInfo,
    ):
        super().__init__(block_info=block_info)

        self.tx_execution_info_iterator: Iterator[TransactionExecutionInfo] = iter(
            tx_execution_infos
        )
        self.call_iterator: Iterator[CallInfo] = iter([])

        # A stack that keeps track of the state of the calls being executed now.
        # The last item is the state of the current call; the one before it, is the
        # state of the caller (the call the called the current call); and so on.
        self.call_stack: List[CallInfo] = []

        # An iterator over contract addresses that were deployed during that call.
        self.deployed_contracts_iterator: Iterator[int] = iter([])

        # An iterator to the retdata of its internal calls.
        self.retdata_iterator: Iterator[List[int]] = iter([])

        # An iterator to the read_values array which is consumed when the transaction
        # code is executed.
        self.execute_code_read_iterator: Iterator[int] = iter([])
        # StarkNet storage members.
        self.starknet_storage_by_address = starknet_storage_by_address

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
        return next(self.retdata_iterator)

    def _deploy(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue) -> int:
        constructor_retdata = next(self.retdata_iterator)
        assert len(constructor_retdata) == 0, "Unexpected constructor_retdata."
        return next(self.deployed_contracts_iterator)

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
        return next(self.execute_code_read_iterator)

    def _storage_write(self, address: int, value: int):
        # Advance execute_code_read_iterators since the previous storage value is written
        # in each write operation. See BusinessLogicSysCallHandler._storage_write().
        next(self.execute_code_read_iterator)

    def execute_syscall_storage_write(self, contract_address: int, key: int, value: int) -> int:
        """
        Updates the cached storage and returns the storage value before
        the write operation.
        """
        previous_value = self.starknet_storage_by_address[contract_address].write(
            key=key, value=value
        )
        return previous_value

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

    def assert_interators_exhausted(self):
        assert_exhausted(iterator=self.deployed_contracts_iterator)
        assert_exhausted(iterator=self.retdata_iterator)
        assert_exhausted(iterator=self.execute_code_read_iterator)

    def enter_call(self):
        self.assert_interators_exhausted()

        call_info = next(self.call_iterator)
        self.call_stack.append(call_info)

        self.deployed_contracts_iterator = (
            call.contract_address
            for call in call_info.internal_calls
            if call.entry_point_type is EntryPointType.CONSTRUCTOR
        )
        self.retdata_iterator = (call.retdata for call in call_info.internal_calls)
        self.execute_code_read_iterator = iter(call_info.storage_read_values)

    def exit_call(self):
        self.assert_interators_exhausted()
        self.call_stack.pop()

    def skip_tx(self):
        """
        Called when skipping the execution of a transaction.
        It replaces a call to start_tx and end_tx.
        """
        next(self.tx_execution_info_iterator)
