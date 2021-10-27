import dataclasses
from typing import Optional

# Each EC operation P + m * Q = R contains 7 cells: P_x, P_y, Q_x, Q_y, m, R_x, R_y.
CELLS_PER_EC_OP = 7
INPUT_CELLS_PER_EC_OP = 5


@dataclasses.dataclass
class EcOpInstanceDef:
    # Defines the ratio between the number of steps to the number of EC op instances.
    # For every ratio steps, we have one instance.
    ratio: int

    # Size of coefficient.
    scalar_height: int
    scalar_bits: int
    # The upper bound on the multiplication scalar, m. If None, the upper bound is 2^scalar_bits.
    scalar_limit: Optional[int] = None

    @property
    def cells_per_builtin(self):
        return CELLS_PER_EC_OP

    @property
    def range_check_units_per_builtin(self):
        return 0
