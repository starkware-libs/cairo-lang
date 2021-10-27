import dataclasses
from typing import List


@dataclasses.dataclass
class KeccakInstanceDef:
    # Defines the ratio between the number of steps to the number of Keccak instances.
    # For every ratio steps, we have one instance that computes diluted_n_bits Keccak invocations.
    ratio: int

    # The input and output are 1600 bits that are represented using a sequence of field elements in
    # the following pattern. For example [64] * 25 means 25 field elements each containing 64 bits.
    state_rep: List[int]

    @property
    def cells_per_builtin(self):
        return 2 * len(self.state_rep)

    @property
    def range_check_units_per_builtin(self):
        return 0
