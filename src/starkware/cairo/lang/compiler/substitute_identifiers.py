from typing import Callable

from starkware.cairo.lang.compiler.ast.expr import (
    ExprConst, Expression, ExprFutureLabel, ExprIdentifier)
from starkware.cairo.lang.compiler.expression_transformer import ExpressionTransformer


class SubstituteIdentifiers(ExpressionTransformer):
    def __init__(self, get_identifier_callback: Callable):
        super().__init__()
        self.get_identifier_callback = get_identifier_callback

    def visit_ExprIdentifier(self, expr: ExprIdentifier) -> Expression:
        val = self.get_identifier_callback(expr)
        if isinstance(val, int):
            return ExprConst(val, location=expr.location)
        return val

    def visit_ExprFutureLabel(self, expr: ExprFutureLabel):
        return self.visit(expr.identifier)


def substitute_identifiers(expr: Expression, get_identifier_callback: Callable) -> Expression:
    """
    Replaces identifiers by other expressions according to the given callback.
    """
    return SubstituteIdentifiers(get_identifier_callback).visit(expr)
