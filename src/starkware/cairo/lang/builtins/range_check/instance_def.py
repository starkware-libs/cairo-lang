import dataclasses
from typing import Optional

CELLS_PER_RANGE_CHECK = 1


@dataclasses.dataclass
class RangeCheckInstanceDef:
    # Defines the ratio between the number of steps to the number of range check instances.
    # For every ratio steps, we have one instance.
    # None means dynamic ratio.
    ratio: Optional[int]
    # Number of 16-bit range checks that will be used for each instance of the builtin.
    # For example, n_parts=8 defines the range [0, 2^128).
    n_parts: int

    @property
    def cells_per_builtin(self):
        return CELLS_PER_RANGE_CHECK

    @property
    def range_check_units_per_builtin(self):
        return self.n_parts
