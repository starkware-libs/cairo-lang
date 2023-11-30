import dataclasses
from typing import List

from starkware.cairo.lang.builtins.instance_def import BuiltinInstanceDef
from starkware.python.math_utils import next_power_of_2

POSEIDON_M = 3


@dataclasses.dataclass
class PoseidonInstanceDef(BuiltinInstanceDef):
    # Defines the partition of the partial rounds to virtual columns.
    partial_rounds_partition: List[int]

    @property
    def memory_cells_per_instance(self) -> int:
        return 2 * POSEIDON_M

    @property
    def range_check_units_per_builtin(self) -> int:
        return 0

    @property
    def invocation_height(self) -> int:
        # The virtual columns of poseidon hash are:
        # 1. full_rounds_state{i} - whose height is Rf = number of full rounds = 8.
        # 2. partial_rounds_state{part} - whose height is self.partial_rounds_partition[part].
        # 3. The squares of the above, which have the same sizes.
        # The total height is defined by the maximum of all sizes.
        return next_power_of_2(max([8] + self.partial_rounds_partition))

    def get_diluted_units_per_builtin(self, diluted_spacing: int, diluted_n_bits: int) -> int:
        return 0
