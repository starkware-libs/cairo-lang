from typing import Any, Dict, Optional, Tuple, Union

from starkware.cairo.lang.builtins.ec.instance_def import (
    CELLS_PER_EC_OP,
    INPUT_CELLS_PER_EC_OP,
    EcOpInstanceDef,
)
from starkware.cairo.lang.vm.builtin_runner import SimpleBuiltinRunner
from starkware.cairo.lang.vm.relocatable import RelocatableValue
from starkware.crypto.signature.signature import ALPHA, BETA, FIELD_PRIME
from starkware.python.math_utils import EC_INFINITY, ec_safe_add, ec_safe_mult

# The indices of the inputs that represent EC points.
EC_POINT_INDICES = [(0, 1), (2, 3), (5, 6)]
M_INDEX = 4
OUTPUT_INDICES = EC_POINT_INDICES[2]
INPUT_NAMES = ["p_x", "p_y", "q_x", "q_y", "m"]
assert INPUT_CELLS_PER_EC_OP == len(INPUT_NAMES)
assert INPUT_CELLS_PER_EC_OP + len(OUTPUT_INDICES) == CELLS_PER_EC_OP


def point_on_curve(x: int, y: int, alpha: int, beta: int, p: int) -> bool:
    """
    Returns True if the point (x, y) is on the elliptic curve defined as
    y^2 = x^3 + alpha * x + beta (mod p)
    or False otherwise.
    """
    return pow(y, 2, p) == (pow(x, 3, p) + alpha * x + beta) % p


def ec_op_impl(
    p_x: int, p_y: int, q_x: int, q_y: int, m: int, alpha: int, p: int
) -> Union[Tuple[int, int], str]:
    """
    Returns the result of the EC operation P + m * Q.
    where P = (p_x, p_y), Q = (q_x, q_y) are points on the elliptic curve defined as
    y^2 = x^3 + alpha * x + beta (mod p).
    """
    return ec_safe_add((p_x, p_y), ec_safe_mult(m, (q_x, q_y), alpha, p), alpha, p)


class EcOpBuiltinRunner(SimpleBuiltinRunner):
    def __init__(self, included: bool, ec_op_builtin: EcOpInstanceDef):
        super().__init__(
            name="ec_op",
            included=included,
            ratio=None if ec_op_builtin is None else ec_op_builtin.ratio,
            cells_per_instance=CELLS_PER_EC_OP,
            n_input_cells=INPUT_CELLS_PER_EC_OP,
        )
        self.stop_ptr: Optional[RelocatableValue] = None
        self.ec_op_builtin: EcOpInstanceDef = ec_op_builtin

    def add_auto_deduction_rules(self, runner):
        def rule(vm, addr):
            memory = vm.run_context.memory
            index = addr.offset % CELLS_PER_EC_OP
            instance = addr - index

            # If the index is not an output cell or not all input cells are filled, return None.
            if index not in OUTPUT_INDICES:
                return None
            if not all(instance + i in memory for i in range(INPUT_CELLS_PER_EC_OP)):
                return None

            # Assert that m <= scalar_limit.
            if self.ec_op_builtin.scalar_limit is not None:
                assert (
                    memory[instance + M_INDEX] <= self.ec_op_builtin.scalar_limit
                ), f"{self.name} builtin: m must be at most {self.ec_op_builtin.scalar_limit}."

            for i in range(INPUT_CELLS_PER_EC_OP):
                assert vm.is_integer_value(memory[instance + i]), (
                    f"{self.name} builtin: Expected integer at address {instance + i}."
                    f"Got: {memory[instance + i]}."
                )

            # Assert that if the current address is part of a point which is all set in the
            # memory, the point is on the curve.
            for pair in EC_POINT_INDICES[:2]:
                ec_point_x, ec_point_y = [memory[instance + i] for i in pair]
                assert point_on_curve(
                    ec_point_x, ec_point_y, ALPHA, BETA, FIELD_PRIME
                ), f"{self.name} builtin: point {pair} is not on the curve."

            res = ec_op_impl(  # type: ignore
                *[memory[instance + i] for i in range(INPUT_CELLS_PER_EC_OP)], ALPHA, FIELD_PRIME
            )
            # The result cannot be the point at infinity.
            assert res != EC_INFINITY, "The result cannot be the point at infinity."

            return res[index - INPUT_CELLS_PER_EC_OP]

        runner.vm.add_auto_deduction_rule(self.base.segment_index, rule)

    def air_private_input(self, runner) -> Dict[str, Any]:
        assert self.base is not None, "Uninitialized self.base."
        res: Dict[int, Any] = {}
        for addr, val in runner.vm_memory.items():
            if (
                not isinstance(addr, RelocatableValue)
                or addr.segment_index != self.base.segment_index
            ):
                continue
            idx, typ = divmod(addr.offset, CELLS_PER_EC_OP)
            if typ >= INPUT_CELLS_PER_EC_OP:
                continue

            assert isinstance(val, int)
            res.setdefault(idx, {"index": idx})[INPUT_NAMES[typ]] = hex(val)

        for index, item in res.items():
            for name in INPUT_NAMES:
                assert name in item, f"Missing input '{name}' of {self.name} instance {index}."

        return {self.name: sorted(res.values(), key=lambda item: item["index"])}
