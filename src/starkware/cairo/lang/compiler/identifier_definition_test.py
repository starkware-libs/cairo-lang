from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt
from starkware.cairo.lang.compiler.identifier_definition import (
    IdentifierDefinitionSchema, MemberDefinition, StructDefinition)
from starkware.cairo.lang.compiler.scoped_name import ScopedName

scope = ScopedName.from_string


def test_struct_sorting():
    orig = StructDefinition(
        full_name=ScopedName.from_string('T'),
        members={
            'b': MemberDefinition(offset=1, cairo_type=TypeFelt()),
            'a': MemberDefinition(offset=0, cairo_type=TypeFelt()),
        },
        size=2
    )
    members = orig.members

    assert list(members.items()) != sorted(
        members.items(), key=lambda key_value: key_value[1].offset)

    schema = IdentifierDefinitionSchema()
    loaded = schema.load(schema.dump(orig))
    members = loaded.members
    assert list(members.items()) == sorted(
        members.items(), key=lambda key_value: key_value[1].offset)
