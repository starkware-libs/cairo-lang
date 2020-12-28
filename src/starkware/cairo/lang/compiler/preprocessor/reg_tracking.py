import dataclasses
from abc import ABC, abstractmethod
from typing import Callable, Union

from starkware.cairo.lang.compiler.ast.expr import ExprConst, Expression

RegChangeLike = Union[Union[int, Expression, 'RegChange']]


class RegChange(ABC):
    """
    Represents a change in the value of a register.
    Can be either RegChangeKnown(int), RegChangeUnknown() or RegChangeUnconstrained().
    """

    @abstractmethod
    def __add__(self, other):
        pass

    def __radd__(self, other):
        return self + other

    @abstractmethod
    def __and__(self, other):
        pass

    def __rand__(self, other):
        return self & other

    @staticmethod
    def from_expr(expr: RegChangeLike):
        if isinstance(expr, int):
            return RegChangeKnown(expr)
        if isinstance(expr, RegChange):
            return expr
        if not isinstance(expr, Expression):
            raise TypeError
        if isinstance(expr, ExprConst):
            return RegChangeKnown(expr.val)
        return RegChangeUnknown()


@dataclasses.dataclass(frozen=True)
class RegChangeUnconstrained(RegChange):
    def __add__(self, other: RegChange):
        raise TypeError

    def __and__(self, other: RegChange):
        other = RegChange.from_expr(other)
        return other


@dataclasses.dataclass(frozen=True)
class RegChangeUnknown(RegChange):
    def __add__(self, other: RegChange):
        return self

    def __and__(self, other: RegChange):
        return self


@dataclasses.dataclass(frozen=True)
class RegChangeKnown(RegChange):
    value: int

    def __add__(self, other: RegChangeLike):
        other = RegChange.from_expr(other)
        if not isinstance(other, RegChangeKnown):
            return NotImplemented
        return RegChangeKnown(self.value + other.value)

    def __and__(self, other: RegChangeLike):
        other = RegChange.from_expr(other)
        if not isinstance(other, RegChangeKnown):
            return NotImplemented
        if self.value != other.value:
            return RegChangeUnknown()
        return RegChangeKnown(self.value)


@dataclasses.dataclass(frozen=True)
class RegTrackingData:
    """
    Used to track the progress of a register during a run.
    As long as tracking is possible (i.e., no unknown changes to ap or fp), offset will change
    according to the instruction.
    Once an unknown change happens, group will increase by 1. Different group
    numbers mean that it is not possible to deduce what happened to the register between the two
    locations. Within the same group, offset increases the same way the register does (so the
    difference between the two is constant). Therefore, given the register at one point, it is
    possible to deduce the register at another pointer (as long as both points belong to the same
    group).
    """
    group: int = 0
    offset: int = 0

    @classmethod
    def new(cls, group_alloc: Callable) -> 'RegTrackingData':
        return cls(
            group=group_alloc(),
            offset=0,
        )

    def __sub__(self, other: 'RegTrackingData') -> RegChange:
        """
        If possible, returns the difference between the values of ap between self and other.
        Otherwise, returns RegChangeUnknown.
        """
        if not isinstance(other, RegTrackingData):
            return NotImplemented
        if self.group != other.group:
            return RegChangeUnknown()
        return RegChangeKnown(self.offset - other.offset)

    def add(self, change: RegChangeLike, group_alloc: Callable) -> 'RegTrackingData':
        change = RegChange.from_expr(change)
        if isinstance(change, RegChangeKnown):
            return RegTrackingData(group=self.group, offset=self.offset + change.value)
        if isinstance(change, RegChangeUnknown):
            return RegTrackingData(group=group_alloc(), offset=0)
        raise NotImplementedError(f'Unsupported change type {type(change).__name__}')

    def converge(self, other: 'RegTrackingData', group_alloc: Callable):
        if not isinstance(other, RegTrackingData):
            return other.converge(self, group_alloc)
        if self != other:
            return type(self).new(group_alloc)
        return self
