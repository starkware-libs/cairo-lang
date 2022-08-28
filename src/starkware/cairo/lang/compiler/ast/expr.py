import dataclasses
import re
from abc import abstractmethod
from dataclasses import field
from typing import List, Optional, Sequence

import marshmallow

from starkware.cairo.lang.compiler.ast.cairo_types import CairoType, CastType
from starkware.cairo.lang.compiler.ast.formatting_utils import (
    INDENTATION,
    LocationField,
    Particle,
    ParticleList,
    SeparatedParticleList,
    SingleParticle,
)
from starkware.cairo.lang.compiler.ast.node import AstNode
from starkware.cairo.lang.compiler.ast.notes import Notes, NotesField
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.instruction import Register
from starkware.python.expression_string import ExpressionString
from starkware.python.utils import indent, safe_zip
from starkware.starkware_utils.marshmallow_dataclass_fields import additional_metadata


class Expression(AstNode):
    location: Optional[Location]

    def format(self):
        res = str(self.to_expr_str())
        # Indent all lines except for the first.
        res = res.replace("\n", "\n" + " " * INDENTATION)
        # Remove trailing spaces.
        res = re.sub(r" +\n", "\n", res)
        return res

    @abstractmethod
    def to_expr_str(self) -> ExpressionString:
        """
        Formats the Expression and returns an ExpressionString. This is useful for automatic
        insertion of parentheses (where required).
        """

    @abstractmethod
    def get_particles(self) -> List[Particle]:
        """
        Returns a list of particles representing the expression, for formatting purposes.
        """


@dataclasses.dataclass
class ExprConst(Expression):
    val: int
    # Indicates the way the absolute value of the expression should be formatted in the code.
    # For example, it may contain the hexadecimal representation.
    format_str: Optional[str] = field(
        default=None,
        hash=False,
        compare=False,
        metadata=additional_metadata(
            marshmallow_field=marshmallow.fields.Field(load_only=True, dump_only=True)
        ),
    )
    location: Optional[Location] = LocationField

    def absolute_val_format(self) -> str:
        return str(abs(self.val)) if self.format_str is None else self.format_str

    def to_expr_str(self):
        abs_format = self.absolute_val_format()
        if self.val >= 0:
            return ExpressionString.highest(abs_format)
        return -ExpressionString.highest(abs_format)

    def get_particles(self) -> List[Particle]:
        abs_format = self.absolute_val_format()
        return [SingleParticle(text=abs_format if self.val >= 0 else f"-{abs_format}")]

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return []


@dataclasses.dataclass
class ExprHint(Expression):
    hint_code: str
    # The number of new lines following the "%{" symbol.
    n_prefix_newlines: int
    location: Optional[Location] = LocationField

    @classmethod
    def from_str(cls, val, location):
        HINT_PATTERN = r"%\{(?P<prefix_whitespace>([ \t]*\n)*)(?P<code>.*?)%\}"
        m = re.match(HINT_PATTERN, val, re.DOTALL)
        assert m is not None
        code = m.group("code").rstrip()
        if code is None:
            code = ""

        # Remove common indentation.
        lines = code.split("\n")
        common_indent = min(
            (len(line) - len(line.lstrip(" ")) for line in lines if line), default=0
        )
        code = "\n".join(line[common_indent:] for line in lines)

        return cls(
            hint_code=code,
            n_prefix_newlines=m.group("prefix_whitespace").count("\n"),
            location=location,
        )

    def to_str(self):
        if self.hint_code == "":
            return "%{\n%}"
        if "\n" not in self.hint_code:
            # One liner.
            return f"%{{ {self.hint_code} %}}"
        code = indent(self.hint_code, INDENTATION)
        return f"%{{\n{code}\n%}}"

    def to_expr_str(self):
        return ExpressionString.highest(f"nondet {self.to_str()}")

    def get_particles(self) -> List[Particle]:
        return [SingleParticle(text=f"nondet {self.to_str()}")]

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return []


@dataclasses.dataclass
class ExprIdentifier(Expression):
    name: str
    location: Optional[Location] = LocationField

    def to_expr_str(self):
        return ExpressionString.highest(self.name)

    def get_particles(self) -> List[Particle]:
        return [SingleParticle(text=self.name)]

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return []


@dataclasses.dataclass
class ExprAssignment(AstNode):
    """
    A code element of the form [ident=]expr. The identifier is optional.
    """

    identifier: Optional[ExprIdentifier]
    expr: Expression
    location: Optional[Location] = LocationField

    def format(self):
        if self.identifier is None:
            return self.expr.format()
        return f"{self.identifier.format()}={self.expr.format()}"

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.identifier, self.expr]


@dataclasses.dataclass
class ArgList(AstNode):
    """
    Represents a list of arguments (e.g., to a function call or a return statement).
    For example: 'a=1, b=2'.
    """

    args: List[ExprAssignment]
    notes: List[Notes]
    has_trailing_comma: bool
    location: Optional[Location] = LocationField

    def __post_init__(self):
        assert len(self.notes) == len(self.args) + 1

    def assert_no_comments(self):
        for note in self.notes:
            note.assert_no_comments()

    def format(self):
        if len(self.args) == 0:
            assert len(self.notes) == 1
            return self.notes[0].format()

        code = ""
        assert len(self.args) + 1 == len(self.notes)
        for notes, arg in safe_zip(self.notes[:-1], self.args):
            if code != "":
                code += ","
                if notes.empty:
                    code += " "
            code += f"{notes.format()}{arg.format()}"

        # Add trailing comma at the end if necessary.
        if self.has_trailing_comma:
            code += ","
        code += self.notes[-1].format()
        return code

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return self.args


@dataclasses.dataclass
class ExprReg(Expression):
    reg: Register
    location: Optional[Location] = LocationField

    def to_expr_str(self):
        return ExpressionString.highest(self.reg.name.lower())

    def get_particles(self) -> List[Particle]:
        return [SingleParticle(text=self.reg.name.lower())]

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return []


@dataclasses.dataclass
class ExprOperator(Expression):
    a: Expression
    op: str
    b: Expression
    notes: Notes = NotesField
    location: Optional[Location] = LocationField

    def to_expr_str(self):
        self.notes.assert_no_comments()
        a = self.a.to_expr_str()
        b = self.b.to_expr_str()
        if not self.notes.empty:
            b = b.prepend("\n")
        if self.op == "+":
            return a + b
        elif self.op == "-":
            return a - b
        elif self.op == "*":
            return a * b
        elif self.op == "/":
            return a / b
        else:
            raise NotImplementedError(f"Unexpected operator '{self.op}'")

    def get_particles(self) -> List[Particle]:
        self.notes.assert_no_comments()

        a_particles = self.a.get_particles()
        a_particles[-1].add_suffix(f" {self.op} ")
        return a_particles + self.b.get_particles()

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.a, self.b]


@dataclasses.dataclass
class ExprPow(Expression):
    a: Expression
    b: Expression
    notes: Notes = NotesField
    location: Optional[Location] = LocationField

    def to_expr_str(self):
        self.notes.assert_no_comments()
        a = self.a.to_expr_str()
        b = self.b.to_expr_str()
        if not self.notes.empty:
            b = b.prepend("\n")
        return a.double_star_pow(b)

    def get_particles(self) -> List[Particle]:
        self.notes.assert_no_comments()

        a_particles = self.a.get_particles()
        a_particles[-1].add_suffix(f" ** ")
        return a_particles + self.b.get_particles()

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.a, self.b]


@dataclasses.dataclass
class ExprAddressOf(Expression):
    """
    Represents an expression of the form "&expr".
    """

    expr: Expression
    location: Optional[Location] = LocationField

    def to_expr_str(self):
        return self.expr.to_expr_str().address_of()

    def get_particles(self) -> List[Particle]:
        particles = self.expr.get_particles()
        particles[0].add_prefix("&")
        return particles

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.expr]


@dataclasses.dataclass
class ExprNeg(Expression):
    val: Expression
    location: Optional[Location] = LocationField

    def to_expr_str(self):
        return -self.val.to_expr_str()

    def get_particles(self) -> List[Particle]:
        particles = self.val.get_particles()
        particles[0].add_prefix("-")
        return particles

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.val]


@dataclasses.dataclass
class ExprParentheses(Expression):
    val: Expression
    notes: Notes = NotesField
    location: Optional[Location] = LocationField

    def to_expr_str(self):
        return ExpressionString.highest(f"({self.notes.format()}{str(self.val.to_expr_str())})")

    def get_particles(self) -> List[Particle]:
        self.notes.assert_no_comments()
        return [
            SeparatedParticleList(
                elements=self.val.get_particles(),
                start="(",
                end=")",
                separator="",
            )
        ]

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.val]


@dataclasses.dataclass
class ExprDeref(Expression):
    """
    Represents an expression of the form "[addr]".
    """

    addr: Expression
    notes: Notes = NotesField
    location: Optional[Location] = LocationField

    def to_expr_str(self):
        self.notes.assert_no_comments()
        notes = "" if self.notes.empty else "\n"
        return ExpressionString.highest(f"[{notes}{str(self.addr.to_expr_str())}]")

    def get_particles(self) -> List[Particle]:
        self.notes.assert_no_comments()
        return [
            SeparatedParticleList(
                elements=self.addr.get_particles(), start="[", end="]", separator=""
            )
        ]

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.addr]


@dataclasses.dataclass
class ExprSubscript(Expression):
    """
    Represents an expression of the form "expr[offset]".
    """

    expr: Expression
    offset: Expression
    notes: Notes = NotesField
    location: Optional[Location] = LocationField

    def to_expr_str(self):
        self.notes.assert_no_comments()
        notes = "" if self.notes.empty else "\n"
        # If expr is not an atom, add parentheses.
        return ExpressionString.highest(
            f"{self.expr.to_expr_str():HIGHEST}[{notes}{str(self.offset.to_expr_str())}]"
        )

    def get_particles(self) -> List[Particle]:
        self.notes.assert_no_comments()

        expr_particles = self.expr.get_particles()
        expr_particles[-1].add_suffix("[")
        offset_particle = SeparatedParticleList(
            elements=self.offset.get_particles(), start="", end="]", separator=""
        )

        return expr_particles + [offset_particle]

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.expr, self.offset]


@dataclasses.dataclass
class ExprDot(Expression):
    """
    Represents an expression of the form "expr.member".
    """

    expr: Expression
    member: ExprIdentifier
    location: Optional[Location] = LocationField

    def to_expr_str(self):
        # If expr is not an atom, add parentheses.
        return ExpressionString.highest(
            f"{self.expr.to_expr_str():HIGHEST}.{str(self.member.to_expr_str())}"
        )

    def get_particles(self) -> List[Particle]:
        expr_particles = self.expr.get_particles()
        member_str = "".join(str(particle) for particle in self.member.get_particles())
        expr_particles[-1].add_suffix(f".{member_str}")

        return expr_particles

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.expr, self.member]


@dataclasses.dataclass
class ExprCast(Expression):
    """
    Represents a cast expression of the form "cast(expr, T)" (which transforms expr to type T).
    """

    expr: Expression
    dest_type: CairoType
    # Cast expressions resulting from the Cairo code always have cast_type=CastType.EXPLICIT.
    # 'cast_type' is only used when an ExprCast instance is created during compilation.
    cast_type: CastType = CastType.EXPLICIT
    notes: Notes = NotesField
    location: Optional[Location] = LocationField

    def to_expr_str(self):
        self.notes.assert_no_comments()
        notes = "" if self.notes.empty else "\n"
        return ExpressionString.highest(
            f"cast({notes}{str(self.expr.to_expr_str())}, {self.dest_type.format()})"
        )

    def get_particles(self) -> List[Particle]:
        expr_particles = self.expr.get_particles()
        type_particle = self.dest_type.to_particle()
        return [
            SeparatedParticleList(
                elements=[ParticleList(elements=expr_particles), type_particle],
                start="cast(",
                end=")",
            )
        ]

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.expr, self.dest_type]


@dataclasses.dataclass
class ExprTuple(Expression):
    members: ArgList
    location: Optional[Location] = LocationField

    def to_expr_str(self):
        code = self.members.format()
        return ExpressionString.highest(f"({code})")

    def get_particles(self) -> List[Particle]:
        return [
            SeparatedParticleList(
                elements=[x.format() for x in self.members.args], start="(", end=")"
            )
        ]

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.members]


@dataclasses.dataclass(frozen=True)
class ExprFutureLabel(Expression):
    """
    Represents a future label whose current pc is not known yet.
    """

    identifier: ExprIdentifier
    # True if the label should be considered of type codeoffset (otherwise it is considered felt).
    is_typed: bool
    location: Optional[Location] = LocationField

    def to_expr_str(self):
        return self.identifier.to_expr_str()

    def get_particles(self) -> List[Particle]:
        return self.identifier.get_particles()

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.identifier]


@dataclasses.dataclass
class ExprNewOperator(Expression):
    """
    Represents an expression of the form "new expr".
    The typical use case is "new MyStruct(1, 2, z=3)", but "new (1 + 2)" is also valid.
    """

    expr: Expression
    # True if the type of the expression should be a pointer to the type of 'expr'.
    # False, if the type should be considered as felt.
    is_typed: bool
    location: Optional[Location] = LocationField

    def to_expr_str(self):
        return self.expr.to_expr_str().operator_new()

    def get_particles(self) -> List[Particle]:
        particles = self.expr.get_particles()
        particles[0].add_prefix("new ")
        return particles

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.expr]
