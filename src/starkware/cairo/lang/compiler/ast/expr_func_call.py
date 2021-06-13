import dataclasses
from typing import Optional, Sequence

from starkware.cairo.lang.compiler.ast.expr import Expression
from starkware.cairo.lang.compiler.ast.formatting_utils import LocationField
from starkware.cairo.lang.compiler.ast.node import AstNode
from starkware.cairo.lang.compiler.ast.rvalue import RvalueFuncCall
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.python.expression_string import ExpressionString


@dataclasses.dataclass
class ExprFuncCall(Expression):
    """
    Represents an expression of the form "<func_name>(<arguments>)". For example, "foo(1, 2, z=3)".
    """

    rvalue: RvalueFuncCall
    location: Optional[Location] = LocationField

    def to_expr_str(self):
        return ExpressionString.highest(self.rvalue.format_for_expr())

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.rvalue]
