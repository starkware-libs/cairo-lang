from starkware.cairo.lang.compiler.constants import SIZE_CONSTANT
from starkware.cairo.lang.compiler.identifier_definition import (
    ConstDefinition,
    DefinitionError,
    IdentifierDefinition,
    ReferenceDefinition,
    StructDefinition,
)
from starkware.cairo.lang.compiler.identifier_manager import (
    IdentifierError,
    IdentifierManager,
    IdentifierSearchResult,
)
from starkware.cairo.lang.compiler.offset_reference import OffsetReferenceDefinition


def resolve_search_result(
    search_result: IdentifierSearchResult, identifiers: IdentifierManager
) -> IdentifierDefinition:
    """
    Returns a fully parsed identifier definition for the given identifier search result.
    If search_result contains a reference with non_parsed data, returns an instance of
    OffsetReferenceDefinition.
    """
    identifier_definition = search_result.identifier_definition

    if len(search_result.non_parsed) == 0:
        return identifier_definition

    if isinstance(identifier_definition, StructDefinition):
        if search_result.non_parsed == SIZE_CONSTANT:
            return ConstDefinition(value=identifier_definition.size)

        member_def = identifier_definition.members.get(search_result.non_parsed.path[0])
        struct_name = identifier_definition.full_name
        if member_def is None:
            raise DefinitionError(
                f"'{search_result.non_parsed}' is not a member of '{struct_name}'."
            )

        if len(search_result.non_parsed) > 1:
            raise IdentifierError(
                f"Unexpected '.' after '{struct_name + search_result.non_parsed.path[0]}' which is "
                f"{member_def.TYPE}."
            )

        identifier_definition = member_def
    elif isinstance(identifier_definition, ReferenceDefinition):
        identifier_definition = OffsetReferenceDefinition(
            parent=identifier_definition, member_path=search_result.non_parsed
        )
    else:
        search_result.assert_fully_parsed()

    return identifier_definition
