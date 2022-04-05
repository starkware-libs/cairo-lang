import dataclasses
from abc import abstractmethod
from typing import Optional, Sequence

from starkware.cairo.lang.compiler.ast.expr import ArgList, Expression, ExprIdentifier
from starkware.cairo.lang.compiler.ast.formatting_utils import (
    INDENTATION,
    LocationField,
    ParticleFormattingConfig,
    ParticleList,
    SeparatedParticleList,
    particles_in_lines,
)
from starkware.cairo.lang.compiler.ast.instructions import CallInstruction
from starkware.cairo.lang.compiler.ast.node import AstNode
from starkware.cairo.lang.compiler.error_handling import Location


class Rvalue(AstNode):
    """
    An expression that can appear on the right-hand side of a reference assignment.

    For example, in the code:
      let a = foo(1, 2, 3)
    the expression "foo(1, 2, 3)" is an rvalue.
    """

    @property
    @abstractmethod
    def location(self):
        """
        The location of the Rvalue.
        """

    @abstractmethod
    def get_particles(self):
        """
        Returns a list of particles that can be used to convert the Rvalue to a multiline string.
        """

    @abstractmethod
    def format(self):
        """
        Converts the Rvalue to a string.
        """


@dataclasses.dataclass
class RvalueExpr(Rvalue):
    """
    Represents an rvalue which is a simple expression. E.g., fp + 17.
    """

    expr: Expression

    @property
    def location(self):
        return self.expr.location

    def get_particles(self):
        return [self.expr.format()]

    def format(self):
        return self.expr.format()

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.expr]


class RvalueCall(Rvalue):
    """
    Represents one of the following:
      foo(a, b)
      call foo
    """


@dataclasses.dataclass
class RvalueCallInst(RvalueCall):
    """
    Represents a call instruction rvalue.

    call_inst is CallInstruction that calls the function.
    """

    call_inst: CallInstruction

    @property
    def location(self):
        return self.call_inst.location

    def get_particles(self):
        return [self.call_inst.format()]

    def format(self):
        return self.call_inst.format()

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.call_inst]


@dataclasses.dataclass
class RvalueFuncCall(RvalueCall):
    """
    Represents an rvalue of the form:
      func_ident([ident=]expr, ...).
    """

    func_ident: ExprIdentifier
    arguments: ArgList
    implicit_arguments: Optional[ArgList]
    location: Optional[Location] = LocationField

    def assert_no_comments(self):
        self.arguments.assert_no_comments()
        if self.implicit_arguments is not None:
            self.implicit_arguments.assert_no_comments()

    def get_particles(self):
        self.assert_no_comments()

        particles = [self.func_ident.format()]

        if self.implicit_arguments is not None:
            particles[-1] += "{"
            particles.append(
                SeparatedParticleList(
                    elements=[x.format() for x in self.implicit_arguments.args], end="}("
                )
            )
        else:
            particles[-1] += "("

        particles.append(
            SeparatedParticleList(elements=[x.format() for x in self.arguments.args], end=")")
        )
        return particles

    def format(self, allowed_line_length):
        self.assert_no_comments()
        return particles_in_lines(
            particles=ParticleList(elements=self.get_particles()),
            config=ParticleFormattingConfig(
                allowed_line_length=allowed_line_length, line_indent=INDENTATION, one_per_line=True
            ),
        )

    def format_for_expr(self) -> str:
        """
        Formats the rvalue without automatic line breaking.
        Should be used when the rvalue is part of an expression (where the line breaking mechanism
        is not supported yet).
        """
        res = self.func_ident.format()

        if self.implicit_arguments is not None:
            res += "{" + self.implicit_arguments.format() + "}"

        res += "(" + self.arguments.format() + ")"
        return res

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.func_ident, self.arguments, self.implicit_arguments]
