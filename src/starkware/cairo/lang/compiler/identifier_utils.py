from typing import Dict, Tuple, Type

from starkware.cairo.lang.compiler.ast.cairo_types import TypeStruct
from starkware.cairo.lang.compiler.identifier_definition import (
    DefinitionError,
    IdentifierDefinition,
    StructDefinition,
    TypeDefinition,
)
from starkware.cairo.lang.compiler.identifier_manager import (
    IdentifierManager,
    MissingIdentifierError,
)
from starkware.cairo.lang.compiler.scoped_name import ScopedName


def get_identifier_definition(
    name: ScopedName,
    identifier_manager: IdentifierManager,
    supported_types: Tuple[Type[IdentifierDefinition], ...],
    resolve_type_definitions: bool = False,
) -> IdentifierDefinition:
    """
    Returns the identifier definition given its full name (no alias resolution).

    If `resolve_type_definitions` is set and the identifier is a type definition that
    points to a struct, the corresponding struct definition is returned.
    """

    identifier_definition = identifier_manager.get_by_full_name(name)
    if identifier_definition is None:
        raise MissingIdentifierError(name)

    if resolve_type_definitions and isinstance(identifier_definition, TypeDefinition):
        cairo_type = identifier_definition.cairo_type
        if isinstance(cairo_type, TypeStruct):
            identifier_definition = get_struct_definition(
                struct_name=cairo_type.scope, identifier_manager=identifier_manager
            )

    if not isinstance(identifier_definition, supported_types):
        possible_types = " or ".join(
            supported_type.TYPE for supported_type in supported_types  # type: ignore
        )
        raise DefinitionError(
            f"""\
Expected '{name}' to be {possible_types}. Found: '{identifier_definition.TYPE}'."""
        )

    return identifier_definition


def get_struct_definition(
    struct_name: ScopedName, identifier_manager: IdentifierManager
) -> StructDefinition:
    """
    Returns the struct definition of a struct given its full name (no alias resolution).
    If `struct_name` corresponds to a type definition that point to a struct, the corresponding
    struct definition is returned.
    """
    res = get_identifier_definition(
        name=struct_name,
        identifier_manager=identifier_manager,
        supported_types=(StructDefinition,),
        resolve_type_definitions=True,
    )

    assert isinstance(res, StructDefinition)
    return res


def get_type_definition(name: ScopedName, identifier_manager: IdentifierManager) -> TypeDefinition:
    """
    Returns a type definition given its full name (no alias resolution).
    """
    res = get_identifier_definition(
        name=name, identifier_manager=identifier_manager, supported_types=(TypeDefinition,)
    )
    assert isinstance(res, TypeDefinition)
    return res


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
