import dataclasses
import functools
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, cast

import cachetools

from starkware.cairo.common.cairo_secp.secp_utils import SECP256K1, SECP256R1, Curve
from starkware.cairo.common.cairo_sha256.sha256_utils import sha_256_update_state
from starkware.cairo.common.keccak_utils.keccak_utils import keccak_f
from starkware.cairo.common.structs import CairoStructProxy
from starkware.cairo.lang.vm.memory_segments import MemorySegmentManager
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.cairo.lang.vm.vm_consts import VmConstsReference
from starkware.python.math_utils import (
    EC_INFINITY,
    EcInfinity,
    EcPoint,
    ec_safe_add,
    ec_safe_mult,
    safe_div,
    y_squared_from_x,
)
from starkware.python.utils import blockify, from_bytes, safe_zip, to_bytes
from starkware.starknet.business_logic.execution.objects import CallResult
from starkware.starknet.core.os.os_logger import OptionalSegmentManager
from starkware.starknet.core.os.syscall_utils import (
    STARKNET_SYSCALLS_COMPILED_PATH,
    cast_to_int,
    get_selector_from_program,
    get_syscall_structs,
    load_program,
    validate_runtime_request_type,
)
from starkware.starknet.definitions import constants
from starkware.starknet.definitions.constants import GasCost
from starkware.starknet.definitions.error_codes import CairoErrorCode
from starkware.starknet.public.abi import EXECUTE_ENTRY_POINT_SELECTOR

SyscallFullResponse = Tuple[tuple, tuple]  # Response header + specific syscall response.
ExecuteSyscallCallback = Callable[
    ["SyscallHandlerBase", int, CairoStructProxy], SyscallFullResponse
]

KECCAK_FULL_RATE_IN_U64S = 17


def from_uint256(val: CairoStructProxy) -> int:
    return val.high * 2**128 + val.low  # type: ignore


def to_uint256(structs: CairoStructProxy, val: int) -> CairoStructProxy:
    return structs.Uint256(low=val & (2**128 - 1), high=val >> 128)  # type: ignore


@dataclasses.dataclass(frozen=True)
class SyscallInfo:
    name: str
    execute_callback: ExecuteSyscallCallback
    request_struct: CairoStructProxy


class SyscallHandlerBase(ABC):
    def __init__(
        self,
        segments: OptionalSegmentManager,
        initial_syscall_ptr: Optional[RelocatableValue],
    ):
        # Static syscall information.
        self.structs = get_syscall_structs()
        self.selector_to_syscall_info = self.get_selector_to_syscall_info()

        # Memory segments of the running program.
        self._segments = segments
        # Current syscall pointer; updated internally during the call execution.
        self._syscall_ptr = initial_syscall_ptr

        # Mapping from ec_point* to pythonic EcPoint.
        self.ec_points: Dict[RelocatableValue, EcPoint] = {}
        # A segment that holds all the ec points.
        self.ec_points_segment: Optional[RelocatableValue] = None
        self.ec_point_size = cast(int, self.structs.EcPoint.size)

        self.sha256_segment: Optional[VmConstsReference] = None
        self.sha256_block_count = 0

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
            get_selector("secp256k1_new"): SyscallInfo(
                name="secp256k1_new",
                execute_callback=cls.secp256k1_new,
                request_struct=structs.Secp256k1NewRequest,
            ),
            get_selector("secp256k1_add"): SyscallInfo(
                name="secp256k1_add",
                execute_callback=functools.partial(cls.secp_add, curve=SECP256K1),
                request_struct=structs.Secp256k1AddRequest,
            ),
            get_selector("secp256r1_add"): SyscallInfo(
                name="secp256r1_add",
                execute_callback=functools.partial(cls.secp_add, curve=SECP256R1),
                request_struct=structs.Secp256r1AddRequest,
            ),
            get_selector("secp256k1_mul"): SyscallInfo(
                name="secp256k1_mul",
                execute_callback=functools.partial(cls.secp_mul, curve=SECP256K1),
                request_struct=structs.Secp256k1MulRequest,
            ),
            get_selector("secp256r1_mul"): SyscallInfo(
                name="secp256r1_mul",
                execute_callback=functools.partial(cls.secp_mul, curve=SECP256R1),
                request_struct=structs.Secp256r1MulRequest,
            ),
            get_selector("secp256k1_get_point_from_x"): SyscallInfo(
                name="secp256k1_get_point_from_x",
                execute_callback=cls.secp256k1_get_point_from_x,
                request_struct=structs.Secp256k1GetPointFromXRequest,
            ),
            get_selector("secp256r1_get_point_from_x"): SyscallInfo(
                name="secp256r1_get_point_from_x",
                execute_callback=cls.secp256r1_get_point_from_x,
                request_struct=structs.Secp256r1GetPointFromXRequest,
            ),
            get_selector("secp256k1_get_xy"): SyscallInfo(
                name="secp256k1_get_xy",
                execute_callback=cls.secp_get_xy,
                request_struct=structs.Secp256k1GetXyRequest,
            ),
            get_selector("secp256r1_get_xy"): SyscallInfo(
                name="secp256r1_get_xy",
                execute_callback=cls.secp_get_xy,
                request_struct=structs.Secp256r1GetXyRequest,
            ),
            get_selector("secp256r1_new"): SyscallInfo(
                name="secp256r1_new",
                execute_callback=cls.secp256r1_new,
                request_struct=structs.Secp256r1NewRequest,
            ),
            get_selector("keccak"): SyscallInfo(
                name="keccak",
                execute_callback=cls.keccak,
                request_struct=structs.KeccakRequest,
            ),
            get_selector("sha256_process_block"): SyscallInfo(
                name="sha256_process_block",
                execute_callback=cls.sha256_process_block,
                request_struct=structs.Sha256ProcessBlockRequest,
            ),
            get_selector("get_block_hash"): SyscallInfo(
                name="get_block_hash",
                execute_callback=cls.get_block_hash,
                request_struct=structs.GetBlockHashRequest,
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
            get_selector("get_class_hash_at"): SyscallInfo(
                name="get_class_hash_at",
                execute_callback=cls.get_class_hash_at,
                request_struct=structs.GetClassHashAtRequest,
            ),
            get_selector("meta_tx_v0"): SyscallInfo(
                name="meta_tx_v0",
                execute_callback=cls.meta_tx_v0,
                request_struct=structs.MetaTxV0Request,
            ),
        }

    @property
    def segments(self) -> MemorySegmentManager:
        return self._segments.segments

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
        assert (
            syscall_info is not None
        ), f"Unsupported syscall selector {bytes.fromhex(hex(selector)[2:])!r}"
        if syscall_info.name != "keccak":
            self._count_syscall(syscall_name=syscall_info.name)
        request = self._read_and_validate_request(request_struct=syscall_info.request_struct)

        # Check and reduce gas (after validating the syscall selector for consistency with the OS).
        initial_gas = cast_to_int(request_header.gas)
        required_gas = self._get_required_gas(name=syscall_info.name)
        if syscall_info.name == "deploy":
            assert isinstance(request.constructor_calldata_start, RelocatableValue)
            assert isinstance(request.constructor_calldata_end, RelocatableValue)
            calldata_size = request.constructor_calldata_end - request.constructor_calldata_start
            assert isinstance(calldata_size, int)
            linear_cost = calldata_size * GasCost.DEPLOY_CALLDATA_FACTOR.value
            required_gas += linear_cost
        if syscall_info.name == "meta_tx_v0":
            assert isinstance(request.calldata_start, RelocatableValue)
            assert isinstance(request.calldata_end, RelocatableValue)
            calldata_size = request.calldata_end - request.calldata_start
            assert isinstance(calldata_size, int)
            linear_cost = calldata_size * GasCost.META_TX_V0_CALLDATA_FACTOR.value
            required_gas += linear_cost

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
        if request.selector == EXECUTE_ENTRY_POINT_SELECTOR:
            return self._handle_failure(
                final_gas=remaining_gas,
                error_code=CairoErrorCode.INVALID_ARGUMENT,
            )

        return self.call_contract_helper(
            remaining_gas=remaining_gas, request=request, syscall_name="call_contract"
        )

    def library_call(self, remaining_gas: int, request: CairoStructProxy) -> SyscallFullResponse:
        return self.call_contract_helper(
            remaining_gas=remaining_gas, request=request, syscall_name="library_call"
        )

    def meta_tx_v0(self, remaining_gas: int, request: CairoStructProxy) -> SyscallFullResponse:
        if request.selector != EXECUTE_ENTRY_POINT_SELECTOR:
            return self._handle_failure(
                final_gas=remaining_gas,
                error_code=CairoErrorCode.INVALID_ARGUMENT,
            )
        return self.call_contract_helper(
            remaining_gas=remaining_gas, request=request, syscall_name="meta_tx_v0"
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

    def get_block_hash(self, remaining_gas: int, request: CairoStructProxy) -> SyscallFullResponse:
        """
        Executes the get_block_hash system call.

        Returns the block hash of the block at given block_number.
        Returns the expected block hash if the given block was created at least 10 blocks before the
        current block. Otherwise, returns an error.
        """
        block_number = cast_to_int(request.block_number)

        # Handle out of range block number.
        if self.current_block_number - block_number < constants.STORED_BLOCK_HASH_BUFFER:
            return self._handle_failure(
                final_gas=remaining_gas, error_code=CairoErrorCode.BLOCK_NUMBER_OUT_OF_RANGE
            )

        block_hash = self._get_block_hash(block_number=block_number)
        response_header = self.structs.ResponseHeader(gas=remaining_gas, failure_flag=0)
        response = self.structs.GetBlockHashResponse(block_hash=block_hash)

        return response_header, response

    def get_execution_info(
        self, remaining_gas: int, request: CairoStructProxy
    ) -> SyscallFullResponse:
        execution_info_ptr = self._get_execution_info_ptr()

        response_header = self.structs.ResponseHeader(gas=remaining_gas, failure_flag=0)
        response = self.structs.GetExecutionInfoResponse(execution_info=execution_info_ptr)
        return response_header, response

    def _secp_new(
        self,
        remaining_gas: int,
        request: CairoStructProxy,
        curve: Curve,
        response_struct: CairoStructProxy,
    ) -> SyscallFullResponse:
        x = from_uint256(request.x)
        y = from_uint256(request.y)

        if x >= curve.prime or y >= curve.prime:
            return self._handle_failure(
                final_gas=remaining_gas,
                error_code=CairoErrorCode.INVALID_ARGUMENT,
            )

        response_header = self.structs.ResponseHeader(gas=remaining_gas, failure_flag=0)

        ec_point: Optional[RelocatableValue] = None
        if x == 0 and y == 0:
            ec_point = self._new_ec_point(ec_point=EC_INFINITY)
        else:
            y_squared = y_squared_from_x(
                x=x, alpha=curve.alpha, beta=curve.beta, field_prime=curve.prime
            )

            if (y**2 - y_squared) % curve.prime == 0:
                ec_point = self._new_ec_point(ec_point=(x, y))

        if ec_point is None:
            response = response_struct(not_on_curve=1, ec_point=0)
        else:
            response = response_struct(not_on_curve=0, ec_point=ec_point)

        return response_header, response

    def secp256k1_new(self, remaining_gas: int, request: CairoStructProxy) -> SyscallFullResponse:
        return self._secp_new(
            remaining_gas=remaining_gas,
            request=request,
            curve=SECP256K1,
            response_struct=self.structs.Secp256k1NewResponse,
        )

    def secp256r1_new(self, remaining_gas: int, request: CairoStructProxy) -> SyscallFullResponse:
        return self._secp_new(
            remaining_gas=remaining_gas,
            request=request,
            curve=SECP256R1,
            response_struct=self.structs.Secp256r1NewResponse,
        )

    def secp_add(
        self, remaining_gas: int, request: CairoStructProxy, curve: Curve
    ) -> SyscallFullResponse:
        response_header = self.structs.ResponseHeader(gas=remaining_gas, failure_flag=0)
        response = self.structs.SecpOpResponse(
            ec_point=self._new_ec_point(
                ec_point=ec_safe_add(
                    point1=self._get_ec_point(request.p0),
                    point2=self._get_ec_point(request.p1),
                    alpha=curve.alpha,
                    p=curve.prime,
                )
            ),
        )

        return response_header, response

    def secp_mul(
        self, remaining_gas: int, request: CairoStructProxy, curve: Curve
    ) -> SyscallFullResponse:
        response_header = self.structs.ResponseHeader(gas=remaining_gas, failure_flag=0)
        response = self.structs.SecpOpResponse(
            ec_point=self._new_ec_point(
                ec_point=ec_safe_mult(
                    m=from_uint256(request.scalar),
                    point=self.ec_points[cast(RelocatableValue, request.p)],
                    alpha=curve.alpha,
                    p=curve.prime,
                )
            ),
        )
        return response_header, response

    def secp_get_point_from_x(
        self,
        remaining_gas: int,
        request: CairoStructProxy,
        curve: Curve,
    ) -> SyscallFullResponse:
        x = from_uint256(request.x)

        if x >= curve.prime:
            return self._handle_failure(
                final_gas=remaining_gas,
                error_code=CairoErrorCode.INVALID_ARGUMENT,
            )

        prime = curve.prime
        y_squared = y_squared_from_x(
            x=x,
            alpha=curve.alpha,
            beta=curve.beta,
            field_prime=prime,
        )

        y = pow(y_squared, (prime + 1) // 4, prime)
        if (y & 1) != request.y_parity:
            y = (-y) % prime

        response_header = self.structs.ResponseHeader(gas=remaining_gas, failure_flag=0)
        response = (
            self.structs.SecpNewResponse(
                not_on_curve=0,
                ec_point=self._new_ec_point(ec_point=(x, y)),
            )
            if (y * y) % prime == y_squared
            else self.structs.SecpNewResponse(
                not_on_curve=1,
                ec_point=0,
            )
        )

        return response_header, response

    def secp256k1_get_point_from_x(
        self, remaining_gas: int, request: CairoStructProxy
    ) -> SyscallFullResponse:
        return self.secp_get_point_from_x(
            remaining_gas=remaining_gas, request=request, curve=SECP256K1
        )

    def secp256r1_get_point_from_x(
        self, remaining_gas: int, request: CairoStructProxy
    ) -> SyscallFullResponse:
        return self.secp_get_point_from_x(
            remaining_gas=remaining_gas, request=request, curve=SECP256R1
        )

    def secp_get_xy(self, remaining_gas: int, request: CairoStructProxy) -> SyscallFullResponse:
        ec_point = self.ec_points[cast(RelocatableValue, request.ec_point)]
        response_header = self.structs.ResponseHeader(gas=remaining_gas, failure_flag=0)
        if isinstance(ec_point, EcInfinity):
            x, y = 0, 0
        else:
            x, y = ec_point

        # Note that we can't use self.structs.SecpGetXyResponse here as it is not flat.
        response = to_uint256(self.structs, x) + to_uint256(self.structs, y)  # type: ignore

        return response_header, response

    def keccak(self, remaining_gas: int, request: CairoStructProxy) -> SyscallFullResponse:
        assert isinstance(request.input_end, RelocatableValue)
        assert isinstance(request.input_start, RelocatableValue)
        input_len = cast(int, request.input_end - request.input_start)

        if input_len % KECCAK_FULL_RATE_IN_U64S != 0:
            return self._handle_failure(
                final_gas=remaining_gas,
                error_code=CairoErrorCode.INVALID_INPUT_LEN,
            )

        n_rounds = safe_div(input_len, KECCAK_FULL_RATE_IN_U64S)
        gas_cost = n_rounds * GasCost.KECCAK_ROUND_COST.value
        if gas_cost > remaining_gas:
            return self._handle_failure(
                final_gas=remaining_gas,
                error_code=CairoErrorCode.OUT_OF_GAS,
            )
        remaining_gas -= gas_cost

        self._keccak(n_rounds=n_rounds)
        input_array = self._get_felt_range(
            start_addr=request.input_start, end_addr=request.input_end
        )
        state = bytearray(200)
        for chunk in blockify(input_array, chunk_size=KECCAK_FULL_RATE_IN_U64S):
            for i, val in safe_zip(range(0, KECCAK_FULL_RATE_IN_U64S * 8, 8), chunk):
                state[i : i + 8] = to_bytes(
                    value=from_bytes(value=state[i : i + 8], byte_order="little") ^ val,
                    length=8,
                    byte_order="little",
                )
            state = bytearray(keccak_f(state))

        result = [
            from_bytes(state[0:16], byte_order="little"),
            from_bytes(state[16:32], byte_order="little"),
        ]

        response_header = self.structs.ResponseHeader(gas=remaining_gas, failure_flag=0)
        response = self.structs.KeccakResponse(result_low=result[0], result_high=result[1])
        return response_header, response

    def sha256_process_block(
        self, remaining_gas: int, request: CairoStructProxy
    ) -> SyscallFullResponse:
        assert isinstance(request.state_ptr, RelocatableValue)
        assert isinstance(request.input_start, RelocatableValue)

        state_array = self._get_felt_range(
            start_addr=request.state_ptr, end_addr=request.state_ptr + 8
        )

        input_array = self._get_felt_range(
            start_addr=request.input_start, end_addr=request.input_start + 16
        )

        assert type(self.sha256_segment) == VmConstsReference

        state_array = sha_256_update_state(
            state_array,
            input_array,
        )

        self.segments.write_arg(
            ptr=self.sha256_segment[self.sha256_block_count].out_state.address_, arg=state_array
        )

        response_header = self.structs.ResponseHeader(gas=remaining_gas, failure_flag=0)
        response = self.structs.Sha256ProcessBlockResponse(
            state_ptr=self.sha256_segment[self.sha256_block_count].out_state.address_
        )
        self.sha256_block_count += 1

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

    def get_class_hash_at(
        self, remaining_gas: int, request: CairoStructProxy
    ) -> SyscallFullResponse:
        class_hash = self._get_class_hash_at(contract_address=cast_to_int(request.contract_address))

        response_header = self.structs.ResponseHeader(gas=remaining_gas, failure_flag=0)
        response = self.structs.GetClassHashAtResponse(class_hash=class_hash)
        return response_header, response

    # Application-specific syscall implementation.
    @abstractmethod
    def _get_class_hash_at(self, contract_address: int) -> int:
        """
        Returns the class hash of the given contract address.
        If the contract address is not in the contracts tree, returns 0.
        """

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
    def _get_block_hash(self, block_number: int) -> int:
        """
        Returns the block hash of the block at given block number.
        """

    @abstractmethod
    def _get_execution_info_ptr(self) -> RelocatableValue:
        """
        Returns a pointer to the ExecutionInfo struct.
        """

    @abstractmethod
    def _keccak(self, n_rounds: int):
        """
        Post-process for the keccak syscall.
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

    def _handle_failure(self, final_gas: int, error_code: CairoErrorCode) -> SyscallFullResponse:
        response_header = self.structs.ResponseHeader(gas=final_gas, failure_flag=1)
        data = [error_code.to_felt()]
        start = self.allocate_segment(data=data)
        failure_reason = self.structs.FailureReason(start=start, end=start + len(data))

        return response_header, failure_reason

    def _handle_out_of_gas(self, initial_gas: int) -> SyscallFullResponse:
        return self._handle_failure(final_gas=initial_gas, error_code=CairoErrorCode.OUT_OF_GAS)

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

    @abstractmethod
    def _count_syscall(self, syscall_name: str):
        """
        Counts syscalls.
        """

    def _new_ec_point(self, ec_point: EcPoint) -> RelocatableValue:
        """
        Allocates ec_points handle and stores it in the ec_points mapping.
        """

        if self.ec_points_segment is None:
            self.ec_points_segment = self.segments.add()

        handle = self.ec_points_segment + len(self.ec_points) * self.ec_point_size
        self.ec_points[handle] = ec_point
        return handle

    def _get_ec_point(self, handle: CairoStructProxy) -> EcPoint:
        """
        Returns the ec_points corresponding to `handle`.
        """

        assert isinstance(handle, RelocatableValue)
        return self.ec_points[handle]

    @property
    @abstractmethod
    def current_block_number(self) -> int:
        """
        Returns the block number of the current block.
        """
