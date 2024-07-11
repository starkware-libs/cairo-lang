import dataclasses
from abc import abstractmethod
from typing import Optional


# Mypy has a problem with dataclasses that contain unimplemented abstract methods.
# See https://github.com/python/mypy/issues/5374 for details on this problem.
@dataclasses.dataclass  # type: ignore[misc]
class BuiltinInstanceDef:
    # Defines the ratio between the number of steps to the number of builtin instances.
    # For every ratio steps, we have one instance.
    # None means dynamic ratio.
    ratio: Optional[int]

    @property
    @abstractmethod
    def memory_cells_per_instance(self) -> int:
        """
        The number of memory cells used by one builtin.
        """

    @property
    @abstractmethod
    def range_check_units_per_builtin(self) -> int:
        """
        The number of range check units used by one builtin.
        """

    @property
    @abstractmethod
    def invocation_height(self) -> int:
        """
        The height in rows used by one invocation of the builtin.
        """

    @abstractmethod
    def get_diluted_units_per_builtin(self, diluted_spacing: int, diluted_n_bits: int) -> int:
        """
        Returns the number of diluted check units used by one builtin.
        """

    def uses_dynamic_ratio(self) -> bool:
        return self.ratio is None

    def is_used(self) -> bool:
        assert self.ratio is not None, "ratio must be non-dynamic - it must have an integer value."
        return self.ratio != 0

    def get_ratio_den(self) -> int:
        """
        Returns 1, as this builtin does not support a fractional ratio.
        """
        return 1


# Mypy has a problem with dataclasses that contain unimplemented abstract methods.
# See https://github.com/python/mypy/issues/5374 for details on this problem.
@dataclasses.dataclass  # type: ignore[misc]
class BuiltinInstanceDefWithLowRatio(BuiltinInstanceDef):
    # Some builtins can have ratios smaller than one, which we encode with ratio=1 and
    # ratio_den = 1/ratio. In other words, the real ratio is ratio/ratio_den, and at least one of
    # ratio or ratio_den should equal 1.
    ratio_den: int

    def get_ratio_den(self) -> int:
        """
        Returns the denominator of the builtin's ratio.
        """
        return self.ratio_den
