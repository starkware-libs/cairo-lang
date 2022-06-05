import re

import pytest

from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt
from starkware.cairo.lang.compiler.identifier_definition import (
    ConstDefinition,
    DefinitionError,
    MemberDefinition,
    StructDefinition,
)
from starkware.cairo.lang.compiler.identifier_manager import (
    IdentifierManager,
    MissingIdentifierError,
)
from starkware.cairo.lang.compiler.identifier_utils import get_struct_definition
from starkware.cairo.lang.compiler.scoped_name import ScopedName

scope = ScopedName.from_string


def test_get_struct_definition():
    identifier_dict = {
        scope("T"): StructDefinition(
            full_name=scope("T"),
            members={
                "a": MemberDefinition(offset=0, cairo_type=TypeFelt()),
                "b": MemberDefinition(offset=1, cairo_type=TypeFelt()),
            },
            size=2,
        ),
        scope("MyConst"): ConstDefinition(value=5),
    }

    manager = IdentifierManager.from_dict(identifier_dict)

    struct_def = get_struct_definition(ScopedName.from_string("T"), manager)

    # Convert to a list, to check the order of the elements in the dict.
    assert list(struct_def.members.items()) == [
        ("a", MemberDefinition(offset=0, cairo_type=TypeFelt())),
        ("b", MemberDefinition(offset=1, cairo_type=TypeFelt())),
    ]

    assert struct_def.size == 2

    with pytest.raises(DefinitionError, match="Expected 'MyConst' to be struct. Found: 'const'."):
        get_struct_definition(scope("MyConst"), manager)

    with pytest.raises(MissingIdentifierError, match=re.escape("Unknown identifier 'abc'.")):
        get_struct_definition(scope("abc"), manager)
