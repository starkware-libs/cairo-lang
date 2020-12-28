import pytest

from starkware.cairo.lang.compiler.scoped_name import ScopedName


def test_scoped_name():
    assert ScopedName(('some', 'thing')).path == ('some', 'thing')
    assert str(ScopedName(('some', 'thing'))) == 'some.thing'
    assert ScopedName.from_string('some.thing').path == ('some', 'thing')
    assert ScopedName(('some', 'thing')) + 'el.se' == ScopedName(('some', 'thing', 'el', 'se'))
    assert ScopedName(('some', 'thing')) + 'el.se' != ScopedName(('some', 'thing', 'else'))

    assert ScopedName.from_string('aa.bb.cc.dd')[1:3] == ScopedName.from_string('bb.cc')

    with pytest.raises(AssertionError):
        ScopedName(('some', 'thing.else'))


def test_empty():
    assert str(ScopedName()) == ''
    assert ScopedName.from_string('') == ScopedName()


def test_len():
    assert len(ScopedName()) == 0
    assert len(ScopedName.from_string('a')) == 1
    assert len(ScopedName.from_string('a.b')) == 2
    assert len(ScopedName.from_string('x.a.b')) == 3
    assert len(ScopedName.from_string('x.a.b.c')) == 4


def test_startswith():
    assert ScopedName.from_string('a.b').startswith(ScopedName.from_string('a'))
    assert not ScopedName.from_string('x.a.b').startswith(ScopedName.from_string('a'))
    assert not ScopedName.from_string('a.b').startswith(ScopedName.from_string('x'))
    assert not ScopedName.from_string('a.b').startswith('b')
    assert ScopedName.from_string('x.a.b').startswith('')
    assert ScopedName.from_string('x.a.b').startswith('x.a')
    assert not ScopedName.from_string('abc').startswith('a')
