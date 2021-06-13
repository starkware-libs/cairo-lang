import re

import pytest

from starkware.cairo.lang.compiler.identifier_definition import AliasDefinition, ConstDefinition
from starkware.cairo.lang.compiler.identifier_manager import (
    IdentifierError, IdentifierManager, IdentifierSearchResult, MissingIdentifierError)
from starkware.cairo.lang.compiler.scoped_name import ScopedName

scope = ScopedName.from_string


def test_identifier_manager_get():
    identifier_dict = {
        scope('a.b.c'): ConstDefinition(value=7),
    }
    manager = IdentifierManager.from_dict(identifier_dict)

    for name in ['a', 'a.b']:
        with pytest.raises(MissingIdentifierError, match=f"Unknown identifier '{name}'."):
            manager.get(scope(name))

    # Search 'a.b.c.*'.
    for suffix in ['d', 'd.e']:
        result = manager.get(scope('a.b.c') + scope(suffix))
        assert result == IdentifierSearchResult(
            identifier_definition=identifier_dict[scope('a.b.c')],
            canonical_name=scope('a.b.c'),
            non_parsed=scope(suffix))

        error_msg = re.escape("Unexpected '.' after 'a.b.c' which is const")
        with pytest.raises(IdentifierError, match=error_msg):
            result.assert_fully_parsed()
        with pytest.raises(IdentifierError, match=error_msg):
            result.get_canonical_name()

    result = manager.get(scope('a.b.c'))
    assert result == IdentifierSearchResult(
        identifier_definition=identifier_dict[scope('a.b.c')],
        canonical_name=scope('a.b.c'),
        non_parsed=ScopedName())
    result.assert_fully_parsed()
    assert result.get_canonical_name() == scope('a.b.c')

    for name in ['a.d', 'a.d.e']:
        # The error should point to the first unknown item, rather then the entire name.
        with pytest.raises(MissingIdentifierError, match="Unknown identifier 'a.d'."):
            manager.get(scope(name))


def test_identifier_manager_get_by_full_name():
    identifier_dict = {
        scope('a.b.c'): ConstDefinition(value=7),
        scope('x'): AliasDefinition(destination=scope('a')),
    }
    manager = IdentifierManager.from_dict(identifier_dict)
    assert manager.get_by_full_name(scope('a.b.c')) == identifier_dict[scope('a.b.c')]
    assert manager.get_by_full_name(scope('x')) == identifier_dict[scope('x')]

    assert manager.get_by_full_name(scope('a.b')) is None
    assert manager.get_by_full_name(scope('a.b.c.d')) is None
    assert manager.get_by_full_name(scope('x.b.c')) is None


def test_identifier_manager_aliases():
    identifier_dict = {
        scope('a.b.c'): AliasDefinition(destination=scope('x.y')),
        scope('x.y'): AliasDefinition(destination=scope('x.y2')),
        scope('x.y2.z'): ConstDefinition(value=3),
        scope('x.y2.s.z'): ConstDefinition(value=4),
        scope('x.y2.s2'): AliasDefinition(destination=scope('x.y2.s')),

        scope('z0'): AliasDefinition(destination=scope('z1.z2')),
        scope('z1.z2'): AliasDefinition(destination=scope('z3')),
        scope('z3'): AliasDefinition(destination=scope('z0')),

        scope('to_const'): AliasDefinition(destination=scope('x.y2.z')),
        scope('unresolved'): AliasDefinition(destination=scope('z1.missing')),
    }
    manager = IdentifierManager.from_dict(identifier_dict)

    # Test manager.get().
    assert manager.get(scope('a.b.c.z.w')) == IdentifierSearchResult(
        identifier_definition=identifier_dict[scope('x.y2.z')],
        canonical_name=scope('x.y2.z'),
        non_parsed=scope('w'))
    assert manager.get(scope('to_const.w')) == IdentifierSearchResult(
        identifier_definition=identifier_dict[scope('x.y2.z')],
        canonical_name=scope('x.y2.z'),
        non_parsed=scope('w'))

    with pytest.raises(IdentifierError, match='Cyclic aliasing detected: z0 -> z1.z2 -> z3 -> z0'):
        manager.get(scope('z0'))

    with pytest.raises(IdentifierError, match=(re.escape(
            'Alias resolution failed: unresolved -> z1.missing. '
            "Unknown identifier 'z1.missing'."))):
        manager.get(scope('unresolved'))

    # Test manager.get_scope().
    assert manager.get_scope(scope('a.b')).fullname == scope('a.b')
    assert manager.get_scope(scope('a.b.c')).fullname == scope('x.y2')
    assert manager.get_scope(scope('a.b.c.s')).fullname == scope('x.y2.s')
    assert manager.get_scope(scope('a.b.c.s2')).fullname == scope('x.y2.s')

    with pytest.raises(IdentifierError, match='Cyclic aliasing detected: z0 -> z1.z2 -> z3 -> z0'):
        manager.get_scope(scope('z0'))
    with pytest.raises(IdentifierError, match=(
            'Alias resolution failed: unresolved -> z1.missing. '
            "Unknown identifier 'z1.missing'.")):
        manager.get_scope(scope('unresolved'))
    with pytest.raises(IdentifierError, match=(
            "^Identifier 'x.y2.z' is const, expected a scope.")):
        manager.get_scope(scope('x.y2.z'))
    with pytest.raises(IdentifierError, match=(
            'Alias resolution failed: a.b.c.z.w -> x.y.z.w -> x.y2.z.w. '
            "Identifier 'x.y2.z' is const, expected a scope.")):
        manager.get_scope(scope('a.b.c.z.w'))


def test_identifier_manager_search():
    identifier_dict = {
        scope('a.b.c.y'): ConstDefinition(value=1),
        scope('a.b.x'): ConstDefinition(value=2),
        scope('a.b.z'): ConstDefinition(value=3),
        scope('a.x'): ConstDefinition(value=4),
        scope('x'): ConstDefinition(value=5),
        scope('d.b.w'): ConstDefinition(value=6),
    }
    manager = IdentifierManager.from_dict(identifier_dict)

    for accessible_scopes, name, canonical_name in [
        (['a', 'a.b', 'a.b.c', 'e'], 'x', 'a.b.x'),
        (['a', 'a.b'], 'x', 'a.b.x'),
        (['a.b', 'a'], 'x', 'a.x'),
        ([''], 'x', 'x'),
        (['a', 'e', 'a.b.c'], 'b.z', 'a.b.z'),
    ]:
        result = manager.search(list(map(scope, accessible_scopes)), scope(name))
        assert result.canonical_name == scope(canonical_name)
        assert result.identifier_definition == identifier_dict[scope(canonical_name)]

    with pytest.raises(IdentifierError, match="Unknown identifier 'x'"):
        manager.search([], scope('x'))

    # Since 'd.b' exists, and it does not contain a sub-identifier 'z' the following raises an
    # exception (even though a.b.z exists).
    # Compare with the line (['a', 'e', 'a.b.c'], 'b.z', 'a.b.z') above.
    with pytest.raises(IdentifierError, match="Unknown identifier 'd.b.z'."):
        manager.search([scope('a'), scope('d'), scope('e'), scope('a.b.c')], scope('b.z.w'))
