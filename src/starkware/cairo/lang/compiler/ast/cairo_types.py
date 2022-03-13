import dataclasses
from abc import abstractmethod
from enum import Enum, auto
from typing import List, Optional, Sequence

from starkware.cairo.lang.compiler.ast.formatting_utils import LocationField
from starkware.cairo.lang.compiler.ast.node import AstNode
from starkware.cairo.lang.compiler.ast.notes import Notes
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.scoped_name import ScopedName


class CairoType(AstNode):
    location: Optional[Location]

    @abstractmethod
    def format(self) -> str:
        """
        Returns a representation of the type as a string.
        """

    def get_pointer_type(self) -> "CairoType":
        """
        Returns a type of a pointer to the current type.
        """
        return TypePointer(pointee=self, location=self.location)


@dataclasses.dataclass
class TypeFelt(CairoType):
    location: Optional[Location] = LocationField

    def format(self):
        return "felt"

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return []


@dataclasses.dataclass
class TypeCodeoffset(CairoType):
    location: Optional[Location] = LocationField

    def format(self):
        return "codeoffset"

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return []


@dataclasses.dataclass
class TypePointer(CairoType):
    pointee: CairoType
    location: Optional[Location] = LocationField

    def format(self):
        return f"{self.pointee.format()}*"

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
        assert self.is_fully_resolved, "Type is expected to be fully resolved at this point."
        return self.scope

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return []


@dataclasses.dataclass
class TypeTuple(CairoType):
    """
    Represents a type of a named or unnamed tuple.
    For example, "(felt, felt*)" or "(a : felt, b : felt*)".
    """

    @dataclasses.dataclass
    class Item(AstNode):
        """
        Represents a possibly named type item of a TypeTuple.
        For example: "felt" or "a : felt".
        """

        name: Optional[str]
        typ: CairoType
        location: Optional[Location] = LocationField

        def format(self):
            if self.name is None:
                return self.typ.format()
            return f"{self.name} : {self.typ.format()}"

        def get_children(self) -> Sequence[Optional[AstNode]]:
            return [self.typ]

    members: List["TypeTuple.Item"]
    notes: List[Notes] = dataclasses.field(hash=False, compare=False)
    has_trailing_comma: bool = dataclasses.field(hash=False, compare=False)
    location: Optional[Location] = LocationField

    def __post_init__(self):
        assert len(self.notes) == len(self.members) + 1

    def assert_no_comments(self):
        for note in self.notes:
            note.assert_no_comments()

    def format(self):
        self.assert_no_comments()
        member_formats = [member.format() for member in self.members]
        return f"({', '.join(member_formats)})"

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return self.members

    @property
    def types(self) -> List[CairoType]:
        """
        Returns the unnamed types of the tuple.
        """
        return [x.typ for x in self.members]

    @classmethod
    def unnamed(cls, types: List[CairoType], location: Optional[Location] = None):
        """
        Creates an unnamed tuple type from the given types.
        """
        return cls.from_members(
            members=[TypeTuple.Item(name=None, typ=typ) for typ in types],
            location=location,
        )

    @classmethod
    def from_members(cls, members: List["TypeTuple.Item"], location: Optional[Location]):
        """
        Creates a tuple (with no notes) from the given members.
        """
        return cls(
            members=members,
            notes=[Notes() for _ in range(len(members) + 1)],
            has_trailing_comma=False,
            location=location,
        )

    @property
    def is_named(self) -> bool:
        return all(member.name is not None for member in self.members)


class CastType(Enum):
    # When the compiler creates a cast expression for references.
    FORCED = 0
    # When an explicit cast occurs using 'cast(*, *)'.
    EXPLICIT = auto()
    # When unpacking occurs (e.g., 'let (x : T) = foo()').
    UNPACKING = auto()
    # When a variable is initialized (e.g., 'tempvar x : T = 5').
    ASSIGN = auto()
