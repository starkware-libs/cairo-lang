from typing import Dict

from starkware.cairo.lang.compiler.identifier_definition import DefinitionError, StructDefinition
from starkware.cairo.lang.compiler.identifier_manager import (
    IdentifierManager,
    MissingIdentifierError,
)
from starkware.cairo.lang.compiler.scoped_name import ScopedName


def get_struct_definition(
    struct_name: ScopedName, identifier_manager: IdentifierManager
) -> StructDefinition:
    """
    Returns the struct definition of a struct given its full name (no alias resolution).
    """

    struct_def = identifier_manager.get_by_full_name(struct_name)
    if struct_def is None:
        raise MissingIdentifierError(struct_name)

    if not isinstance(struct_def, StructDefinition):
        raise DefinitionError(
            f"""\
Expected '{struct_name}' to be a {StructDefinition.TYPE}. Found: '{struct_def.TYPE}'."""
        )

    return struct_def


def get_struct_member_offsets(
    struct_name: ScopedName, identifier_manager: IdentifierManager
) -> Dict[str, int]:
    """
    Returns a dict that maps a struct member name to its offset in the struct.
    """

    struct_def = get_struct_definition(
        struct_name=struct_name, identifier_manager=identifier_manager
    )

    return {name: member_def.offset for name, member_def in struct_def.members.items()}
