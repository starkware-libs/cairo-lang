import dataclasses
from typing import List, Optional

POSEIDON_M = 3


@dataclasses.dataclass
class PoseidonInstanceDef:
    # Defines the ratio between the number of steps to the number of Poseidon invocations.
    # None means dynamic ratio.
    ratio: Optional[int]

    # Defines the partition of the partial rounds to virtual columns.
    partial_rounds_partition: List[int]

    @property
    def cells_per_builtin(self):
        return 2 * POSEIDON_M

    @property
    def range_check_units_per_builtin(self):
        return 0
