from typing import Callable, Optional, Union

from starkware.cairo.lang.compiler.ast.cairo_types import CairoType
from starkware.cairo.lang.compiler.ast.expr import (
    ExprCast, ExprConst, Expression, ExprFutureLabel, ExprIdentifier)
from starkware.cairo.lang.compiler.expression_transformer import ExpressionTransformer

GetIdentifierCallback = Callable[[ExprIdentifier], Union[int, Expression]]
ResolveTypeCallback = Optional[Callable[[CairoType], CairoType]]


class SubstituteIdentifiers(ExpressionTransformer):
    def __init__(
            self, get_identifier_callback: GetIdentifierCallback,
            resolve_type_callback: ResolveTypeCallback = None):
        super().__init__()
        self.get_identifier_callback = get_identifier_callback
        self.resolve_type_callback = (
            resolve_type_callback
            if resolve_type_callback is not None
            else (lambda cairo_type: cairo_type))

    def visit_ExprIdentifier(self, expr: ExprIdentifier) -> Expression:
        val = self.get_identifier_callback(expr)
        if isinstance(val, int):
            return ExprConst(val, location=expr.location)
        return val

    def visit_ExprCast(self, expr: ExprCast):
        return ExprCast(
            expr=self.visit(expr.expr),
            dest_type=self.resolve_type_callback(expr.dest_type),
            cast_type=expr.cast_type,
            notes=expr.notes,
            location=expr.location)

    def visit_ExprFutureLabel(self, expr: ExprFutureLabel):
        return self.visit(expr.identifier)


def substitute_identifiers(
        expr: Expression, get_identifier_callback: GetIdentifierCallback,
        resolve_type_callback: ResolveTypeCallback = None) -> Expression:
    """
    Replaces identifiers by other expressions according to the given callback.
    """
    return SubstituteIdentifiers(
        get_identifier_callback=get_identifier_callback,
        resolve_type_callback=resolve_type_callback,
    ).visit(expr)
