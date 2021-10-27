import dataclasses

# Each bitwise operation consists of 5 cells (two inputs and three outputs - and, or, xor).
CELLS_PER_BITWISE = 5
INPUT_CELLS_PER_BITWISE = 2


@dataclasses.dataclass
class BitwiseInstanceDef:
    # Defines the ratio between the number of steps to the number of bitwise instances.
    # For every ratio steps, we have one instance.
    ratio: int

    # The number of bits in a single field element that are supported by the bitwise builtin.
    total_n_bits: int

    @property
    def cells_per_builtin(self):
        return CELLS_PER_BITWISE

    @property
    def range_check_units_per_builtin(self):
        return 0
