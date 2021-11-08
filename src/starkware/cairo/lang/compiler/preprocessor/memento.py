import dataclasses
from abc import abstractmethod
from collections import ChainMap
from typing import Any, Dict, Generic, List, Mapping, MutableMapping, Tuple, Type, TypeVar

Self = TypeVar("Self")
T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


class Memento(Generic[T]):
    """
    Creates checkpoints for objects.
    The checkpoint can be used to restore the state of the object to a previous state.
    Example:
      value = [5]
      checkpoint, value = AppendOnlyListMemento[int].from_object(value)
      value += [3, 4]

      # value = checkpoint.apply(value) would result in value == [5, 3, 4]
      # value = checkpoint.restore(value) would result in value == [5]
    """

    @classmethod
    @abstractmethod
    def from_object(cls: Type[Self], value: T) -> Tuple[Self, T]:
        """
        Creates a checkpoint from an object. The original object should not be used until either
        restore() or apply() are called, and they should be called only once.
        Returns:
        * checkpoint - the interface to applying / restoring the checkpoint.
        * new_value - A object to be used instead of the old object. This behaves the same as the
          old object.
        """

    @abstractmethod
    def restore(self, value: T) -> T:
        """
        Restores the state at the time the checkpoint was created.
        Returns the new object to be used.
        Args:
        * object - the current instance of the object.
        """

    @abstractmethod
    def apply(self, value: T) -> T:
        """
        Applies the changes. The checkpoint should then be thrown away.
        Returns the new object to be used.
        Args:
        * object - the current instance of the object.
        """


@dataclasses.dataclass
class AppendOnlyListMemento(Generic[T], Memento[List[T]]):
    """
    Memento for append-only lists (lists whose elements are not modified, just appended).
    """

    # The size of the list at the time of the checkpoint.
    size: int

    @classmethod
    def from_object(cls, value: List[T]) -> Tuple["AppendOnlyListMemento", List[T]]:
        return cls(size=len(value)), value

    def restore(self, value: List[T]) -> List[T]:
        del value[self.size :]
        return value

    def apply(self, value: List[T]) -> List[T]:
        return value


@dataclasses.dataclass
class ChainMapMemento(Generic[K, V], Memento[MutableMapping[K, V]]):
    original: MutableMapping[K, V]
    updates: Dict[K, V]

    @classmethod
    def from_object(
        cls, value: MutableMapping[K, V]
    ) -> Tuple["ChainMapMemento", MutableMapping[K, V]]:
        updates: Dict[K, V] = {}
        return (
            cls(original=value, updates=updates),
            ChainMap(updates, value),
        )

    def restore(self, value: MutableMapping[K, V]) -> MutableMapping[K, V]:
        return self.original

    def apply(self, value: MutableMapping[K, V]) -> MutableMapping[K, V]:
        self.original.update(self.updates)
        return self.original


@dataclasses.dataclass
class ByValueMemento(Generic[T], Memento[T]):
    """
    Memento that stores the previous object instance, and returns it when restoring.
    """

    original: T

    @classmethod
    def from_object(cls, value: T) -> Tuple["ByValueMemento[T]", T]:
        return cls(original=value), value

    def restore(self, value: T) -> T:
        return self.original

    def apply(self, value: T) -> T:
        return value


TMembersMemento = TypeVar("TMembersMemento", bound="MembersMemento")


class MembersMemento(Generic[T], Memento[T]):
    """
    An abstract memento for general classes.
    Example usage:
      @dataclass
      class A:
        a: int

      class MyMemento(MembersMemento[A]):
        @classmethod
        def get_fields(cls) -> Mapping[str, Type[Memento]]:
          return dict(a=ByValueMemento[int])
    """

    def __init__(self, field_checkpoints: Dict[str, Any]):
        # A dictionary of mementos for each field.
        self.field_checkpoints = field_checkpoints

    @classmethod
    @abstractmethod
    def get_fields(cls) -> Mapping[str, Type[Memento]]:
        """
        A mapping from field name to a Memento class.
        """

    @classmethod
    def from_object(cls: Type[TMembersMemento], value: T) -> Tuple[TMembersMemento, T]:
        field_checkpoints: Dict[str, Any] = {}
        for name, memento_cls in cls.get_fields().items():
            checkpoint, new_value = memento_cls.from_object(getattr(value, name))
            field_checkpoints[name] = checkpoint
            setattr(value, name, new_value)
        return cls(field_checkpoints=field_checkpoints), value

    def restore(self, value: T) -> T:
        for name, memento_cls in self.field_checkpoints.items():
            new_value = memento_cls.restore(getattr(value, name))
            setattr(value, name, new_value)
        return value

    def apply(self, value: T) -> T:
        for name, memento_cls in self.field_checkpoints.items():
            new_value = memento_cls.apply(getattr(value, name))
            setattr(value, name, new_value)
        return value
