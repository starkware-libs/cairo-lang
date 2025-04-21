from abc import ABC, abstractmethod
from typing import Iterable

from starkware.cairo.common.structs import CairoStructProxy
from starkware.cairo.lang.vm.memory_segments import MemorySegmentManager
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.python.utils import camel_to_snake_case
from starkware.starknet.business_logic.execution.objects import CallResult
from starkware.starknet.business_logic.state.state_api_objects import BlockInfo
from starkware.starknet.core.os.os_logger import OptionalSegmentManager
from starkware.starknet.core.os.syscall_utils import (
    cast_to_int,
    get_deprecated_syscall_structs_and_info,
)


class DeprecatedSysCallHandlerBase(ABC):
    """
    Base class for execution of system calls in the StarkNet OS.
    """

    def __init__(self, block_info: BlockInfo, segments: OptionalSegmentManager):
        self._segments = segments
        self.block_info = block_info

        self.syscall_structs, self.syscall_info = get_deprecated_syscall_structs_and_info()

    @property
    def segments(self) -> MemorySegmentManager:
        return self._segments.segments

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
        """
        Handles the emit_event system call.
        """

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
        response = self.syscall_structs.GetBlockNumberResponse(
            block_number=self._get_block_number()
        )
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
            sequencer_address=self._get_sequencer_address()
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
        response = self.syscall_structs.GetBlockTimestampResponse(
            block_timestamp=self._get_block_timestamp()
        )
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
    def _get_block_number(self) -> int:
        """
        Returns the block number.
        """

    @abstractmethod
    def _get_block_timestamp(self) -> int:
        """
        Returns the block timestamp.
        """

    @abstractmethod
    def _get_sequencer_address(self) -> int:
        """
        Returns the block sequencer address.
        """

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
