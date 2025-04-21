from typing import Any, Dict, Optional

from starkware.cairo.common.keccak_utils.keccak_utils import keccak_f
from starkware.cairo.lang.builtins.keccak.instance_def import KeccakInstanceDef
from starkware.cairo.lang.vm.builtin_runner import SimpleBuiltinRunner
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.python.math_utils import safe_div
from starkware.python.utils import from_bytes, safe_zip, to_bytes


def is_keccak_input_cell(index: int, n_input_cells: int) -> bool:
    return index < n_input_cells


def keccak_auto_deduction_rule_wrapper(
    keccak_cache, instance_def: Optional[KeccakInstanceDef] = None
):
    """
    Returns an auto-deduction rule for the keccak builtin to be used by the vm.
    Defined in the builtin runner, or manually in a hint by the program.
    """
    if instance_def is not None:
        state_rep = instance_def.state_rep
        cells_per_instance = instance_def.memory_cells_per_instance
    else:
        state_rep = [200] * 8  # Set the keccak state to be represented by 8 felts of 200 bits each.
        cells_per_instance = 16

    n_input_cells = safe_div(cells_per_instance, 2)

    def rule(vm, addr):
        memory = vm.run_context.memory
        index = addr.offset % cells_per_instance
        if is_keccak_input_cell(index=index, n_input_cells=n_input_cells):
            # This is an input cell.
            return
        if addr in keccak_cache:
            return keccak_cache[addr]
        first_input_addr = addr - index
        first_output_addr = first_input_addr + n_input_cells
        if not all(first_input_addr + i in memory for i in range(n_input_cells)):
            return

        for i, bits in enumerate(state_rep):
            value = memory[first_input_addr + i]
            assert vm.is_integer_value(value), (
                f"Keccak builtin: Expected integer at address {first_input_addr + i}. "
                + f"Got: {value}."
            )
            assert 0 <= value < 2**bits, (
                f"Keccak builtin: Expected integer at address {first_input_addr + i} "
                + f"to be smaller than 2^{bits}. Got: {value}."
            )
        input_felts = [memory[first_input_addr + i] for i in range(n_input_cells)]
        output_bytes = keccak_f(
            b"".join(
                to_bytes(value, safe_div(bits, 8), "little")
                for value, bits in safe_zip(input_felts, state_rep)
            )
        )
        start_index = 0
        for i, bits in enumerate(state_rep):
            end_index = start_index + safe_div(bits, 8)
            keccak_cache[first_output_addr + i] = from_bytes(
                output_bytes[start_index:end_index], byte_order="little"
            )
            start_index = end_index
        return keccak_cache[addr]

    return rule


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

    def add_auto_deduction_rules(self, runner):
        runner.vm.add_auto_deduction_rule(
            self.base.segment_index,
            keccak_auto_deduction_rule_wrapper(
                keccak_cache=self.cache, instance_def=self.instance_def
            ),
        )

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
            if not is_keccak_input_cell(index=state_index, n_input_cells=self.n_input_cells):
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
