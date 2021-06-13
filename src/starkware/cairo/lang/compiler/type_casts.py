import itertools
from typing import Iterable, Optional, cast

from starkware.cairo.lang.compiler.ast.cairo_types import (
    CairoType, CastType, TypeFelt, TypePointer, TypeStruct, TypeTuple)
from starkware.cairo.lang.compiler.ast.expr import Expression, ExprTuple
from starkware.cairo.lang.compiler.error_handling import LocationError
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.identifier_utils import get_struct_definition

FELT_STAR = TypePointer(pointee=TypeFelt())


class CairoTypeError(LocationError):
    pass


def check_cast(
        src_type: CairoType, dest_type: CairoType, identifier_manager: IdentifierManager,
        expr: Optional[Expression] = None, cast_type: CastType = CastType.EXPLICIT) -> bool:
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
    assert expr is not None, f'CastType.EXPLICIT requires expr != None.'

    if isinstance(src_type, TypeTuple) and isinstance(dest_type, TypeStruct):
        struct_def = get_struct_definition(
            struct_name=dest_type.resolved_scope, identifier_manager=identifier_manager)

        n_src_members = len(src_type.members)
        n_dest_members = len(struct_def.members)
        if n_src_members != n_dest_members:
            raise CairoTypeError(
                f"""\
Cannot cast an expression of type '{src_type.format()}' to '{dest_type.format()}'.
The former has {n_src_members} members while the latter has {n_dest_members} members.""",
                location=expr.location)

        src_exprs = cast(
            Iterable, expr.members.args if isinstance(expr, ExprTuple) else
            itertools.repeat(expr))

        for (src_expr, src_member_type, dest_member) in zip(
                src_exprs, src_type.members, struct_def.members.values()):
            dest_member_type = dest_member.cairo_type
            if not check_cast(
                    src_type=src_member_type, dest_type=dest_member_type,
                    identifier_manager=identifier_manager, expr=src_expr,
                    cast_type=CastType.ASSIGN):

                raise CairoTypeError(
                    f"Cannot cast '{src_member_type.format()}' to '{dest_member_type.format()}'.",
                    location=src_expr.location)

        return True

    assert cast_type is CastType.EXPLICIT, f'Unsupported cast type: {cast_type}.'
    return False
