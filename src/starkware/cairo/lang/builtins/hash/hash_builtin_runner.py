from typing import Any, Dict, Optional, Set

from starkware.cairo.lang.builtins.hash.instance_def import CELLS_PER_HASH, INPUT_CELLS_PER_HASH
from starkware.cairo.lang.vm.builtin_runner import BuiltinVerifier, SimpleBuiltinRunner
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.python.math_utils import safe_div


class HashBuiltinRunner(SimpleBuiltinRunner):
    def __init__(self, name: str, included: bool, ratio: int, hash_func):
        super().__init__(
            name=name,
            included=included,
            ratio=ratio,
            cells_per_instance=CELLS_PER_HASH,
            n_input_cells=INPUT_CELLS_PER_HASH,
        )
        self.hash_func = hash_func
        self.stop_ptr: Optional[RelocatableValue] = None
        self.verified_addresses: Set[MaybeRelocatable] = set()

    def add_auto_deduction_rules(self, runner):
        def rule(vm, addr, verified_addresses):
            memory = vm.run_context.memory
            if addr.offset % CELLS_PER_HASH != 2:
                return
            if addr in verified_addresses:
                return
            if addr - 1 not in memory or addr - 2 not in memory:
                return
            assert vm.is_integer_value(memory[addr - 2]), (
                f"{self.name} builtin: Expected integer at address {addr - 2}. "
                + f"Got: {memory[addr - 2]}."
            )
            assert vm.is_integer_value(memory[addr - 1]), (
                f"{self.name} builtin: Expected integer at address {addr - 1}. "
                + f"Got: {memory[addr - 1]}."
            )
            res = self.hash_func(memory[addr - 2], memory[addr - 1])
            verified_addresses.add(addr)
            return res

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
            idx, typ = divmod(addr.offset, CELLS_PER_HASH)
            if typ == 2:
                continue

            assert isinstance(val, int)
            res.setdefault(idx, {"index": idx})["x" if typ == 0 else "y"] = hex(val)

        for index, item in res.items():
            assert "x" in item, f"Missing first input of {self.name} instance {index}."
            assert "y" in item, f"Missing second input of {self.name} instance {index}."

        return {self.name: sorted(res.values(), key=lambda item: item["index"])}

    def get_additional_data(self):
        return [list(RelocatableValue.to_tuple(x)) for x in sorted(self.verified_addresses)]

    def extend_additional_data(self, data, relocate_callback, data_is_trusted=True):
        if not data_is_trusted:
            return

        for addr in data:
            self.verified_addresses.add(relocate_callback(RelocatableValue.from_tuple(addr)))


class HashBuiltinVerifier(BuiltinVerifier):
    def __init__(self, included: bool, ratio):
        self.included = included
        self.ratio = ratio

    def expected_stack(self, public_input):
        if not self.included:
            return [], []

        addresses = public_input.memory_segments["pedersen"]
        max_size = CELLS_PER_HASH * safe_div(public_input.n_steps, self.ratio)
        assert (
            0
            <= addresses.begin_addr
            <= addresses.stop_ptr
            <= addresses.begin_addr + max_size
            < 2 ** 64
        )
        return [addresses.begin_addr], [addresses.stop_ptr]
