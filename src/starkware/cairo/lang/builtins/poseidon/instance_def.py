import dataclasses
from typing import List, Optional

from starkware.cairo.common.poseidon_utils import PoseidonParams


@dataclasses.dataclass
class PoseidonInstanceDef:
    # Defines the ratio between the number of steps to the number of Poseidon invocations.
    # None means dynamic ratio.
    ratio: Optional[int]

    # Defines the Hades permutation.
    params: PoseidonParams

    # Defines the partition of the partial rounds to virtual columns.
    partial_rounds_partition: List[int]

    @property
    def cells_per_builtin(self):
        return 2 * self.params.m

    @property
    def range_check_units_per_builtin(self):
        return 0
