import pytest

from starkware.cairo.lang.compiler.ast.ast_objects_test_utils import remove_parentheses
from starkware.cairo.lang.compiler.ast.expr import ExprConst, ExprNeg, ExprOperator
from starkware.cairo.lang.compiler.ast.formatting_utils import (
    FormattingError,
    set_one_item_per_line,
)
from starkware.cairo.lang.compiler.parser import parse_code_element, parse_expr, parse_file


def test_format_parentheses():
    """
    Tests that format() adds parentheses where required.
    """

    # Call remove_parentheses(parse_expr()) to create an expression tree in the given structure
    # without ExprParentheses.
    assert (
        remove_parentheses(parse_expr("(a + b) * (c - d) * (e * f)")).format()
        == "(a + b) * (c - d) * e * f"
    )
    assert (
        remove_parentheses(parse_expr("x - (a + b) - (c - d) - (e * f)")).format()
        == "x - (a + b) - (c - d) - e * f"
    )
    assert (
        remove_parentheses(parse_expr("(a + b) + (c - d) + (e * f)")).format()
        == "a + b + c - d + e * f"
    )
    assert remove_parentheses(parse_expr("-(a + b + c)")).format() == "-(a + b + c)"
    assert remove_parentheses(parse_expr("a + -b + c")).format() == "a + (-b) + c"
    assert remove_parentheses(parse_expr("&(a + b)")).format() == "&(a + b)"
    assert remove_parentheses(parse_expr("a ** b ** c ** d")).format() == "a ** (b ** (c ** d))"

    # Test that parentheses are added to non-atomized Dot and Subscript expressions.
    assert remove_parentheses(parse_expr("(x * y).z")).format() == "(x * y).z"
    assert remove_parentheses(parse_expr("(-x).y")).format() == "(-x).y"
    assert remove_parentheses(parse_expr("(&x).y")).format() == "(&x).y"
    assert remove_parentheses(parse_expr("(x * y)[z]")).format() == "(x * y)[z]"
    assert remove_parentheses(parse_expr("(-x)[y]")).format() == "(-x)[y]"
    assert remove_parentheses(parse_expr("(&x)[y]")).format() == "(&x)[y]"

    assert remove_parentheses(parse_expr("&(x.y)")).format() == "&x.y"
    assert remove_parentheses(parse_expr("-(x.y)")).format() == "-x.y"
    assert remove_parentheses(parse_expr("(x.y)*z")).format() == "x.y * z"
    assert remove_parentheses(parse_expr("x-(y.z)")).format() == "x - y.z"

    assert remove_parentheses(parse_expr("([x].y).z")).format() == "[x].y.z"
    assert remove_parentheses(parse_expr("&(x[y])")).format() == "&x[y]"
    assert remove_parentheses(parse_expr("-(x[y])")).format() == "-x[y]"
    assert remove_parentheses(parse_expr("(x[y])*z")).format() == "x[y] * z"
    assert remove_parentheses(parse_expr("x-(y[z])")).format() == "x - y[z]"
    assert remove_parentheses(parse_expr("(([x][y])[z])")).format() == "[x][y][z]"
    assert remove_parentheses(parse_expr("x[(y+z)]")).format() == "x[y + z]"

    assert remove_parentheses(parse_expr("[((x+y) + z)]")).format() == "[x + y + z]"

    assert remove_parentheses(parse_expr("new (2+3)")).format() == "new (2 + 3)"

    # Test that parentheses are not added if they were already present.
    assert parse_expr("(a * (b + c))").format() == "(a * (b + c))"
    assert parse_expr("((a * ((b + c))))").format() == "((a * ((b + c))))"
    assert parse_expr("(x + y)[z]").format() == "(x + y)[z]"


def test_format_parentheses_notes():
    before = """\
(  //    Comment.
         a + b)"""
    after = """\
(  // Comment.
    a + b)"""
    assert parse_expr(before).format() == after

    before = """\
(
         a + b)"""
    after = """\
(
    a + b)"""
    assert parse_expr(before).format() == after

    before = """\
(
      //    Comment.
         a + b)"""
    after = """\
(
    // Comment.
    a + b)"""
    assert parse_expr(before).format() == after

    before = """\
(//    Comment.
      //
      // x.
      // y.
         a + b)"""
    after = """\
(  // Comment.
    //
    // x.
    // y.
    a + b)"""
    assert parse_expr(before).format() == after


def test_format_func_call_notes():
    before = """\
foo(x = 12 // Comment.
);"""
    with pytest.raises(FormattingError, match="Comments inside expressions are not supported"):
        parse_code_element(before).format(allowed_line_length=100)


def test_negative_numbers():
    assert ExprConst(-1).format() == "-1"
    assert ExprNeg(val=ExprConst(val=1)).format() == "-1"
    assert ExprOperator(a=ExprConst(val=-1), op="+", b=ExprConst(val=-2)).format() == "(-1) + (-2)"
    assert (
        ExprOperator(
            a=ExprNeg(val=ExprConst(val=1)), op="+", b=ExprNeg(val=ExprConst(val=2))
        ).format()
        == "(-1) + (-2)"
    )


def test_file_format():
    before = """

ap+=[ fp ]  ;
%lang starknet
[ap + -1] = [fp]  *  3;
 const x=y  +  f(a=g(
                      z) ,// test
                      b=0);
    struct  A{

 x:T.S ,
 }
 let x= ap-y  +  z;
 let y:a.b.c= x;



  label  :
[ap] = [fp],  ap ++;
tempvar x=y*z+w;
tempvar q      : felt;
  alloc_locals;
local     z                     :T*=x;
assert x*z+x=    y+y;
static_assert   ap + (3 +   7 )+ ap   ==fp;
let()=foo();
return  (1,[fp],
  [ap +3],);
   fibonacci  (a = 3 , b=[fp +1]);
[ap - 1] = [fp];//    This is a comment.
  //This is another comment.
label2:

  jmp rel 17 if [ap+3]!=  0;
[fp] = [fp] * [fp];
with_attr     no_value_attribute  {
[ap] = [fp], ap++;
}
with_attr single_line_attribute  (

    "A single line value"

    ) {
    [ap] = [fp], ap++;
}
with_attr long_value_attribute(
    "A single line with_attr expression that is too long and does not fit into a single line") {
    [ap] = [fp], ap++;
}
with_attr error_message  (  "Attribute value " "with"

" multiple"
"\\n"
"lines"  ) {
    [ap] = [fp], ap++;
}"""
    after = """\
ap += [fp];
%lang starknet
[ap + (-1)] = [fp] * 3;
const x = y + f(a=g(
        z),  // test
    b=0);
struct A {
    x: T.S,
}
let x = ap - y + z;
let y: a.b.c = x;

label:
[ap] = [fp], ap++;
tempvar x = y * z + w;
tempvar q: felt;
alloc_locals;
local z: T* = x;
assert x * z + x = y + y;
static_assert ap + (3 + 7) + ap == fp;
let () = foo();
return (1, [fp], [ap + 3],);
fibonacci(a=3, b=[fp + 1]);
[ap - 1] = [fp];  // This is a comment.

// This is another comment.
label2:
jmp rel 17 if [ap + 3] != 0;
[fp] = [fp] * [fp];
with_attr no_value_attribute {
    [ap] = [fp], ap++;
}
with_attr single_line_attribute("A single line value") {
    [ap] = [fp], ap++;
}
with_attr long_value_attribute(
        "A single line with_attr expression that is too long and does not fit into a single line") {
    [ap] = [fp], ap++;
}
with_attr error_message(
        "Attribute value "
        "with"
        " multiple"
        "\\n"
        "lines") {
    [ap] = [fp], ap++;
}
"""
    assert parse_file(before).format() == after


def test_file_format_comments():
    before = """

// First line.
[ap] = [ap];


// Separator comment.


[ap] = [ap];
[ap] = [ap];


// Comment before label.
  label  :
[ap] = [ap]; //    Inline.
  //This is another
  // comment before label.
label2://Inline (label).

[ap] = [ap];
label3:
[ap] = [ap];
// End of file comment."""
    after = """\
// First line.
[ap] = [ap];

// Separator comment.

[ap] = [ap];
[ap] = [ap];

// Comment before label.
label:
[ap] = [ap];  // Inline.

// This is another
// comment before label.
label2:  // Inline (label).
[ap] = [ap];

label3:
[ap] = [ap];
// End of file comment.
"""
    assert parse_file(before).format() == after


def test_file_format_comment_spaces():
    before = """
//   First line.
//{spaces}
//   Second line.{spaces}
//Fourth line.
//   Third line.
[ap] = [ap]; //    inline comment.
//   First line.
//   Second line.

//   First line.
//   Second line.
[ap] = [ap]; //{spaces}
""".format(
        spaces="   "
    )
    after = """\
// First line.
//
//   Second line.
// Fourth line.
//   Third line.
[ap] = [ap];  // inline comment.
// First line.
//   Second line.

// First line.
//   Second line.
[ap] = [ap];  //
"""
    assert parse_file(before).format() == after


def test_file_format_hint():
    before = """\
label:
 %{
 x = y
 "[ fp ]"#Python comment is not auto-formatted
  %}//Cairo Comment

    %{
    %} // Empty hint.
"""
    after = """\
label:
%{
    x = y
    "[ fp ]"#Python comment is not auto-formatted
%}  // Cairo Comment

%{
%}  // Empty hint.
"""
    assert parse_file(before).format() == after


def test_file_format_hints_indent():
    before = """\
  %{
  hint1
  hint2
%}
[fp] = [fp];
func f() {
  %{

    if a:
        b
%}
[fp] = [fp];
}
"""
    after = """\
%{
    hint1
    hint2
%}
[fp] = [fp];
func f() {
    %{
        if a:
            b
    %}
    [fp] = [fp];
}
"""
    assert parse_file(before).format() == after


def test_parse_struct():
    before = """\
struct MyStruct{
x,// Comment1.


      y  :  felt**  ,
 } // Comment2.
"""
    after = """\
struct MyStruct {
    x,  // Comment1.

    y: felt**,
}  // Comment2.
"""
    assert parse_file(before).format() == after


def test_parse_namespace():
    before = """\
namespace MyNamespace {
x = 5;
      y=3;
 } // Comment.

namespace MyNamespace2 {
 }
"""
    after = """\
namespace MyNamespace {
    x = 5;
    y = 3;
}  // Comment.

namespace MyNamespace2 {
}
"""
    assert parse_file(before).format() == after


def test_parse_func():
    before = """\
[ap] = 1, ap++;

func fib() {

      [ap] = 2, ap++;
      ap += 3;
 ret;


 } // Comment.

 call fib;
"""
    after = """\
[ap] = 1, ap++;

func fib() {
    [ap] = 2, ap++;
    ap += 3;
    ret;
}  // Comment.

call fib;
"""
    assert parse_file(before).format() == after


def test_func_arg_splitting():
    before = """\
func myfunc{x, y, z, w, foo_bar}(a, b, c, foo, bar,
    variable_name_which_is_way_too_long_but_has_to_be_supported, g) {
  ret;
}
"""
    after = """\
func myfunc{
        x, y, z, w,
        foo_bar}(
        a, b, c, foo,
        bar,
        variable_name_which_is_way_too_long_but_has_to_be_supported,
        g) {
    ret;
}
"""
    with set_one_item_per_line(False):
        assert parse_file(before).format(allowed_line_length=25) == after


def test_return_splitting():
    before = """\
return (a, b, c, foo, bar,
        variable_name_which_is_way_too_long_but_has_to_be_supported, g);
"""
    after = """\
return (
    a,
    b,
    c,
    foo,
    bar,
    variable_name_which_is_way_too_long_but_has_to_be_supported,
    g);
"""
    with set_one_item_per_line(False):
        assert parse_file(before).format(allowed_line_length=20) == after


def test_func_arg_ret_splitting():
    before = """\
func myfunc(a, b, c, foo, bar,
    variable_name_which_is_way_too_long_but_has_to_be_supported, g)
    -> (x, y, z, a_return_arg_which_is_also_waaaaaaay_too_long, w) {
  ret;
}
"""
    after = """\
func myfunc(
        a, b, c, foo,
        bar,
        variable_name_which_is_way_too_long_but_has_to_be_supported,
        g) -> (
        x, y, z,
        a_return_arg_which_is_also_waaaaaaay_too_long,
        w) {
    ret;
}
"""
    with set_one_item_per_line(False):
        assert parse_file(before).format(allowed_line_length=25) == after
    before = """\
func myfunc(a, b, c, foo, bar,
    variable_name_which_is_way_too_long_but_has_to_be_supported, g) ->
    (x, y, z) {
  ret;
}
"""
    after = """\
func myfunc(
        a, b, c, foo,
        bar,
        variable_name_which_is_way_too_long_but_has_to_be_supported,
        g) -> (x, y, z) {
    ret;
}
"""
    with set_one_item_per_line(False):
        assert parse_file(before).format(allowed_line_length=25) == after
    before = """\
func myfunc(ab, cd, ef) -> (x, y, z, a_return_arg_which_is_also_waaaaaaay_too_long, w) {
  ret;
}
"""
    after = """\
func myfunc(
        ab, cd, ef) -> (
        x, y, z,
        a_return_arg_which_is_also_waaaaaaay_too_long,
        w) {
    ret;
}
"""
    with set_one_item_per_line(False):
        assert parse_file(before).format(allowed_line_length=25) == after


def test_func_one_per_line_splitting():
    before = """\
func myfunc{x, y}(a, b) {
    ret;
}
"""
    with set_one_item_per_line(True):
        assert parse_file(before).format(allowed_line_length=25) == before
    before = """\
func myfunc{x: felt*, y: felt*}(a, b, c, d) {
    ret;
}
"""
    after = """\
func myfunc{
    x: felt*, y: felt*
}(a, b, c, d) {
    ret;
}
"""
    with set_one_item_per_line(True):
        assert parse_file(before).format(allowed_line_length=25) == after
    before = """\
func myfunc{long_imp_arg1, long_imp_arg2,long_imp_arg3}(
        very_long_arg1, very_long_arg2) {
    ret;
}
"""
    after = """\
func myfunc{
    long_imp_arg1,
    long_imp_arg2,
    long_imp_arg3,
}(
    very_long_arg1,
    very_long_arg2,
) {
    ret;
}
"""
    with set_one_item_per_line(True):
        assert parse_file(before).format(allowed_line_length=25) == after
    before = """\
func myfunc{}(a, variable_name_which_is_way_too_long_but_has_to_be_supported) {
    ret;
}
"""
    after = """\
func myfunc{}(
    a,
    variable_name_which_is_way_too_long_but_has_to_be_supported,
) {
    ret;
}
"""
    with set_one_item_per_line(True):
        assert parse_file(before).format(allowed_line_length=25) == after
    before = """\
func myfunc(ab, cd, ef) -> (
        long_return_arg1, long_return_arg2) {
    ret;
}
"""
    after = """\
func myfunc(
    ab, cd, ef
) -> (
    long_return_arg1,
    long_return_arg2,
) {
    ret;
}
"""
    with set_one_item_per_line(True):
        assert parse_file(before).format(allowed_line_length=25) == after


def test_return_one_per_line_splitting():
    before = """\
return (a, b, c, foo, bar,
        variable_name_which_is_way_too_long_but_has_to_be_supported, g);
"""
    after = """\
return (
    a,
    b,
    c,
    foo,
    bar,
    variable_name_which_is_way_too_long_but_has_to_be_supported,
    g,
);
"""
    with set_one_item_per_line(True):
        assert parse_file(before).format(allowed_line_length=25) == after


def test_func_call_one_per_line_splitting():
    before = """\
let (a, b, c) = foo(long_arg1, long_arg2, long_arg3);
"""
    after = """\
let (a, b, c) = foo(
    long_arg1,
    long_arg2,
    long_arg3,
);
"""
    with set_one_item_per_line(True):
        assert parse_file(before).format(allowed_line_length=25) == after
    before = """\
return foo(long_arg1, long_arg2, long_arg3);
"""
    after = """\
return foo(
    long_arg1,
    long_arg2,
    long_arg3,
);
"""
    with set_one_item_per_line(True):
        assert parse_file(before).format(allowed_line_length=25) == after


def test_import_one_per_line_splitting():
    before = """\
from a.b.c import (import1)
from d import (import1, import2)
"""
    after = """\
from a.b.c import import1
from d import (
    import1,
    import2,
)
"""
    with set_one_item_per_line(True):
        assert parse_file(before).format(allowed_line_length=25) == after


def test_directives():
    code = """\
[ap] = [ap];
// Comment.
%builtins ab cd ef  // Comment.

[fp] = [fp];
"""
    assert parse_file(code).format() == code


def test_if():
    code = """\
if ((a + 1) / b == [fp]) {
    [ap] = [ap];
}
"""
    assert parse_file(code).format() == code

    code = """\
if ((a + 1) / b != 5) {
    [ap] = [ap];
} else {
    [ap] = [ap];
}
"""
    assert parse_file(code).format() == code


def test_with():
    code = """\
with   a , b  as   c,d  {
    [ap] = [ap];
    }
"""
    assert (
        parse_file(code).format()
        == """\
with a, b as c, d {
    [ap] = [ap];
}
"""
    )


def test_with_attr():
    code = """\
with_attr attribute_name  ("Comments"
        // within attribute value
        " are not supported") {
    [ap] = [fp], ap++;
}"""
    with pytest.raises(FormattingError, match="Comments inside expressions are not supported"):
        parse_code_element(code).format(allowed_line_length=100)


def test_100_chars_long_import():
    code = """\
from a.b.c import (
    import1, import2, import3, import4, import5, import6, import6, import8, import8, aaaaaaaaaaaaaa,
    import9)
"""
    with set_one_item_per_line(False):
        assert parse_file(code).format() == code


def test_tuples():
    code = """\
local x: (
    a: felt,
    b: (c: felt,
        d: felt,
        e: (felt, (felt, felt)),
        f: (g: felt, h: felt),
        i: (felt, felt, felt)));
"""
    with set_one_item_per_line(True):
        assert (
            parse_file(code).format()
            == """\
local x: (
    a: felt,
    b: (c: felt, d: felt, e: (felt, (felt, felt)), f: (g: felt, h: felt), i: (felt, felt, felt)),
);
"""
        )

        assert (
            parse_file(code).format(allowed_line_length=50)
            == """\
local x: (
    a: felt,
    b: (
        c: felt,
        d: felt,
        e: (felt, (felt, felt)),
        f: (g: felt, h: felt),
        i: (felt, felt, felt),
    ),
);
"""
        )
