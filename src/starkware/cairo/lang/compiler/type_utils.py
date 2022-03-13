from typing import Optional

from starkware.cairo.lang.compiler.ast.cairo_types import CairoType, TypeFelt, TypeStruct, TypeTuple
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.identifier_utils import get_struct_definition


def check_felts_only_type(
    cairo_type: CairoType, identifier_manager: IdentifierManager
) -> Optional[int]:
    """
    A felts-only type defined to be either felt or a struct whose members are all felts-only types.
    Returns the size of the given type if it is felts-only and None otherwise.
    """

    if isinstance(cairo_type, TypeFelt):
        return 1
    elif isinstance(cairo_type, TypeStruct):
        struct_definition = get_struct_definition(
            cairo_type.resolved_scope, identifier_manager=identifier_manager
        )

        size = 0
        for member_def in struct_definition.members.values():
            res = check_felts_only_type(
                member_def.cairo_type, identifier_manager=identifier_manager
            )
            if res is None:
                return None
            size += res
        return size
    elif isinstance(cairo_type, TypeTuple):
        size = 0
        for item_type in cairo_type.types:
            res = check_felts_only_type(item_type, identifier_manager=identifier_manager)
            if res is None:
                return None
            size += res
        return size
    else:
        return None
