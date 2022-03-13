import itertools
from typing import Iterable, Optional, Sequence

from starkware.cairo.lang.compiler.ast.cairo_types import (
    CairoType,
    CastType,
    TypeCodeoffset,
    TypeFelt,
    TypePointer,
    TypeStruct,
    TypeTuple,
)
from starkware.cairo.lang.compiler.ast.expr import ExprDeref, Expression, ExprTuple
from starkware.cairo.lang.compiler.error_handling import Location, LocationError
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.identifier_utils import get_struct_definition
from starkware.python.utils import safe_zip

FELT_STAR = TypePointer(pointee=TypeFelt())


class CairoTypeError(LocationError):
    pass


def check_cast(
    src_type: CairoType,
    dest_type: CairoType,
    identifier_manager: IdentifierManager,
    cast_type: CastType,
    location: Optional[Location],
    expr: Optional[Expression] = None,
) -> bool:
    """
    Returns true if the given expression can be casted from src_type to dest_type
    according to the given 'cast_type'.
    In some cases of cast failure, an exception with more specific details is raised.
    'location' is used as the default error location if expr is not specified.
    """

    if expr is not None and expr.location is not None:
        location = expr.location

    # CastType.ASSIGN checks:

    if src_type == dest_type:
        return True

    # Allow implicit cast from pointers to felt*.
    if isinstance(src_type, TypePointer) and dest_type == FELT_STAR:
        return True

    # Allow implicit cast between named and unnamed tuples.
    if isinstance(src_type, TypeTuple) and isinstance(dest_type, TypeTuple):
        verify_tuple_like_cast(
            src_type=src_type,
            src_members=src_type.members,
            dest_type=dest_type,
            dest_members=dest_type.members,
            identifier_manager=identifier_manager,
            expr=expr,
            location=location,
            cast_type=cast_type,
        )
        return True

    if cast_type is CastType.ASSIGN:
        return False

    # CastType.UNPACKING checks:

    # Allow explicit cast between felts and pointers.
    if isinstance(src_type, (TypeFelt, TypePointer)) and isinstance(
        dest_type, (TypeFelt, TypePointer)
    ):
        return True

    if cast_type is CastType.UNPACKING:
        return False

    # CastType.EXPLICIT checks:

    # Allow explicit cast between felts and labels.
    if isinstance(src_type, (TypeFelt, TypeCodeoffset)) and isinstance(
        dest_type, (TypeFelt, TypeCodeoffset)
    ):
        return True

    if isinstance(src_type, TypeTuple) and isinstance(dest_type, TypeStruct):
        struct_def = get_struct_definition(
            struct_name=dest_type.resolved_scope, identifier_manager=identifier_manager
        )
        dest_members = [
            TypeTuple.Item(name=name, typ=member.cairo_type)
            for name, member in struct_def.members.items()
        ]

        verify_tuple_like_cast(
            src_type=src_type,
            src_members=src_type.members,
            dest_type=dest_type,
            dest_members=dest_members,
            identifier_manager=identifier_manager,
            cast_type=cast_type,
            location=location,
            expr=expr,
        )

        return True

    if cast_type is CastType.EXPLICIT:
        return False

    # CastType.FORCED checks:
    if (
        isinstance(src_type, TypeFelt)
        and isinstance(dest_type, TypeStruct)
        and isinstance(expr, ExprDeref)
    ):
        return True

    assert cast_type is CastType.FORCED, f"Unsupported cast type: {cast_type}."
    return False


def verify_tuple_like_cast(
    src_type: CairoType,
    src_members: Sequence[TypeTuple.Item],
    dest_type: CairoType,
    dest_members: Sequence[TypeTuple.Item],
    identifier_manager: IdentifierManager,
    cast_type: CastType,
    location: Optional[Location],
    expr: Optional[Expression],
):
    n_src_members = len(src_members)
    n_dest_members = len(dest_members)
    if n_src_members != n_dest_members:
        raise CairoTypeError(
            f"""\
Cannot cast an expression of type '{src_type.format()}' to '{dest_type.format()}'.
The former has {n_src_members} members while the latter has {n_dest_members} members.""",
            location=location,
        )

    src_exprs: Iterable[Optional[Expression]] = (
        [arg.expr for arg in expr.members.args]
        if isinstance(expr, ExprTuple)
        else itertools.repeat(None, times=n_src_members)
    )

    for (src_expr, src_member, dest_member) in safe_zip(src_exprs, src_members, dest_members):
        item_location = location
        if src_expr is not None and src_expr.location is not None:
            item_location = src_expr.location

        src_name = src_member.name
        dest_name = dest_member.name
        if src_name is not None and dest_name is not None and src_name != dest_name:
            raise CairoTypeError(
                f"""\
Cannot cast '{src_type.format()}' to '{dest_type.format()}'.
Expected argument name {dest_name}. Found: {src_name}.""",
                location=item_location,
            )

        src_member_type = src_member.typ
        dest_member_type = dest_member.typ
        if not check_cast(
            src_type=src_member_type,
            dest_type=dest_member_type,
            identifier_manager=identifier_manager,
            cast_type=CastType.FORCED if cast_type is CastType.FORCED else CastType.ASSIGN,
            location=item_location,
            expr=src_expr,
        ):
            raise CairoTypeError(
                f"Cannot cast '{src_member_type.format()}' to '{dest_member_type.format()}'.",
                location=item_location,
            )
