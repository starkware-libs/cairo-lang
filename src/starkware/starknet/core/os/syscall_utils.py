import asyncio
import contextlib
import dataclasses
from abc import ABC, abstractmethod
from typing import Dict, Iterator, List, Optional, Tuple, Type, Union, cast

from starkware.cairo.common.structs import CairoStructFactory, CairoStructProxy
from starkware.cairo.lang.compiler.ast.cairo_types import CairoType, TypeFelt, TypePointer
from starkware.cairo.lang.compiler.identifier_definition import StructDefinition
from starkware.cairo.lang.vm.memory_segments import MemorySegmentManager
from starkware.cairo.lang.vm.relocatable import RelocatableValue
from starkware.cairo.lang.vm.utils import RunResources
from starkware.python.utils import safe_zip
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
from starkware.starknet.storage.starknet_storage import BusinessLogicStarknetStorage
from starkware.starkware_utils.error_handling import StarkException, wrap_with_stark_exception


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
                "starkware.starknet.common.syscalls.SendMessageToL1SysCall",
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
        }

    # Public API.

    def call_contract(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        retdata, updated_storage_ptr = self._call_contract(
            segments=segments, syscall_ptr=syscall_ptr
        )
        self._write_call_contract_response(
            segments=segments,
            syscall_ptr=syscall_ptr,
            retdata=retdata,
            updated_storage_ptr=updated_storage_ptr,
        )

    def get_caller_address(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        """
        Handles the get_caller_address system call.
        """
        caller_address = self._get_caller_address(segments=segments, syscall_ptr=syscall_ptr)

        response = self.structs.GetCallerAddressResponse(caller_address=caller_address)
        response_offset = self.structs.GetCallerAddress.struct_definition_.members[
            "response"
        ].offset
        segments.write_arg(
            ptr=syscall_ptr + response_offset,
            arg=response,
        )

    def send_message_to_l1(self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue):
        self._send_message_to_l1(segments=segments, syscall_ptr=syscall_ptr)

    def enter_call(self):
        raise NotImplementedError(f"{type(self).__name__} does not support enter_call.")

    def exit_call(self):
        raise NotImplementedError(f"{type(self).__name__} does not support exit_call.")

    # Private helpers.

    @abstractmethod
    def _call_contract(
        self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> Tuple[List[int], RelocatableValue]:
        """
        Returns the call retdata and the updated storage ptr.
        """

    def _write_call_contract_response(
        self,
        segments: MemorySegmentManager,
        syscall_ptr: RelocatableValue,
        retdata: List[int],
        updated_storage_ptr: RelocatableValue,
    ):
        """
        Fills the CallContractResponse struct.
        """
        response = self.structs.CallContractResponse(
            retdata_size=len(retdata),
            retdata=self._allocate_segment(segments=segments),
            storage_ptr=updated_storage_ptr,
        )
        response_offset = self.structs.CallContract.struct_definition_.members["response"].offset
        segments.write_arg(
            ptr=syscall_ptr + response_offset,
            arg=response,
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
        caller_address: Optional[int],
        contract_address: int,
        starknet_storage: BusinessLogicStarknetStorage,
        general_config: StarknetGeneralConfig,
        internal_transaction_factory: Type[InternalTransactionInterface],
        initial_syscall_ptr: RelocatableValue,
        initial_storage_ptr: RelocatableValue,
    ):
        super().__init__()

        self.run_resources = run_resources
        self.state = state
        self.caller_address = caller_address
        self.contract_address = contract_address
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

        # A mapping from contract address to its accumulated storage_ptr length; kept for the parent
        # call to know as to where to advance the storage ptr after this call ends.
        self.storage_ptr_diff_by_address: Dict[int, int] = {}

        # Kept for validations during the run.
        self.expected_syscall_ptr = initial_syscall_ptr
        self.current_storage_ptr = initial_storage_ptr

        # Kept for post-run validations.
        self.storage_stop_pointers: List[RelocatableValue] = []

    def _allocate_segment(self, segments: MemorySegmentManager) -> RelocatableValue:
        return segments.add()

    def get_and_validate_syscall_request(
        self, syscall_name: str, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> CairoStructProxy:
        assert (
            syscall_ptr == self.expected_syscall_ptr
        ), f"Bad syscall_ptr, Expected {self.expected_syscall_ptr}, got {syscall_ptr}."

        syscall_info = self.syscall_info[syscall_name]
        request = syscall_info.syscall_request_struct.from_ptr(
            memory=segments.memory, addr=syscall_ptr
        )
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
    ) -> Tuple[List[int], RelocatableValue]:
        # Parse request and prepare the call.
        request = self.get_and_validate_syscall_request(
            syscall_name="call_contract", segments=segments, syscall_ptr=syscall_ptr
        )
        calldata = segments.memory.get_range_as_ints(
            addr=request.calldata, size=request.calldata_size
        )
        external_tx = InvokeFunction(
            contract_address=cast(int, request.contract_address),
            entry_point_selector=cast(int, request.function_selector),
            calldata=calldata,
        )
        tx = self.internal_transaction_factory.from_external(
            external_tx=external_tx, general_config=self.general_config
        )

        # The storage_ptr of the request is the end of the current storage segment;
        # Add it to the list, to be verified at the end.
        self.storage_stop_pointers.append(cast(RelocatableValue, request.storage_ptr))

        with self.contract_call_execution_context(
            tx=tx, called_contract_address=external_tx.contract_address, segments=segments
        ):
            # Execute contract call.
            execution_objects = tx._synchronous_apply_specific_state_updates(
                state=self.state,
                general_config=self.general_config,
                loop=self.loop,
                caller_address=self.contract_address,
                run_resources=self.run_resources,
            )

        execution_info, current_storage_ptr_diff_by_address = execution_objects

        # Update execution info.
        self.l2_to_l1_messages.extend(execution_info.l2_to_l1_messages)
        call_response = ContractCallResponse(
            retdata=execution_info.retdata,
            storage_ptr_diff=current_storage_ptr_diff_by_address.get(self.contract_address, 0),
        )
        self.internal_call_responses.append(call_response)
        self.internal_calls.extend(execution_info.contract_calls)

        # Update storage_ptr_diff_by_address.
        for address, diff in current_storage_ptr_diff_by_address.items():
            prev_diff = self.storage_ptr_diff_by_address.get(address, 0)
            self.storage_ptr_diff_by_address[address] = prev_diff + diff

        # Update current storage_ptr.
        self.current_storage_ptr = segments.add()

        return call_response.retdata, self.current_storage_ptr

    @contextlib.contextmanager
    def contract_call_execution_context(
        self,
        tx: InternalTransactionInterface,
        called_contract_address: int,
        segments: MemorySegmentManager,
    ):
        # Pre-execution preperation and validations.
        self._validate_current_storage_segment(segments=segments)
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

    def _validate_current_storage_segment(self, segments: MemorySegmentManager):
        with wrap_with_stark_exception(
            code=StarknetErrorCode.SECURITY_ERROR, exception_types=[AssertionError, KeyError]
        ):
            size = self.storage_stop_pointers[-1] - self.current_storage_ptr
            assert size >= 0, "The stop_ptr of the storage segment must be ahead of the initial."
            dict_accesses = segments.memory.get_range(addr=self.current_storage_ptr, size=size)
            for value in dict_accesses:
                assert isinstance(
                    value, int
                ), f"The values in a storage dict access must be integers. Found: {value}."

            self.starknet_storage.validate_dict_accesses(
                dict_accesses=cast(List[int], dict_accesses)
            )

    def finalize_storage_validations(
        self, segments: MemorySegmentManager, storage_stop_ptr: RelocatableValue
    ):
        """
        Completes storage validations that can only be done at the very end of the run.
        """
        self.storage_stop_pointers.append(storage_stop_ptr)
        self._validate_current_storage_segment(segments=segments)

        with wrap_with_stark_exception(code=StarknetErrorCode.SECURITY_ERROR):
            for storage_ptr in self.storage_stop_pointers:
                segment_index = storage_ptr.segment_index
                expected_offset = segments.get_segment_used_size(segment_index=segment_index)

                assert storage_ptr.offset == expected_offset, (
                    f"Invalid stop pointer for segment. "
                    f"Expected: {segment_index}:{expected_offset}, found: {storage_ptr}."
                )

        # Update storage_ptr_diff_by_address with this call's storage_ptr length.
        prev_diff = self.storage_ptr_diff_by_address.get(self.contract_address, 0)
        self.storage_ptr_diff_by_address[self.contract_address] = prev_diff + sum(
            storage_ptr.offset for storage_ptr in self.storage_stop_pointers
        )

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
        request = self.get_and_validate_syscall_request(
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

        self.get_and_validate_syscall_request(
            syscall_name="get_caller_address", segments=segments, syscall_ptr=syscall_ptr
        )

        return 0 if self.caller_address is None else self.caller_address


class OsSysCallHandler(SysCallHandlerBase):
    """
    The SysCallHandler implementation that is used by the gps ambassador.
    """

    def __init__(self, contract_calls: List[ContractCall]):
        super().__init__()

        self._call_response_iterator: Iterator[ContractCallResponse] = iter([])
        self._contract_calls_iterator = iter(contract_calls)
        self.call_stack: List[ContractCall] = []

    def _allocate_segment(self, segments: MemorySegmentManager) -> RelocatableValue:
        """
        Allocates and returns a new temporary segment.
        """
        return segments.add_temp_segment()

    def _call_contract(
        self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> Tuple[List[int], RelocatableValue]:
        request = self.structs.CallContractRequest.from_ptr(
            memory=segments.memory, addr=syscall_ptr
        )
        call_response = next(self._call_response_iterator)
        retdata = call_response.retdata
        updated_storage_ptr = request.storage_ptr + call_response.storage_ptr_diff

        return retdata, updated_storage_ptr

    def _get_caller_address(
        self, segments: MemorySegmentManager, syscall_ptr: RelocatableValue
    ) -> int:
        """
        OS specific implementation of the get_caller_address.
        """
        from_address = self.call_stack[-1].from_address
        return 0 if from_address is None else from_address

    def enter_call(self):
        call_info = next(self._contract_calls_iterator)
        self._call_response_iterator = iter(call_info.internal_call_responses)
        self.call_stack.append(call_info)

    def exit_call(self):
        assert (
            next(self._call_response_iterator, None) is None
        ), "internal_call_responses should be consumed before calling exit_call."
        self.call_stack.pop()
