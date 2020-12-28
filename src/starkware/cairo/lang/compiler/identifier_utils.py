from typing import Dict

from starkware.cairo.lang.compiler.identifier_definition import (
    IdentifierDefinition, MemberDefinition, OffsetReferenceDefinition, ReferenceDefinition)
from starkware.cairo.lang.compiler.identifier_manager import (
    IdentifierManager, IdentifierSearchResult)
from starkware.cairo.lang.compiler.scoped_name import ScopedName


def get_struct_members(
        struct_name: ScopedName,
        identifier_manager: IdentifierManager) -> Dict[str, MemberDefinition]:
    """
    Returns the member definitions of a struct sorted by offset.
    """

    scope_items = identifier_manager.get_scope(struct_name).identifiers
    members = (
        (name, indentifier_def)
        for (name, indentifier_def) in scope_items.items()
        if isinstance(indentifier_def, MemberDefinition))

    return {
        name: indentifier_def
        for name, indentifier_def in sorted(members, key=lambda key_value: key_value[1].offset)
    }


def resolve_search_result(
        search_result: IdentifierSearchResult,
        identifiers: IdentifierManager) -> IdentifierDefinition:
    """
    Returns a fully parsed identifier definition for the given identifier search result.
    If search_result contains a reference with non_parsed data, returns an instance of
    OffsetReferenceDefinition.
    """
    identifier_definition = search_result.identifier_definition
    if isinstance(identifier_definition, ReferenceDefinition) and \
            len(search_result.non_parsed) > 0:
        identifier_definition = OffsetReferenceDefinition(
            parent=identifier_definition,
            identifier_values=identifiers.as_dict(),
            member_path=search_result.non_parsed)
    else:
        search_result.assert_fully_parsed()

    return identifier_definition
