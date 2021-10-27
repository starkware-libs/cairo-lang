import dataclasses
from typing import Optional

# Each hash consists of 3 cells (two inputs and one output).
CELLS_PER_HASH = 3
INPUT_CELLS_PER_HASH = 2


@dataclasses.dataclass
class PedersenInstanceDef:
    # Defines the ratio between the number of steps to the number of pedersen instances.
    # For every ratio steps, we have one instance.
    ratio: int

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
    def cells_per_builtin(self):
        return CELLS_PER_HASH

    @property
    def range_check_units_per_builtin(self):
        return 0
