import asyncio
import contextlib
import dataclasses
from abc import ABC, abstractmethod
from typing import Iterator, List, Mapping, Type, Union, cast

from starkware.cairo.common.structs import CairoStructFactory, CairoStructProxy
from starkware.cairo.lang.compiler.ast.cairo_types import CairoType, TypeFelt, TypePointer
from starkware.cairo.lang.compiler.identifier_definition import StructDefinition
from starkware.cairo.lang.vm.memory_segments import MemorySegmentManager
from starkware.cairo.lang.vm.relocatable import RelocatableValue
from starkware.cairo.lang.vm.utils import RunResources
from starkware.python.utils import camel_to_snake_case, safe_zip
from starkware.starknet.business_logic.internal_transaction_interface import (
    ContractCall,
    ContractCallResponse,
    InternalTransactionInterface,
    L2ToL1MessageInfo,
)
from starkware.starknet.business_logic.state import CarriedState
from starkware.starknet.core.os.os_program import get_os_program
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.services.api.gateway.transaction import InvokeFunction
from starkware.starknet.storage.starknet_storage import (
    BusinessLogicStarknetStorage,
    StarknetStorageInterface,
)
from starkware.starkware_utils.error_handling import StarkException


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

    def __init__(self):
        os_program = get_os_program()
        self.structs = CairoStructFactory.from_program(
            program=os_program,
            additional_imports=[
                "starkware.starknet.common.syscalls.CallContract",
                "starkware.starknet.common.syscalls.CallContractRequest",
                "starkware.starknet.common.syscalls.CallContractResponse",
                "starkware.starknet.common.syscalls.GetCallerAddress",
                "starkware.starknet.common.syscalls.GetCallerAddressRequest",
                "starkware.starknet.common.syscalls.GetCallerAddressResponse",
                "starkware.starknet.common.syscalls.GetTxSignature",
                "starkware.starknet.common.syscalls.GetTxSignatureRequest",
                "starkware.starknet.common.syscalls.GetTxSignatureResponse",
                "starkware.starknet.common.syscalls.SendMessageToL1SysCall",
                "starkware.starknet.common.syscalls.StorageRead",
                "starkware.starknet.common.syscalls.StorageReadRequest",
                "starkware.starknet.common.syscalls.StorageReadResponse",
                "starkware.starknet.common.syscalls.StorageWrite",
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
            "get_caller_address": SysCallInfo(
                selector=get_selector("get_caller_address"),
                syscall_request_struct=self.structs.GetCallerAddressRequest,
                syscall_size=self.structs.GetCallerAddress.size,
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
        retdata = self._call_contract(segments=segments, syscall_ptr=syscall_ptr)
        self._write_call_contract_response(
            segments=segments,
            syscall_ptr=syscall_ptr,
            retdata=retdata,
        )

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

    def send_message_to_l1(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        self._send_message_to_l1(segments=segments, syscall_ptr=syscall_ptr)

    def get_tx_signature(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        signature = self._get_tx_signature(segments=segments, syscall_ptr=syscall_ptr)
        response = self.structs.GetTxSignatureResponse(
            signature_len=len(signature), signature=signature
        )

        self._write_syscall_response(
            syscall_name="GetTxSignature",
            response=response,
            segments=segments,
            syscall_ptr=syscall_ptr,
        )

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
        self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> List[int]:
        """
        Returns the call retdata.
        """

    def _write_call_contract_response(
        self,
        segments: MemorySegmentManager,
        syscall_ptr: RelocatableValue,
        retdata: List[int],
    ):
        """
        Fills the CallContractResponse struct.
        """
        response = self.structs.CallContractResponse(
            retdata_size=len(retdata),
            retdata=self._allocate_segment(segments=segments),
        )
        self._write_syscall_response(
            syscall_name="CallContract",
            response=response,
            segments=segments,
            syscall_ptr=syscall_ptr,
        )
        segments.write_arg(ptr=response.retdata, arg=retdata)

    @abstractmethod
    def _get_caller_address(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Specific implementation of the get_caller_address system call.
        """

    def _send_message_to_l1(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Specific implementation of the send_message_to_l1 system call.
        """
        return

    @abstractmethod
    def _get_tx_signature(
        self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> List[int]:
        """
        Returns the signature information for the transaction.
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
    def _allocate_segment(self, segments: MemorySegmentManager) -> RelocatableValue:
        """
        Allocates and returns a new segment.
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
        run_resources: RunResources,
        state: CarriedState,
        caller_address: int,
        contract_address: int,
        signature: List[int],
        starknet_storage: BusinessLogicStarknetStorage,
        general_config: StarknetGeneralConfig,
        internal_transaction_factory: Type[InternalTransactionInterface],
        initial_syscall_ptr: RelocatableValue,
    ):
        super().__init__()

        self.run_resources = run_resources
        self.state = state
        self.caller_address = caller_address
        self.contract_address = contract_address
        self.signature = signature
        self.starknet_storage = starknet_storage
        self.loop = starknet_storage.loop
        self.general_config = general_config
        self.internal_transaction_factory = internal_transaction_factory

        # Accumulated execution info.
        self.internal_call_responses: List[ContractCallResponse] = []
        self.internal_calls: List[ContractCall] = []
        # l2_to_l1_messages including ones sent from internal calls.
        self.l2_to_l1_messages: List[L2ToL1MessageInfo] = []

        # The output length does not include internal transactions.
        self.output_length = 0

        # Kept for validations during the run.
        self.expected_syscall_ptr = initial_syscall_ptr

        # Kept for post-run validations.
        self.storage_stop_pointers: List[RelocatableValue] = []

    def _allocate_segment(self, segments: MemorySegmentManager) -> RelocatableValue:
        return segments.add()

    def _read_and_validate_syscall_request(
        self, syscall_name: str, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> CairoStructProxy:
        """
        Returns the system call request written in the syscall segment, starting at syscall_ptr.
        Performs validations on the request.
        """
        request = self._read_syscall_request(
            syscall_name=syscall_name, segments=segments, syscall_ptr=syscall_ptr
        )

        assert (
            syscall_ptr == self.expected_syscall_ptr
        ), f"Bad syscall_ptr, Expected {self.expected_syscall_ptr}, got {syscall_ptr}."

        syscall_info = self.syscall_info[syscall_name]
        self.expected_syscall_ptr += syscall_info.syscall_size
        selector = request.selector  # type: ignore
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
        self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> List[int]:
        # Parse request and prepare the call.
        request = self._read_and_validate_syscall_request(
            syscall_name="call_contract", segments=segments, syscall_ptr=syscall_ptr
        )
        calldata = segments.memory.get_range_as_ints(
            addr=request.calldata, size=request.calldata_size
        )
        external_tx = InvokeFunction(
            contract_address=cast(int, request.contract_address),
            entry_point_selector=cast(int, request.function_selector),
            calldata=calldata,
            signature=[],
        )
        tx = self.internal_transaction_factory.from_external(
            external_tx=external_tx, general_config=self.general_config
        )

        with self.contract_call_execution_context(
            tx=tx, called_contract_address=external_tx.contract_address, segments=segments
        ):
            # Execute contract call.
            execution_info = tx._synchronous_apply_specific_state_updates(
                state=self.state,
                general_config=self.general_config,
                loop=self.loop,
                caller_address=self.contract_address,
                run_resources=self.run_resources,
            )

        # Update execution info.
        self.l2_to_l1_messages.extend(execution_info.l2_to_l1_messages)
        call_response = ContractCallResponse(
            retdata=execution_info.retdata,
        )
        self.internal_call_responses.append(call_response)
        self.internal_calls.extend(execution_info.contract_calls)

        return call_response.retdata

    @contextlib.contextmanager
    def contract_call_execution_context(
        self,
        tx: InternalTransactionInterface,
        called_contract_address: int,
        segments: MemorySegmentManager,
    ):
        # Pre-execution preperation and validations.
        self._enrich_state(tx=tx)

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

    def _enrich_state(self, tx: InternalTransactionInterface):
        """
        Prepares the state for the execution of the given transaction.
        """
        # Apply current modifications to the origin contract storage, in case there will be
        # future nested call to this contract.
        self.state.update_contract_storage(
            contract_address=self.contract_address,
            modifications=self.starknet_storage.get_modifications(),
        )

        # Fetch required information for the transaction (that is not already cached in the state).
        state_selector = tx.get_state_selector(general_config=self.general_config)
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

    def _send_message_to_l1(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        request = self._read_and_validate_syscall_request(
            syscall_name="send_message_to_l1", segments=segments, syscall_ptr=syscall_ptr
        )

        payload_ptr: RelocatableValue = request.payload_ptr  # type: ignore
        payload_size: int = request.payload_size  # type: ignore
        payload = segments.memory.get_range_as_ints(addr=payload_ptr, size=payload_size)

        # Note that the constructor of L2ToL1MessageInfo might fail as it is
        # more restrictive than the Cairo code.
        l2_to_l1_message_info = L2ToL1MessageInfo(
            from_address=self.contract_address,
            to_address=request.to_address,  # type: ignore
            payload=payload,
        )

        self.l2_to_l1_messages.append(l2_to_l1_message_info)
        self.output_length += 3 + payload_size  # Add 3 for: to, from addresses and payload_size.

    def _get_caller_address(
        self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> int:
        """
        Batcher specific implementation of the get_caller_address.
        """

        self._read_and_validate_syscall_request(
            syscall_name="get_caller_address", segments=segments, syscall_ptr=syscall_ptr
        )

        return self.caller_address

    def _get_tx_signature(
        self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> List[int]:
        self._read_and_validate_syscall_request(
            syscall_name="get_tx_signature", segments=segments, syscall_ptr=syscall_ptr
        )

        return self.signature

    def _storage_read(self, address: int) -> int:
        return self.starknet_storage.read(address=address)

    def _storage_write(self, address: int, value: int):
        # Read the value before the write operation in order to log it in the read_values list.
        # This value is needed to create the DictAccess while executing the corresponding
        # storage_write system call.
        self.starknet_storage.read(address=address)
        self.starknet_storage.write(address=address, value=value)


class OsSysCallHandler(SysCallHandlerBase):
    """
    The SysCallHandler implementation that is used by the gps ambassador.
    """

    def __init__(
        self,
        contract_calls: List[ContractCall],
        starknet_storage_by_address: Mapping[int, StarknetStorageInterface],
    ):
        super().__init__()

        self._call_response_iterator: Iterator[ContractCallResponse] = iter([])
        self._contract_calls_iterator = iter(contract_calls)

        # The following members are stacks that represent the calls being executed now (the last
        # item is the current execution; the one before it, is the caller function; and so on).
        self.call_stack: List[ContractCall] = []
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

    def _allocate_segment(self, segments: MemorySegmentManager) -> RelocatableValue:
        """
        Allocates and returns a new temporary segment.
        """
        return segments.add_temp_segment()

    def _call_contract(
        self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> List[int]:
        request = self.structs.CallContractRequest.from_ptr(
            memory=segments.memory, addr=syscall_ptr
        )
        call_response = next(self._call_response_iterator)
        return call_response.retdata

    def _get_caller_address(
        self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> int:
        """
        OS specific implementation of the get_caller_address.
        """
        return self.call_stack[-1].from_address

    def _get_tx_signature(
        self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> List[int]:
        return self.call_stack[-1].signature

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

    def enter_call(self):
        call_info = next(self._contract_calls_iterator)
        self._call_response_iterator = iter(call_info.internal_call_responses)
        self.call_stack.append(call_info)
        # Create two iterators for call_info.storage_read_values.
        self.execute_code_read_iterators.append(iter(call_info.storage_read_values))
        self.execute_syscall_read_iterators.append(iter(call_info.storage_read_values))

    def exit_call(self):
        assert (
            next(self._call_response_iterator, None) is None
        ), "internal_call_responses should be consumed before calling exit_call."
        self.call_stack.pop()
        # Remove the top iterators in execute_code_read_iterators and execute_syscall_read_iterators
        # and make sure it is empty.
        assert all(False for x in self.execute_code_read_iterators.pop())
        assert all(False for x in self.execute_syscall_read_iterators.pop())
