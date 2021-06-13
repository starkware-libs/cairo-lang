import pytest

from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt
from starkware.cairo.lang.compiler.identifier_definition import MemberDefinition, StructDefinition
from starkware.cairo.lang.compiler.identifier_manager import (
    IdentifierError, IdentifierManager, IdentifierSearchResult)
from starkware.cairo.lang.compiler.resolve_search_result import resolve_search_result
from starkware.cairo.lang.compiler.scoped_name import ScopedName

scope = ScopedName.from_string


def test_resolve_search_result():
    struct_def = StructDefinition(
        full_name=scope('T'),
        members={
            'a': MemberDefinition(offset=0, cairo_type=TypeFelt()),

            'b': MemberDefinition(offset=1, cairo_type=TypeFelt()),
        },
        size=2,
    )

    identifier_dict = {
        struct_def.full_name: struct_def,
    }

    identifier = IdentifierManager.from_dict(identifier_dict)

    with pytest.raises(IdentifierError, match="Unexpected '.' after 'T.a' which is member"):
        resolve_search_result(
            search_result=IdentifierSearchResult(
                identifier_definition=struct_def,
                canonical_name=struct_def.full_name,
                non_parsed=scope('a.z')),
            identifiers=identifier)
