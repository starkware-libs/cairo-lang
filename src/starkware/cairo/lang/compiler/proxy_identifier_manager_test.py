import pytest

from starkware.cairo.lang.compiler.identifier_definition import ConstDefinition
from starkware.cairo.lang.compiler.identifier_manager import (
    IdentifierManager,
    MissingIdentifierError,
)
from starkware.cairo.lang.compiler.proxy_identifier_manager import (
    ProxyIdentifierManager,
    ProxyIdentifierScope,
)
from starkware.cairo.lang.compiler.scoped_name import ScopedName

scope = ScopedName.from_string


def test_identifier_manager_get():
    identifier_dict = {
        scope("a.b.c"): ConstDefinition(value=7),
    }
    manager = IdentifierManager.from_dict(identifier_dict)
    proxy = ProxyIdentifierManager(manager)
    for full_name in ["a", "a.b"]:
        proxy_scope = proxy.get_scope(scope(full_name))
        assert isinstance(proxy_scope, ProxyIdentifierScope)
        assert proxy_scope.parent == manager.get_scope(scope(full_name))
    assert proxy.get(scope("a.b.c")) == manager.get(scope("a.b.c"))

    proxy.add_identifier(scope("a.d"), ConstDefinition(value=8))
    proxy.get_scope(scope("a.b")).add_identifier(scope("e.f"), ConstDefinition(value=9))

    # Not present in original.
    with pytest.raises(MissingIdentifierError, match="Unknown identifier 'a.d'."):
        assert manager.get(scope("a.d"))
    with pytest.raises(MissingIdentifierError, match="Unknown identifier 'a.d'."):
        assert manager.get_scope(scope("a")).get(scope("d"))
    with pytest.raises(MissingIdentifierError, match="Unknown identifier 'a.b.e'."):
        assert manager.get_scope(scope("a.b.e")).get(scope("f"))
    assert manager.as_dict() == {ScopedName(path=("a", "b", "c")): ConstDefinition(value=7)}

    # Present in proxy.
    assert proxy.get(scope("a.d")).identifier_definition == ConstDefinition(value=8)
    assert proxy.get_scope(scope("a")).get(scope("d")).identifier_definition == ConstDefinition(
        value=8
    )
    assert proxy.get_scope(scope("a.b.e")).get(scope("f")).identifier_definition == ConstDefinition(
        value=9
    )
    assert dict(proxy.as_dict()) == {
        ScopedName(path=("a", "d")): ConstDefinition(value=8),
        ScopedName(path=("a", "b", "c")): ConstDefinition(value=7),
        ScopedName(path=("a", "b", "e", "f")): ConstDefinition(value=9),
    }

    # Present in original.
    proxy.apply()
    assert manager.get(scope("a.d")) == proxy.get(scope("a.d"))
    assert manager.get_scope(scope("a")).get(scope("d")) == proxy.get_scope(scope("a")).get(
        scope("d")
    )
    assert manager.get_scope(scope("a.b.e")).get(scope("f")) == proxy.get_scope(scope("a.b.e")).get(
        scope("f")
    )
    assert manager.as_dict() == dict(proxy.as_dict())
