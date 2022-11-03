from starkware.cairo.lang.compiler.unique_name_provider import UniqueNameKind, UniqueNameProvider


def test_unique_name_provider_next():
    provider = UniqueNameProvider()
    assert provider.next(UniqueNameKind.Label) == "$lbl0"
    assert provider.next(UniqueNameKind.Var) == "$var1"
    assert provider.next(UniqueNameKind.Var) == "$var2"


def test_is_name_unique():
    assert UniqueNameProvider.is_name_unique("$lbl1")
    assert not UniqueNameProvider.is_name_unique("x")

    # This is an (acceptable) false positive.
    assert UniqueNameProvider.is_name_unique("$Hello")
