import dataclasses

from starkware.cairo.lang.builtins.instance_def import BuiltinInstanceDefWithLowRatio

CELLS_PER_RANGE_CHECK = 1


@dataclasses.dataclass
class RangeCheckInstanceDef(BuiltinInstanceDefWithLowRatio):
    # Number of 16-bit range checks that will be used for each instance of the builtin.
    # For example, n_parts=8 defines the range [0, 2^128).
    n_parts: int

    @property
    def memory_cells_per_instance(self) -> int:
        return CELLS_PER_RANGE_CHECK

    @property
    def range_check_units_per_builtin(self) -> int:
        return self.n_parts

    @property
    def invocation_height(self) -> int:
        return self.n_parts

    def get_diluted_units_per_builtin(self, diluted_spacing: int, diluted_n_bits: int) -> int:
        return 0
