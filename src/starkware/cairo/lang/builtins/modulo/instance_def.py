import dataclasses
from abc import abstractmethod

from starkware.cairo.lang.builtins.instance_def import BuiltinInstanceDefWithLowRatio
from starkware.python.math_utils import div_ceil, log2_ceil, safe_div


# Mypy has a problem with dataclasses that contain unimplemented abstract methods.
# See https://github.com/python/mypy/issues/5374 for details on this problem.
@dataclasses.dataclass  # type: ignore[misc]
class ModInstanceDef(BuiltinInstanceDefWithLowRatio):
    # The parameters of the presentation of large integers in felts. Each number is composed of
    # n_words felts, each containing a value in [0, 2**word_bit_len), to represent
    # n_words * word_bit_len bit-long integers.
    # E.g., for 384-bit numbers, use word_bit_len = 96 and n_words = 4.
    word_bit_len: int
    n_words: int
    batch_size: int

    @property
    def memory_cells_per_instance(self) -> int:
        # The user-facing memory has n_words + 3 memory cells per instance (p, n and two pointers),
        # and the additional memory contains 3*(n_words + 1) memory cells, for offsets and values
        # of each of a, b, and c.
        return self.n_words + 3 + self.batch_size * 3 * (self.n_words + 1)

    @property
    @abstractmethod
    def range_check_units_per_builtin(self) -> int:
        pass

    @property
    def invocation_height(self) -> int:
        # Both add_mod and mul_mod have virtual columns such as the carries whose height is
        # batch_size, yet no virtual column is of height greater than batch_size.
        return self.batch_size

    def get_diluted_units_per_builtin(self, diluted_spacing: int, diluted_n_bits: int) -> int:
        return 0


@dataclasses.dataclass
class AddModInstanceDef(ModInstanceDef):
    @property
    def range_check_units_per_builtin(self) -> int:
        # No range check units in the builtin itself. The range check is done externally.
        return 0


@dataclasses.dataclass
class MulModInstanceDef(ModInstanceDef):
    # The bits in the basic range check units, needed to calculate the amount used by the builtin.
    bits_per_part: int = 16

    @property
    def p_multiplier_n_parts(self):
        return safe_div(self.word_bit_len, self.bits_per_part)

    """
    Let W = 2**word_bit_len.
    Each carry in the computation of a * b - k * p - c is the sum of up to <n_words> positive
    terms from a * b, each having absolute value < W**2, <n_words> negative terms from k * p,
    each having absolute value < W**2, and a negative term from c, having absolute value < W.

    Therefore each carry is in the (closed) range [-n_words * W**2 - W + 1, n_words * W**2 - 1].
    This can be tightened to [-n_words * W**2, n_words * W**2 - W] based on the fact that carries
    are always a multiple of W.

    We store each carry c_i in a trace cell having value (c_i / W) + carry_offset. Choosing
    carry_offset = n_words * W ensures that the trace cell will have a non-negative value.

    Therefore the maximal value of a carry trace cell is (2 * n_words * W - 1).
    """

    @property
    def carry_n_parts(self):
        # The number of parts required to represent the maximal carry trace cell value.
        return self.p_multiplier_n_parts + div_ceil(log2_ceil(self.n_words) + 1, self.bits_per_part)

    @property
    def carry_offset(self):
        return self.n_words * (1 << self.word_bit_len)

    @property
    def range_check_units_per_builtin(self) -> int:
        # The carry requires 2 * (n_words - 1) * carry_n_parts range check units and p_multiplier
        # requires n_words * p_multiplier_n_parts units for each (a,b,c) tuple, of which there are
        # self.batch_size in an instance.
        return (
            self.n_words * self.p_multiplier_n_parts + 2 * (self.n_words - 1) * self.carry_n_parts
        ) * self.batch_size
