import dataclasses
from typing import Optional

from starkware.cairo.lang.builtins.instance_def import BuiltinInstanceDef

# Each EC operation P + m * Q = R contains 7 cells: P_x, P_y, Q_x, Q_y, m, R_x, R_y.
CELLS_PER_EC_OP = 7
INPUT_CELLS_PER_EC_OP = 5


@dataclasses.dataclass
class EcOpInstanceDef(BuiltinInstanceDef):
    # Size of coefficient.
    scalar_height: int
    scalar_bits: int
    # The upper bound on the multiplication scalar, m. If None, the upper bound is 2^scalar_bits.
    scalar_limit: Optional[int] = None

    @property
    def memory_cells_per_instance(self) -> int:
        return CELLS_PER_EC_OP

    @property
    def range_check_units_per_builtin(self) -> int:
        return 0

    @property
    def invocation_height(self) -> int:
        return self.scalar_height

    def get_diluted_units_per_builtin(self, diluted_spacing: int, diluted_n_bits: int) -> int:
        return 0
