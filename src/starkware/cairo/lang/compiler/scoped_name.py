import dataclasses
from typing import ClassVar, Tuple, Union

import marshmallow.fields as mfields


@dataclasses.dataclass(frozen=True)
class ScopedName:
    SEPARATOR: ClassVar[str] = '.'
    path: Tuple[str, ...] = ()

    def __post_init__(self):
        assert '' not in self.path, 'Empty namespace is not supported.'
        assert all([self.SEPARATOR not in part for part in self.path])

    @classmethod
    def from_string(cls, scope: str):
        if scope == '':
            # Handle the special case of an empty tuple.
            return cls()
        return cls(tuple(scope.split(cls.SEPARATOR)))

    def __str__(self) -> str:
        return self.SEPARATOR.join(self.path)

    def __len__(self) -> int:
        """
        Returns the scope path length.
        """
        return len(self.path)

    def startswith(self, other: Union[str, 'ScopedName']) -> bool:
        if isinstance(other, str):
            return self.startswith(self.from_string(other))

        assert isinstance(other, ScopedName)
        return self[:len(other)] == other

    def __add__(self, other: Union[str, 'ScopedName']):
        if isinstance(other, str):
            return self + ScopedName.from_string(other)

        assert isinstance(other, ScopedName)
        return ScopedName(self.path + other.path)

    def __getitem__(self, index: slice):
        assert isinstance(index, slice)
        return ScopedName(path=self.path[index])


class ScopedNameAsStr(mfields.Field):
    """
    A field that behaves like a ScopedName, but serializes to a string.
    """

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        assert isinstance(value, ScopedName)
        return str(value)

    def _deserialize(self, value, attr, data, **kwargs):
        return ScopedName.from_string(value)
