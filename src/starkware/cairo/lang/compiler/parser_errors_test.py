import pytest

from starkware.cairo.lang.compiler.parser import ParserError, parse_file
from starkware.cairo.lang.compiler.parser_test_utils import verify_exception


def test_unexpected_token():
    verify_exception("""
x + = y
""", """
file:?:?: Unexpected token Token(EQUAL, '='). Expected: expression.
x + = y
    ^
""")
    verify_exception("""
let x =
""", r"""
file:?:?: Unexpected token Token(_NEWLINE, '\n'). Expected one of: "call", expression.
let x =
       ^
""")
    verify_exception("""
foo bar
""", """
file:?:?: Unexpected token Token(IDENTIFIER, 'bar'). Expected one of: "(", ".", ":", "=", "[", \
"{", operator.
foo bar
    ^*^
""")
    verify_exception("""
foo = bar test
""", """
file:?:?: Unexpected token Token(IDENTIFIER, 'test'). Expected one of: "(", ".", ";", "[", "{", \
operator.
foo = bar test
          ^**^
""")
    verify_exception("""
const func
""", """
file:?:?: Unexpected token Token(FUNC, 'func'). Expected: identifier.
const func
      ^**^
""")
    verify_exception("""
%[ 5 %] %[ 7 %]
""", """
file:?:?: Unexpected token Token(PYCONST, '%[ 7 %]'). Expected one of: ".", "=", "[", operator.
%[ 5 %] %[ 7 %]
        ^*****^
""")
    verify_exception("""
static_assert ap
""", r"""
file:?:?: Unexpected token Token(_NEWLINE, '\n'). Expected one of: ".", "==", "[", operator.
static_assert ap
                ^
""")
    verify_exception("""
[ap] = x& + y
""", """
file:?:?: Unexpected token Token(AMPERSAND, '&'). Expected one of: "(", ".", ";", "[", "{", \
operator.
[ap] = x& + y
        ^
""")
    verify_exception("""
func &
""", """
file:?:?: Unexpected token Token(AMPERSAND, '&'). Expected: identifier.
func &
     ^
""")
    verify_exception("""
let x : T 5
""", """
file:?:?: Unexpected token Token(INT, '5'). Expected one of: "*", ".", "=".
let x : T 5
          ^
""")
    verify_exception("""
foo( *
""", """
file:?:?: Unexpected token Token(STAR, '*'). Expected one of: ")", expression.
foo( *
     ^
""")
    verify_exception("""
if x y
""", """
file:?:?: Unexpected token Token(IDENTIFIER, 'y'). Expected one of: "!=", "(", ".", "==", "[", \
"{", operator.
if x y
     ^
""")
    verify_exception("""
x = y; ap--
""", """
file:?:?: Unexpected token Token(MINUS, '-'). Expected: "++".
x = y; ap--
         ^
""")
    verify_exception("""
func foo()*
""", """
file:?:?: Unexpected token Token(STAR, '*'). Expected one of: "->", ":".
func foo()*
          ^
""")


def test_unexpected_character():
    verify_exception("""
x~y
""", """
file:?:?: Unexpected character "~".
x~y
 ^
""")


def test_parser_error():
    # Unexpected EOF - missing 'end'.
    with pytest.raises(ParserError, match='Unexpected end-of-input.') as e:
        parse_file(code="""
func f():
const a = 5
""")
    assert str(e.value).endswith("""
const a = 5
          ^""")
