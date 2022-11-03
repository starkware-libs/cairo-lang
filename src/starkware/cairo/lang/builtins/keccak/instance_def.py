import dataclasses
from typing import List


@dataclasses.dataclass
class KeccakInstanceDef:
    # Defines the ratio between the number of steps to the number of Keccak invocations.
    # Note that diluted_n_bits invocations fit into one component instance, hence for every
    # (diluted_n_bits * ratio) steps, we have one Keccak component instance.
    ratio: int

    # The input and output are 1600 bits that are represented using a sequence of field elements in
    # the following pattern. For example [64] * 25 means 25 field elements each containing 64 bits.
    state_rep: List[int]

    # Should equal n_diluted_bits.
    instances_per_component: int

    @property
    def cells_per_builtin(self):
        return 2 * len(self.state_rep)

    @property
    def range_check_units_per_builtin(self):
        return 0
