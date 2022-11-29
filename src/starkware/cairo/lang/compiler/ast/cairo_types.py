import dataclasses
from abc import abstractmethod
from contextlib import contextmanager
from contextvars import ContextVar
from enum import Enum, auto
from typing import List, Optional, Sequence

from starkware.cairo.lang.compiler.ast.formatting_utils import LocationField
from starkware.cairo.lang.compiler.ast.node import AstNode
from starkware.cairo.lang.compiler.ast.notes import Notes
from starkware.cairo.lang.compiler.ast.particle import (
    Particle,
    SeparatedParticleList,
    SingleParticle,
)
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.scoped_name import ScopedName

add_backward_compatibility_space_ctx_var: ContextVar[int] = ContextVar(
    "add_backward_compatibility_space", default=False
)


@contextmanager
def add_backward_compatibility_space(value: bool):
    """
    Adds space before the colon when formatting named tuple types.
    This should be used for backward compatibility in the contract hash computation in versions
    before 0.10.0.
    For example, use "(a : felt)" instead of "(a: felt)".
    """
    token = add_backward_compatibility_space_ctx_var.set(value)
    try:
        yield
    finally:
        add_backward_compatibility_space_ctx_var.reset(token)


class CairoType(AstNode):
    location: Optional[Location]

    @abstractmethod
    def to_particle(self) -> Particle:
        """
        Returns a representation of the type as a Particle.
        """

    def format(self) -> str:
        """
        Returns a representation of the type as a string.
        """
        return str(self.to_particle())

    def get_pointer_type(self) -> "CairoType":
        """
        Returns a type of a pointer to the current type.
        """
        return TypePointer(pointee=self, location=self.location)


@dataclasses.dataclass
class TypeFelt(CairoType):
    location: Optional[Location] = LocationField

    def to_particle(self) -> Particle:
        return SingleParticle(text="felt")

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return []


@dataclasses.dataclass
class TypeCodeoffset(CairoType):
    location: Optional[Location] = LocationField

    def to_particle(self) -> Particle:
        return SingleParticle(text="codeoffset")

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return []


@dataclasses.dataclass
class TypePointer(CairoType):
    pointee: CairoType
    location: Optional[Location] = LocationField

    def to_particle(self) -> Particle:
        return SingleParticle(text=f"{self.pointee.format()}*")

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.pointee]


@dataclasses.dataclass
class TypeIdentifier(CairoType):
    """
    Represents a name of an unresolved type.
    This type can be resolved to TypeStruct or TypeDefinition.
    """

    name: ScopedName
    location: Optional[Location] = LocationField

    def to_particle(self) -> Particle:
        return SingleParticle(text=str(self.name))

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return []


@dataclasses.dataclass
class TypeStruct(CairoType):
    scope: ScopedName
    location: Optional[Location] = LocationField

    def to_particle(self) -> Particle:
        return SingleParticle(text=str(self.scope))

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return []


@dataclasses.dataclass
class TypeFunction(CairoType):
    """
    Represents a type of a function.
    """

    scope: ScopedName
    location: Optional[Location] = LocationField

    def to_particle(self) -> Particle:
        return SingleParticle(text=str(self.scope))

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return []


@dataclasses.dataclass
class TypeTuple(CairoType):
    """
    Represents a type of a named or unnamed tuple.
    For example, "(felt, felt*)" or "(a: felt, b: felt*)".
    """

    @dataclasses.dataclass
    class Item(AstNode):
        """
        Represents a possibly named type item of a TypeTuple.
        For example: "felt" or "a: felt".
        """

        name: Optional[str]
        typ: CairoType
        location: Optional[Location] = LocationField

        def to_particle(self) -> Particle:
            particle = self.typ.to_particle()
            if self.name is not None:
                backward_compatibility_space = (
                    " " if add_backward_compatibility_space_ctx_var.get() else ""
                )
                particle.add_prefix(f"{self.name}{backward_compatibility_space}: ")
            return particle

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

    def to_particle(self) -> Particle:
        self.assert_no_comments()
        has_trailing_comma = len(self.members) == 1 and self.members[0].name is None
        return SeparatedParticleList(
            elements=[member.to_particle() for member in self.members],
            start="(",
            end=")",
            trailing_separator=has_trailing_comma,
        )

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
    # When unpacking occurs (e.g., 'let (x: T) = foo();').
    UNPACKING = auto()
    # When a variable is initialized (e.g., 'tempvar x: T = 5;').
    ASSIGN = auto()
