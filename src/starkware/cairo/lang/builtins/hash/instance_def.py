import dataclasses
from typing import Optional

from starkware.cairo.lang.builtins.instance_def import BuiltinInstanceDef

# Each hash consists of 3 cells (two inputs and one output).
CELLS_PER_HASH = 3
INPUT_CELLS_PER_HASH = 2


@dataclasses.dataclass
class PedersenInstanceDef(BuiltinInstanceDef):
    # Split to this many different components - for optimization.
    repetitions: int

    # Size of hash.
    element_height: int
    element_bits: int
    # Number of inputs for hash.
    n_inputs: int
    # The upper bound on the hash inputs. If None, the upper bound is 2^element_bits.
    hash_limit: Optional[int] = None

    @property
    def memory_cells_per_instance(self) -> int:
        return CELLS_PER_HASH

    @property
    def range_check_units_per_builtin(self) -> int:
        return 0

    @property
    def invocation_height(self) -> int:
        return self.element_height * self.n_inputs

    def get_diluted_units_per_builtin(self, diluted_spacing: int, diluted_n_bits: int) -> int:
        return 0
