from typing import Any, Dict, Optional, Tuple

from starkware.cairo.lang.vm.builtin_runner import BuiltinVerifier, SimpleBuiltinRunner
from starkware.cairo.lang.vm.relocatable import RelocatableValue
from starkware.python.math_utils import safe_div


class RangeCheckBuiltinRunner(SimpleBuiltinRunner):
    def __init__(self, included: bool, ratio, inner_rc_bound, n_parts):
        super().__init__('range_check', included, ratio)
        self.inner_rc_bound = inner_rc_bound
        self.bound = inner_rc_bound ** n_parts
        self.n_parts = n_parts

    def add_validation_rules(self, runner):
        def rule(memory, addr):
            value = memory[addr]
            assert isinstance(value, int), \
                f'Range-check builtin: Expected value at address {addr} to be an integer. ' \
                f'Got: {value}.'
            # The range check builtin asserts that 0 <= value < BOUND.
            # For example, if the layout uses 8 16-bit range-checks per instance,
            # bound will be 2**(16 * 8) = 2**128.
            assert 0 <= value < self.bound, \
                f'Value {value}, in range check builtin {addr - self.base}, is out of range ' \
                f'[0, {self.bound}).'
            return {addr}

        runner.vm.add_validation_rule(self.base.segment_index, rule)

    def air_private_input(self, runner) -> Dict[str, Any]:
        assert self.base is not None, 'Uninitialized self.base.'
        res: Dict[int, Any] = {}
        for addr, val in runner.vm_memory.items():
            if not isinstance(addr, RelocatableValue) or \
                    addr.segment_index != self.base.segment_index:
                continue
            idx = addr.offset

            assert isinstance(val, int)
            res[idx] = {'index': idx, 'value': hex(val)}

        return {'range_check': sorted(res.values(), key=lambda item: item['index'])}

    def get_range_check_usage(self, runner) -> Optional[Tuple[int, int]]:
        assert self.base is not None, 'Uninitialized self.base.'
        rc_min = None
        rc_max = None
        for addr, val in runner.vm_memory.items():
            if not isinstance(addr, RelocatableValue) or \
                    addr.segment_index != self.base.segment_index:
                continue

            # Split val into n_parts parts.
            for _ in range(self.n_parts):
                part_val = val % self.inner_rc_bound

                if rc_min is None:
                    rc_min = rc_max = part_val
                else:
                    rc_min = min(rc_min, part_val)
                    rc_max = max(rc_max, part_val)
                val //= self.inner_rc_bound
        if rc_min is None or rc_max is None:
            return None
        return rc_min, rc_max

    def get_used_perm_range_check_units(self, runner) -> int:
        used_cells, _ = self.get_used_cells_and_allocated_size(runner)
        # Each cell in the range check segment requires n_parts range check units.
        return used_cells * self.n_parts


class RangeCheckBuiltinVerifier(BuiltinVerifier):
    def __init__(self, included: bool, ratio):
        self.included = included
        self.ratio = ratio

    def expected_stack(self, public_input):
        if not self.included:
            return [], []

        addresses = public_input.memory_segments['range_check']
        max_size = safe_div(public_input.n_steps, self.ratio)
        assert 0 <= addresses.begin_addr <= addresses.stop_ptr <= \
            addresses.begin_addr + max_size < 2**64
        return [addresses.begin_addr], [addresses.stop_ptr]
