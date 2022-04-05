from dataclasses import dataclass
from typing import Sequence, Optional

from starkware.cairo.lang.compiler.ast.expr import ExprIdentifier, Expression
from starkware.cairo.lang.compiler.ast.node import AstNode
from starkware.python.expression_string import ExpressionString


@dataclass
class ForGeneratorRange(Expression):
    start: Optional[Expression]
    end: Expression
    step: Optional[Expression]

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return self.get_arguments()

    def get_arguments(self) -> Sequence[Expression]:
        args = []

        if self.start is not None:
            args.append(self.start)

        args.append(self.end)

        if self.step is not None:
            args.append(self.step)

        return args

    def to_expr_str(self) -> ExpressionString:
        # TODO: Better line breaking for arguments
        args = ", ".join([child.format() for child in self.get_arguments()])
        return ExpressionString.highest(f"range({args})")


@dataclass
class ForClauseIn(AstNode):
    identifier: ExprIdentifier
    generator: ForGeneratorRange

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.identifier, self.generator]

    def get_particles(self):
        return [f"{self.identifier.format()} in ", self.generator.format()]
