import dataclasses

from starkware.cairo.lang.builtins.instance_def import BuiltinInstanceDef

# Each bitwise operation consists of 5 cells (two inputs and three outputs - and, or, xor).
CELLS_PER_BITWISE = 5
HEIGHT = 64
INPUT_CELLS_PER_BITWISE = 2


@dataclasses.dataclass
class BitwiseInstanceDef(BuiltinInstanceDef):
    # The number of bits in a single field element that are supported by the bitwise builtin.
    total_n_bits: int

    @property
    def memory_cells_per_instance(self) -> int:
        return CELLS_PER_BITWISE

    @property
    def range_check_units_per_builtin(self) -> int:
        return 0

    @property
    def invocation_height(self) -> int:
        return HEIGHT

    def get_diluted_units_per_builtin(self, diluted_spacing: int, diluted_n_bits: int) -> int:
        """
        Calculates the number of diluted check units used by one bitwise builtin.
        """
        partition = [
            i + j
            for i in range(0, self.total_n_bits, diluted_spacing * diluted_n_bits)
            for j in range(diluted_spacing)
            if i + j < self.total_n_bits
        ]
        num_trimmed = len(
            [
                1
                for shift in partition
                if shift + diluted_spacing * (diluted_n_bits - 1) + 1 > self.total_n_bits
            ]
        )
        return 4 * len(partition) + num_trimmed
