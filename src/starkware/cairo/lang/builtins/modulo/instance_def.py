import dataclasses

from starkware.cairo.lang.builtins.instance_def import BuiltinInstanceDef

HEIGHT = 1


@dataclasses.dataclass
class AddModInstanceDef(BuiltinInstanceDef):
    # The parameters of the presentation of large integers in felts. Each number is composed of
    # n_words felts, each containing a value in [0, 2**word_bit_len), to represent
    # n_words * word_bit_len bit-long integers.
    # E.g., for 384-bit numbers, use word_bit_len = 96 and n_words = 4.
    word_bit_len: int
    n_words: int

    @property
    def memory_cells_per_instance(self) -> int:
        # The user-facing memory has n_words + 3 memory cells per instance (p, n and two pointers),
        # and the additional memory contains 3*(n_words + 1) memory cells, for offsets and values
        # of each of a, b, and c.
        return 4 * self.n_words + 6

    @property
    def range_check_units_per_builtin(self) -> int:
        # No range check units in the builtin itself. The range check is done externally.
        return 0

    @property
    def invocation_height(self) -> int:
        return HEIGHT

    def get_diluted_units_per_builtin(self, diluted_spacing: int, diluted_n_bits: int) -> int:
        return 0
