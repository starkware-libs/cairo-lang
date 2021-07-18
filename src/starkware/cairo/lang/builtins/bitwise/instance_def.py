import dataclasses

# Each bitwise operation consists of 5 cells (two inputs and three outputs - and, or, xor).
CELLS_PER_BITWISE = 5


@dataclasses.dataclass
class BitwiseInstanceDef:
    # Defines the ratio between the number of steps to the number of bitwise instances.
    # For every ratio steps, we have one instance.
    ratio: int

    diluted_spacing: int
    diluted_n_bits: int
    total_n_bits: int
