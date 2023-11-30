from typing import Any, Dict

from starkware.cairo.common.keccak_utils.keccak_utils import keccak_f
from starkware.cairo.lang.builtins.keccak.instance_def import KeccakInstanceDef
from starkware.cairo.lang.vm.builtin_runner import SimpleBuiltinRunner
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.python.math_utils import safe_div
from starkware.python.utils import from_bytes, safe_zip, to_bytes


class KeccakBuiltinRunner(SimpleBuiltinRunner):
    def __init__(self, included: bool, instance_def: KeccakInstanceDef):
        super().__init__(
            name="keccak",
            included=included,
            ratio=None if instance_def is None else instance_def.ratio,
            instances_per_component=instance_def.instances_per_component,
            cells_per_instance=instance_def.memory_cells_per_instance,
            n_input_cells=safe_div(instance_def.memory_cells_per_instance, 2),
        )
        self.instance_def: KeccakInstanceDef = instance_def
        self.cache: Dict[MaybeRelocatable, int] = {}

    def get_instance_def(self):
        return self.instance_def

    def is_input_cell(self, index: int) -> bool:
        return index < self.n_input_cells

    def add_auto_deduction_rules(self, runner):
        def rule(vm, addr):
            memory = vm.run_context.memory
            index = addr.offset % self.cells_per_instance
            if self.is_input_cell(index):
                return
            if addr in self.cache:
                return self.cache[addr]
            first_input_addr = addr - index
            first_output_addr = first_input_addr + self.n_input_cells
            if not all(first_input_addr + i in memory for i in range(self.n_input_cells)):
                return

            for i, bits in enumerate(self.instance_def.state_rep):
                value = memory[first_input_addr + i]
                assert vm.is_integer_value(value), (
                    f"{self.name} builtin: Expected integer at address {first_input_addr + i}. "
                    + f"Got: {value}."
                )
                assert 0 <= value < 2**bits, (
                    f"{self.name} builtin: Expected integer at address {first_input_addr + i} "
                    + f"to be smaller than 2^{bits}. Got: {value}."
                )
            input_felts = [memory[first_input_addr + i] for i in range(self.n_input_cells)]
            output_bytes = keccak_f(
                b"".join(
                    to_bytes(value, safe_div(bits, 8), "little")
                    for value, bits in safe_zip(input_felts, self.instance_def.state_rep)
                )
            )
            start_index = 0
            for i, bits in enumerate(self.instance_def.state_rep):
                end_index = start_index + safe_div(bits, 8)
                self.cache[first_output_addr + i] = from_bytes(
                    output_bytes[start_index:end_index], byte_order="little"
                )
                start_index = end_index
            return self.cache[addr]

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
            idx, state_index = divmod(addr.offset, self.cells_per_instance)
            if not self.is_input_cell(state_index):
                continue

            assert isinstance(val, int)
            res.setdefault(idx, {"index": idx})[f"input_s{state_index}"] = hex(val)

        for index, item in res.items():
            for i in range(self.n_input_cells):
                assert f"input_s{i}" in item, f"Missing input #{i} of {self.name} instance {index}."

        return {self.name: sorted(res.values(), key=lambda item: item["index"])}

    def get_used_diluted_check_units(self, diluted_spacing: int, diluted_n_bits: int) -> int:
        return self.instance_def.get_diluted_units_per_builtin(
            diluted_spacing=diluted_spacing, diluted_n_bits=diluted_n_bits
        )
