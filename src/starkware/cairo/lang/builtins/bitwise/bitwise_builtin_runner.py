from typing import Any, Dict, Optional

from starkware.cairo.lang.builtins.bitwise.instance_def import (
    CELLS_PER_BITWISE,
    INPUT_CELLS_PER_BITWISE,
    BitwiseInstanceDef,
)
from starkware.cairo.lang.vm.builtin_runner import SimpleBuiltinRunner
from starkware.cairo.lang.vm.relocatable import RelocatableValue


class BitwiseBuiltinRunner(SimpleBuiltinRunner):
    def __init__(self, included: bool, bitwise_builtin: BitwiseInstanceDef):
        super().__init__(
            name="bitwise",
            included=included,
            ratio=None if bitwise_builtin is None else bitwise_builtin.ratio,
            cells_per_instance=CELLS_PER_BITWISE,
            n_input_cells=INPUT_CELLS_PER_BITWISE,
        )
        self.stop_ptr: Optional[RelocatableValue] = None
        self.bitwise_builtin: BitwiseInstanceDef = bitwise_builtin

    def add_auto_deduction_rules(self, runner):
        def rule(vm, addr):
            memory = vm.run_context.memory
            index = addr.offset % CELLS_PER_BITWISE
            if addr.offset % CELLS_PER_BITWISE in [0, 1]:
                return
            x_addr = addr - index
            y_addr = x_addr + 1
            if x_addr not in memory or y_addr not in memory:
                return
            assert vm.is_integer_value(memory[x_addr]), (
                f"{self.name} builtin: Expected integer at address {x_addr}. "
                + f"Got: {memory[x_addr]}."
            )
            assert memory[x_addr] < 2 ** self.bitwise_builtin.total_n_bits, (
                f"{self.name} builtin: Expected integer at address {x_addr} to be smaller than "
                + f"2^{self.bitwise_builtin.total_n_bits}. Got: {memory[x_addr]}."
            )
            assert vm.is_integer_value(memory[y_addr]), (
                f"{self.name} builtin: Expected integer at address {y_addr}. "
                + f"Got: {memory[y_addr]}."
            )
            assert memory[y_addr] < 2 ** self.bitwise_builtin.total_n_bits, (
                f"{self.name} builtin: Expected integer at address {y_addr} to be smaller than "
                + f"2^{self.bitwise_builtin.total_n_bits}. Got: {memory[y_addr]}."
            )
            if index == 2:
                res = memory[x_addr] & memory[y_addr]
            elif index == 3:
                res = memory[x_addr] ^ memory[y_addr]
            elif index == 4:
                res = memory[x_addr] | memory[y_addr]
            return res

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
            idx, typ = divmod(addr.offset, CELLS_PER_BITWISE)
            if typ >= 2:
                continue

            assert isinstance(val, int)
            res.setdefault(idx, {"index": idx})["x" if typ == 0 else "y"] = hex(val)

        for index, item in res.items():
            assert "x" in item, f"Missing first input of bitwise instance {index}."
            assert "y" in item, f"Missing second input of bitwise instance {index}."

        return {"bitwise": sorted(res.values(), key=lambda item: item["index"])}

    def get_used_diluted_check_units(self, diluted_spacing: int, diluted_n_bits: int) -> int:
        total_n_bits = self.bitwise_builtin.total_n_bits

        partition = [
            i + j
            for i in range(0, total_n_bits, diluted_spacing * diluted_n_bits)
            for j in range(diluted_spacing)
            if i + j < total_n_bits
        ]
        num_trimmed = len(
            [
                1
                for shift in partition
                if shift + diluted_spacing * (diluted_n_bits - 1) + 1 > total_n_bits
            ]
        )
        return 4 * len(partition) + num_trimmed
