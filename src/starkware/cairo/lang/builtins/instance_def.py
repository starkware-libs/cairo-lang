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
    def cells_per_builtin(self) -> int:
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
