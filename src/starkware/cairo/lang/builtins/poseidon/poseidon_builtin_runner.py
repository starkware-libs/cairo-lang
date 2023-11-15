from typing import Any, Dict, Set

from starkware.cairo.lang.builtins.poseidon.instance_def import PoseidonInstanceDef
from starkware.cairo.lang.vm.builtin_runner import SimpleBuiltinRunner
from starkware.cairo.lang.vm.crypto import poseidon_perm
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.python.math_utils import safe_div


class PoseidonBuiltinRunner(SimpleBuiltinRunner):
    def __init__(self, included: bool, instance_def: PoseidonInstanceDef):
        super().__init__(
            name="poseidon",
            included=included,
            ratio=None if instance_def is None else instance_def.ratio,
            cells_per_instance=instance_def.memory_cells_per_instance,
            n_input_cells=safe_div(instance_def.memory_cells_per_instance, 2),
        )
        self.instance_def: PoseidonInstanceDef = instance_def
        self.verified_addresses: Set[MaybeRelocatable] = set()
        self.cache: Dict[MaybeRelocatable, int] = {}

    def get_instance_def(self):
        return self.instance_def

    def is_input_cell(self, index: int) -> bool:
        return index < self.n_input_cells

    def add_auto_deduction_rules(self, runner):
        def rule(vm, addr, verified_addresses):
            memory = vm.run_context.memory
            index = addr.offset % self.cells_per_instance
            if self.is_input_cell(index):
                return
            if addr in self.cache:
                return self.cache[addr]
            first_input_addr = addr - index
            first_output_addr = first_input_addr + self.n_input_cells
            if first_output_addr in verified_addresses:
                return
            if not all(first_input_addr + i in memory for i in range(self.n_input_cells)):
                return

            for i in range(self.n_input_cells):
                value = memory[first_input_addr + i]
                assert vm.is_integer_value(value), (
                    f"{self.name} builtin: Expected integer at address {first_input_addr + i}. "
                    + f"Got: {value}."
                )
            input_state = memory.get_range(first_input_addr, self.n_input_cells)
            output_state = poseidon_perm(*input_state)
            for i in range(self.n_input_cells):
                self.cache[first_output_addr + i] = output_state[i]
            return self.cache[addr]

        runner.vm.add_auto_deduction_rule(self.base.segment_index, rule, self.verified_addresses)

    def air_private_input(self, runner) -> Dict[str, Any]:
        assert self.base is not None, "Uninitialized self.base."
        res: Dict[int, Any] = {}
        for addr, val in runner.vm_memory.items():
            if (
                not isinstance(addr, RelocatableValue)
                or addr.segment_index != self.base.segment_index
            ):
                continue
            idx, state_index = divmod(addr.offset, self.cells_per_instance)
            if not self.is_input_cell(state_index):
                continue

            assert isinstance(val, int)
            res.setdefault(idx, {"index": idx})[f"input_s{state_index}"] = hex(val)

        for index, item in res.items():
            for i in range(self.n_input_cells):
                assert f"input_s{i}" in item, f"Missing input #{i} of {self.name} instance {index}."

        return {self.name: sorted(res.values(), key=lambda item: item["index"])}
