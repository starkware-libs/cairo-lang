import dataclasses
from abc import abstractmethod
from typing import Optional, Sequence

from starkware.cairo.lang.compiler.ast.formatting_utils import LocationField
from starkware.cairo.lang.compiler.ast.node import AstNode
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.scoped_name import ScopedName


class CairoType(AstNode):
    location: Optional[Location]

    @abstractmethod
    def format(self) -> str:
        """
        Returns a representation of the type as a string.
        """

    def get_pointer_type(self) -> 'CairoType':
        """
        Returns a type of a pointer to the current type.
        """
        return TypePointer(pointee=self, location=self.location)


@dataclasses.dataclass
class TypeFelt(CairoType):
    location: Optional[Location] = LocationField

    def format(self):
        return 'felt'

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return []


@dataclasses.dataclass
class TypePointer(CairoType):
    pointee: CairoType
    location: Optional[Location] = LocationField

    def format(self):
        return f'{self.pointee.format()}*'

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.pointee]


@dataclasses.dataclass
class TypeStruct(CairoType):
    scope: ScopedName
    # Indicates whether scope refers to the fully resolved name.
    is_fully_resolved: bool
    location: Optional[Location] = LocationField

    def format(self):
        return str(self.scope)

    @property
    def resolved_scope(self):
        """
        Verifies that is_fully_resolved=True and returns scope.
        """
        assert self.is_fully_resolved, 'Type is expected to be fully resolved at this point.'
        return self.scope

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return []
