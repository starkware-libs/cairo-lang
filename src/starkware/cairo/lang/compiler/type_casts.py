from typing import Optional

from starkware.cairo.lang.compiler.ast.cairo_types import (
    CairoType, CastType, TypeFelt, TypePointer, TypeStruct)
from starkware.cairo.lang.compiler.ast.expr import ExprDeref, Expression
from starkware.cairo.lang.compiler.error_handling import LocationError

FELT_STAR = TypePointer(pointee=TypeFelt())


class CairoTypeError(LocationError):
    pass


def check_cast(
        src_type: CairoType, dest_type: CairoType, expr: Optional[Expression] = None,
        cast_type: CastType = CastType.EXPLICIT) -> bool:
    """
    Returns true if the given expression can be casted from src_type to dest_type
    according to the given 'cast_type'.
    In some cases of cast failure, an exception with more specific details is raised.

    'expr' must be specified (not None) when CastType.EXPLICIT is used.
    """

    # CastType.ASSIGN checks:

    if src_type == dest_type:
        return True

    # Allow implicit cast from pointers to felt*.
    if isinstance(src_type, TypePointer) and dest_type == FELT_STAR:
        return True

    if cast_type is CastType.ASSIGN:
        return False

    # CastType.UNPACKING checks:

    # Allow explicit cast between felts and pointers.
    if isinstance(src_type, (TypeFelt, TypePointer)) and \
            isinstance(dest_type, (TypeFelt, TypePointer)):
        return True

    if cast_type is CastType.UNPACKING:
        return False

    # CastType.EXPLICIT checks:

    # Allow casting to T if the expression is a dereference expression (that is, of the form [...]).
    if isinstance(dest_type, TypeStruct):
        assert expr is not None, 'expr must be specified with CastType.EXPLICIT.'
        if not isinstance(expr, ExprDeref):
            raise CairoTypeError(
                f"Cannot cast to '{dest_type.format()}' since the expression has no address.",
                location=expr.location)
        return True

    assert cast_type is CastType.EXPLICIT, f'Unsupported cast type: {cast_type}.'
    return False
