from starkware.cairo.lang.compiler.parser_test_utils import verify_exception


def test_unexpected_token():
    verify_exception(
        """
x + = y
""",
        """
file:?:?: Unexpected token Token('EQUAL', '='). Expected: expression.
x + = y
    ^
""",
    )
    verify_exception(
        """
let x =
""",
        r"""
file:?:?: Unexpected token Token('_NEWLINE', '\n'). Expected one of: "call", expression.
let x =
       ^
""",
    )
    verify_exception(
        """
foo bar
""",
        """
file:?:?: Unexpected token Token('IDENTIFIER', 'bar'). Expected one of: "(", ".", ":", "=", "[", \
"{", operator.
foo bar
    ^*^
""",
    )
    verify_exception(
        """
foo = bar test
""",
        """
file:?:?: Unexpected token Token('IDENTIFIER', 'test'). Expected one of: "(", ",", ".", ";", "[", \
"{", operator.
foo = bar test
          ^**^
""",
    )
    verify_exception(
        """
const func
""",
        """
file:?:?: Unexpected token Token('FUNC', 'func'). Expected: identifier.
const func
      ^**^
""",
    )
    verify_exception(
        """
5 7
""",
        """
file:?:?: Unexpected token Token('INT', '7'). Expected one of: ".", "=", "[", operator.
5 7
  ^
""",
    )
    verify_exception(
        """
static_assert ap
""",
        r"""
file:?:?: Unexpected token Token('_NEWLINE', '\n'). Expected one of: ".", "==", "[", operator.
static_assert ap
                ^
""",
    )
    verify_exception(
        """
[ap] = x& + y
""",
        """
file:?:?: Unexpected token Token('AMPERSAND', '&'). Expected one of: "(", ",", ".", ";", "[", "{", \
operator.
[ap] = x& + y
        ^
""",
    )
    verify_exception(
        """
func &
""",
        """
file:?:?: Unexpected token Token('AMPERSAND', '&'). Expected: identifier.
func &
     ^
""",
    )
    verify_exception(
        """
let x : T 5
""",
        """
file:?:?: Unexpected token Token('INT', '5'). Expected one of: "*", ".", "=".
let x : T 5
          ^
""",
    )
    verify_exception(
        """
foo( *
""",
        """
file:?:?: Unexpected token Token('STAR', '*'). Expected one of: ")", ",", expression.
foo( *
     ^
""",
    )
    verify_exception(
        """
if (x y
""",
        """
file:?:?: Unexpected token Token('IDENTIFIER', 'y'). Expected one of: "!=", "(", ".", "==", "[", \
"{", operator.
if (x y
      ^
""",
    )
    verify_exception(
        """
x = y, ap--
""",
        """
file:?:?: Unexpected token Token('MINUS', '-'). Expected: "++".
x = y, ap--
         ^
""",
    )
    verify_exception(
        """
func foo()*
""",
        """
file:?:?: Unexpected token Token('STAR', '*'). Expected one of: "->", "{".
func foo()*
          ^
""",
    )


def test_unexpected_character():
    verify_exception(
        """
x~y
""",
        """
file:?:?: Unexpected character "~".
x~y
 ^
""",
    )


def test_parser_error():
    # Unexpected EOF - missing 'end'.
    verify_exception(
        """
func f() {
const a = 5;
""",
        """
file:?:?: Unexpected end of input. Expected one of: "%builtins", "%lang", "@", "alloc_locals", \
"assert", "call", "const", "dw", "from", "func", ...
const a = 5;
            ^
""",
    )


def test_new_operator_error():
    verify_exception(
        """
let a = new
""",
        """
file:?:?: Unexpected token Token('_NEWLINE', '\\n'). Expected: expression.
let a = new
           ^
""",
    )

    verify_exception(
        """
new = 5
""",
        """
file:?:?: Unexpected token Token('EQUAL', '='). Expected: expression.
new = 5
    ^
""",
    )

    verify_exception(
        """
new A()
""",
        """
file:?:?: Unexpected token Token('_NEWLINE', '\\n'). Expected one of: ".", "=", "[", operator.
new A()
       ^
""",
    )

    verify_exception(
        """
new A().f
""",
        """
file:?:?: Unexpected token Token('_NEWLINE', '\\n'). Expected one of: ".", "=", "[", operator.
new A().f
         ^
""",
    )

    verify_exception(
        """
new A() new
""",
        """
file:?:?: Unexpected token Token('NEW', 'new'). Expected one of: ".", "=", "[", operator.
new A() new
        ^*^
""",
    )


def test_modifier_in_tuple():
    verify_exception(
        """
let a : (b : local felt) = 5;
""",
        """
file:?:?: Unexpected token Token('LOCAL', 'local'). Expected one of: \
"(", "codeoffset", "felt", identifier.
let a : (b : local felt) = 5;
             ^***^
""",
    )


def test_if_with_parenthesized_condition():
    verify_exception(
        """
if ((a == 0 and b == 1)) {
    let x = 0;
}
""",
        """
file:?:?: Unexpected token Token(\'_DBL_EQ\', \'==\'). Expected one of: "(", ")", ",", ".", "=", \
"[", "{", operator.
if ((a == 0 and b == 1)) {
       ^^
      """,
    )


def test_modifier_in_return_type():
    verify_exception(
        """
func f(x) -> (local y) {
    ret;
}
""",
        """
file:?:?: Unexpected token Token('LOCAL', 'local'). \
Expected one of: "(", ")", ",", "codeoffset", "felt", identifier.
func f(x) -> (local y) {
              ^***^
""",
    )


def test_bad_struct():
    verify_exception(
        """
struct T {
    return ();
}
""",
        """
file:?:?: Unexpected token Token('RETURN', 'return'). Expected one of: "local", "}", identifier.
    return ();
    ^****^
""",
    )
