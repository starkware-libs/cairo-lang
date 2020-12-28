from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt
from starkware.cairo.lang.compiler.identifier_definition import ConstDefinition, MemberDefinition
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.identifier_utils import get_struct_members
from starkware.cairo.lang.compiler.scoped_name import ScopedName

scope = ScopedName.from_string


def test_get_struct_members():
    identifier_dict = {
        scope('T.b'): MemberDefinition(offset=1, cairo_type=TypeFelt()),
        scope('T.a'): MemberDefinition(offset=0, cairo_type=TypeFelt()),

        scope('T.SIZE'): ConstDefinition(value=2),
        scope('S.a'): MemberDefinition(offset=0, cairo_type=TypeFelt()),
        scope('S.c'): MemberDefinition(offset=1, cairo_type=TypeFelt()),
        scope('S.SIZE'): ConstDefinition(value=2),
    }
    manager = IdentifierManager.from_dict(identifier_dict)

    member = get_struct_members(scope('T'), manager)
    # Convert to a list, to check the order of the elements in the dict.
    assert list(member.items()) == [
        ('a', MemberDefinition(offset=0, cairo_type=TypeFelt())),
        ('b', MemberDefinition(offset=1, cairo_type=TypeFelt())),
    ]
