from typing import List

import pytest

from starkware.cairo.lang.compiler.ast.aliased_identifier import AliasedIdentifier
from starkware.cairo.lang.compiler.ast.bool_expr import BoolAndExpr, BoolEqExpr
from starkware.cairo.lang.compiler.ast.cairo_types import (
    CairoType,
    TypeCodeoffset,
    TypeFelt,
    TypePointer,
    TypeTuple,
)
from starkware.cairo.lang.compiler.ast.code_elements import (
    CodeElementIf,
    CodeElementImport,
    CodeElementReference,
    CodeElementReturn,
    CodeElementReturnValueReference,
    CodeElementTailCall,
)
from starkware.cairo.lang.compiler.ast.expr import (
    ExprConst,
    ExprDeref,
    ExprDot,
    ExprIdentifier,
    ExprNeg,
    ExprOperator,
    ExprParentheses,
    ExprReg,
    ExprSubscript,
    ExprTuple,
)
from starkware.cairo.lang.compiler.ast.formatting_utils import FormattingError
from starkware.cairo.lang.compiler.ast.instructions import (
    AddApInstruction,
    AssertEqInstruction,
    CallInstruction,
    CallLabelInstruction,
    InstructionAst,
    JnzInstruction,
    JumpInstruction,
    JumpToLabelInstruction,
    RetInstruction,
)
from starkware.cairo.lang.compiler.ast.types import TypedIdentifier
from starkware.cairo.lang.compiler.error_handling import Location, LocationError, get_location_marks
from starkware.cairo.lang.compiler.expression_simplifier import ExpressionSimplifier
from starkware.cairo.lang.compiler.instruction import Register
from starkware.cairo.lang.compiler.parser import (
    parse,
    parse_code_element,
    parse_const,
    parse_expr,
    parse_instruction,
    parse_type,
)
from starkware.cairo.lang.compiler.parser_test_utils import verify_exception
from starkware.cairo.lang.compiler.parser_transformer import ParserContext, ParserError
from starkware.python.utils import safe_zip


def test_int():
    expr_const = parse_const(" 01234 ")
    assert expr_const == ExprConst(val=1234)
    assert expr_const.format_str == "01234"
    assert expr_const.format() == "01234"

    expr = parse_expr("-01234")
    assert isinstance(expr, ExprNeg)
    assert expr == ExprNeg(val=ExprConst(val=1234))
    assert isinstance(expr.val, ExprConst)
    assert expr.val.format_str == "01234"
    assert expr.format() == "-01234"

    assert parse_expr("-1234") == parse_expr("- 1234")


def test_hex_int():
    expr_const = parse_const(" 0x1234 ")
    assert expr_const == ExprConst(val=0x1234)
    assert expr_const.format_str == "0x1234"
    assert expr_const.format() == "0x1234"

    expr = parse_expr("-0x01234")
    assert isinstance(expr, ExprNeg)
    assert expr == ExprNeg(val=ExprConst(val=0x1234))
    assert isinstance(expr.val, ExprConst)
    assert expr.val.format_str == "0x01234"
    assert expr.format() == "-0x01234"

    assert parse_expr("-0x1234") == parse_expr("- 0x1234")


def test_short_string():
    expr_const = parse_const(" 'ab' ")
    assert expr_const == ExprConst(val=ord("a") * 256 + ord("b"))
    assert expr_const.format_str == "'ab'"
    assert expr_const.format() == "'ab'"

    expr = parse_expr("-'abc'")
    assert isinstance(expr, ExprNeg)
    assert expr == ExprNeg(val=ExprConst(val=int.from_bytes(b"abc", "big")))
    assert isinstance(expr.val, ExprConst)
    assert expr.val.format_str == "'abc'"
    assert expr.format() == "-'abc'"

    assert parse_expr("-'abcd'") == parse_expr("- 'abcd'")

    assert parse_const(r"'a\x00\x12b'").val == int.from_bytes([ord("a"), 0, 18, ord("b")], "big")
    assert parse_const(r"'\x00\x1'").val == int.from_bytes(
        [0, ord("\\"), ord("x"), ord("1")], "big"
    )

    verify_exception(
        """let x = '0123456789012345678901234567890123456789';""",
        """
file:?:?: Short string (e.g., 'abc') length must be at most 31.
let x = '0123456789012345678901234567890123456789';
        ^****************************************^
""",
    )
    verify_exception(
        """let x = '\u1234';""",
        """
file:?:?: Expected an ascii string. Found: '\u1234'.
let x = '\u1234';
        ^*^
""",
    )


def test_types():
    assert isinstance(parse_type("felt"), TypeFelt)
    assert parse_type("felt").format() == "felt"
    assert isinstance(parse_type("codeoffset"), TypeCodeoffset)
    assert parse_type("codeoffset").format() == "codeoffset"
    assert parse_type("my_namespace.MyStruct  *  *").format() == "my_namespace.MyStruct**"
    assert parse_type("my_namespace.MyStruct*****").format() == "my_namespace.MyStruct*****"


def test_type_tuple():
    typ = parse_type("(felt)")
    assert typ == TypeTuple.unnamed([TypeFelt()])
    assert typ.format() == "(felt,)"
    assert parse_type("( felt, felt* , (felt, T.S,)* )").format() == "(felt, felt*, (felt, T.S)*)"


def test_type_named_tuple():
    typ = parse_type("(a:felt,   b: felt )")
    assert isinstance(typ, TypeTuple)
    assert typ.members[0].name == "a"
    assert typ.members[1].name == "b"
    assert typ.format() == "(a: felt, b: felt)"
    assert (
        parse_type("( a:(felt, felt*) , b:(c:felt,)* )").format()
        == "(a: (felt, felt*), b: (c: felt)*)"
    )

    # With new lines.
    assert parse_type("(\n a:felt\n\n, \n  b: felt \n )").format() == "(a: felt, b: felt)"

    # With comments (parsing, but no auto-formatting).
    typ2 = parse_type("( // This is a comment.\na:felt\n\n, \n  b: felt \n )")
    assert typ2 == typ
    with pytest.raises(
        FormattingError,
        match="Comments inside expressions are not supported by the auto-formatter.",
    ):
        typ2.format()

    # Partially named tuple types can be parsed, but they won't pass the other compilation stages.
    assert parse_type("( felt  , a:felt, )").format() == "(felt, a: felt)"


def test_type_named_tuple_failure():
    verify_exception(
        "local x: (a*: felt)",
        """
file:?:?: Unexpected token Token('COLON', ':'). Expected one of: ")", "*", ",".
local x: (a*: felt)
            ^
""",
    )
    verify_exception(
        "local x: (a.b: felt);",
        """
file:?:?: Unexpected '.' in name.
local x: (a.b: felt);
          ^*^
""",
    )


def test_identifier_and_dot():
    assert parse_expr("x.y . z + x ").format() == "x.y.z + x"
    assert parse_expr(" [x]. y .  z").format() == "[x].y.z"
    assert parse_expr("(x-y).z").format() == "(x - y).z"
    assert parse_expr("x-y.z").format() == "x - y.z"
    assert parse_expr("[ap+1].x.y").format() == "[ap + 1].x.y"
    assert parse_expr("((a.b + c).d * e.f + g.h).i.j").format() == "((a.b + c).d * e.f + g.h).i.j"

    assert parse_expr("(x).y.z") == ExprDot(
        expr=ExprDot(
            expr=ExprParentheses(val=ExprIdentifier(name="x")), member=ExprIdentifier(name="y")
        ),
        member=ExprIdentifier(name="z"),
    )
    assert parse_expr("x.y.z") == ExprIdentifier(name="x.y.z")

    with pytest.raises(ParserError):
        parse_expr(".x")
    with pytest.raises(ParserError):
        parse_expr("x.")
    with pytest.raises(ParserError):
        parse_expr("x.(y+z)")
    with pytest.raises(ParserError):
        parse_expr("x.[a]")


def test_typed_identifier():
    typed_identifier = parse(None, "t :   felt*", "typed_identifier", TypedIdentifier)
    assert typed_identifier.format() == "t: felt*"

    typed_identifier = parse(None, "local    t :   felt", "typed_identifier", TypedIdentifier)
    assert typed_identifier.format() == "local t: felt"


def test_add_expr():
    expr = parse_expr("[fp + 1] + [ap - x]")
    assert expr == ExprOperator(
        a=ExprDeref(addr=ExprOperator(a=ExprReg(reg=Register.FP), op="+", b=ExprConst(val=1))),
        op="+",
        b=ExprDeref(
            addr=ExprOperator(a=ExprReg(reg=Register.AP), op="-", b=ExprIdentifier(name="x"))
        ),
    )
    assert expr.format() == "[fp + 1] + [ap - x]"
    assert parse_expr("[ap-7]+37").format() == "[ap - 7] + 37"


def test_deref_expr():
    expr = parse_expr("[[fp - 7] + 3]")
    assert expr == ExprDeref(
        addr=ExprOperator(
            a=ExprDeref(addr=ExprOperator(a=ExprReg(reg=Register.FP), op="-", b=ExprConst(val=7))),
            op="+",
            b=ExprConst(val=3),
        )
    )
    assert expr.format() == "[[fp - 7] + 3]"


def test_subscript_expr():
    assert parse_expr("x[y]").format() == "x[y]"
    assert parse_expr("[x][y][z][w]").format() == "[x][y][z][w]"
    assert parse_expr("  x  [ [ y[z[w]] ] ]").format() == "x[[y[z[w]]]]"
    assert parse_expr(" (x+y)[z+w] ").format() == "(x + y)[z + w]"
    assert parse_expr("(&x)[3][(a-b)*2][&c]").format() == "(&x)[3][(a - b) * 2][&c]"
    assert parse_expr("x[i+n*j]").format() == "x[i + n * j]"
    assert parse_expr("x+[y][z]").format() == "x + [y][z]"

    assert parse_expr("[x][y][[z]]") == ExprSubscript(
        expr=ExprSubscript(
            expr=ExprDeref(addr=ExprIdentifier(name="x")), offset=ExprIdentifier(name="y")
        ),
        offset=ExprDeref(addr=ExprIdentifier(name="z")),
    )

    with pytest.raises(ParserError):
        parse_expr("x[)]")
    with pytest.raises(ParserError):
        parse_expr("x[]")


def test_operator_precedence():
    code = "(5 + 2) - (3 - 9) * (7 + (-(8 ** 2))) - 10 * (-2) * 5 ** 3 + (((7)))"
    expr = parse_expr(code)
    # Test formatting.
    assert expr.format() == code

    # Compute the value of expr from the tree and compare it with the correct value.
    PRIME = 3 * 2**30 + 1
    simplified_expr = ExpressionSimplifier(PRIME).visit(expr)
    assert isinstance(simplified_expr, ExprConst)
    assert simplified_expr.val == eval(code)


def test_mul_expr():
    assert parse_expr("[ap]*[fp]").format() == "[ap] * [fp]"
    assert parse_expr("[ap]*37").format() == "[ap] * 37"


def test_div_expr():
    assert parse_expr("[ap]/[fp]/3/[ap+1]").format() == "[ap] / [fp] / 3 / [ap + 1]"

    code = "120 / 2 / 3 / 4"
    expr = parse_expr(code)
    # Compute the value of expr from the tree and compare it with the correct value.
    PRIME = 3 * 2**30 + 1
    simplified_expr = ExpressionSimplifier(PRIME).visit(expr)
    assert isinstance(simplified_expr, ExprConst)
    assert simplified_expr.val == 5


def test_cast_expr():
    assert parse_expr("cast( ap , T * * )").format() == "cast(ap, T**)"
    assert (
        parse_expr("cast( ap , T * * ) * (cast(fp, felt))").format()
        == "cast(ap, T**) * (cast(fp, felt))"
    )
    assert parse_expr("cast( \n ap , T * * )").format() == "cast(\n    ap, T**)"


def test_tuple_expr():
    assert parse_expr("(   )").format() == "()"
    assert parse_expr("(  2)").format() == "(2)"  # Not a tuple.
    assert parse_expr("(a= 2)").format() == "(a=2)"  # Tuple.
    assert parse_expr("(  2,)").format() == "(2,)"
    assert parse_expr("( 1  , ap)").format() == "(1, ap)"
    assert parse_expr("( 1  , ap, )").format() == "(1, ap,)"
    assert parse_expr("( a=1 , b=2, c=(d= ()))").format() == "(a=1, b=2, c=(d=()))"

    # Partially named tuples can be parsed, but they won't pass the other compilation stages.
    assert parse_expr("( 1  , a = ap, )").format() == "(1, a=ap,)"

    verify_exception(
        "let x = (,);",
        """
file:?:?: Unexpected comma.
let x = (,);
         ^
""",
    )
    verify_exception(
        "let x = (a, ,);",
        """
file:?:?: Unexpected comma.
let x = (a, ,);
            ^
""",
    )
    verify_exception(
        "let x = ((a)(b));",
        """
file:?:?: Unexpected token Token('LPAR', '('). Expected one of: ")", ",", ".", "[", operator.
let x = ((a)(b));
            ^
""",
    )
    verify_exception(
        "let x = ((a)\n(b));",
        """
file:?:?: Expected a comma before this expression.
(b));
^*^
""",
    )


def test_tuple_expr_with_notes():
    assert (
        parse_expr(
            """\
( 1 , // a.
 ( // c.
      ) //b.
      , (fp,[3]))"""
        ).format()
        == """\
(1,  // a.
    (  // c.
        ),  // b.
    (fp, [3]))"""
    )
    assert (
        parse_expr(
            """\
( 1 // b.
 , // a.
    )"""
        ).format()
        == """\
(1,  // b.
    // a.
    )"""
    )


def test_hint_expr():
    expr = parse_expr("a*nondet   %{6 %}+   7")
    assert expr.format() == "a * nondet %{ 6 %} + 7"


def test_pow_expr():
    assert parse_expr("2 ** 3").format() == "2 ** 3"
    verify_exception(
        "let x = 2 * * 3",
        """
file:?:?: Unexpected token Token('STAR', '*'). Expected: expression.
let x = 2 * * 3
            ^
""",
    )


def test_offsets():
    assert parse_expr(" [ [ ap] -x ]").format() == "[[ap] - x]"
    assert parse_expr(" [ [ ap+foo] -x ]").format() == "[[ap + foo] - x]"
    assert parse_expr(" [ [ fp+  0 ] - 0]").format() == "[[fp + 0] - 0]"
    assert parse_expr(" [ap+-5]").format() == "[ap + (-5)]"
    assert parse_expr(" [ap--5]").format() == "[ap - (-5)]"


def test_instruction():
    # AssertEq.
    expr = parse_instruction("[ap] = [fp], ap++")
    assert expr == InstructionAst(
        body=AssertEqInstruction(
            a=ExprDeref(addr=ExprReg(reg=Register.AP)), b=ExprDeref(addr=ExprReg(reg=Register.FP))
        ),
        inc_ap=True,
    )
    assert expr.format() == "[ap] = [fp], ap++"
    assert parse_instruction("[ap+5] = [fp]+[ap] - 5").format() == "[ap + 5] = [fp] + [ap] - 5"
    assert parse_instruction("[ap+5]+3= [fp]*7,ap  ++ ").format() == "[ap + 5] + 3 = [fp] * 7, ap++"

    # Jump.
    expr = parse_instruction("jmp rel [ap] + x, ap++")
    assert expr == InstructionAst(
        body=JumpInstruction(
            val=ExprOperator(
                a=ExprDeref(addr=ExprReg(reg=Register.AP)), op="+", b=ExprIdentifier(name="x")
            ),
            relative=True,
        ),
        inc_ap=True,
    )
    assert expr.format() == "jmp rel [ap] + x, ap++"
    assert parse_instruction(" jmp   abs[ap]+x").format() == "jmp abs [ap] + x"
    # Make sure the following are not OK.
    with pytest.raises(ParserError):
        parse_instruction("jmp abs")
    with pytest.raises(ParserError):
        parse_instruction("jmpabs[ap]")

    # JumpToLabel.
    expr = parse_instruction("jmp label")
    assert expr == InstructionAst(
        body=JumpToLabelInstruction(label=ExprIdentifier(name="label"), condition=None),
        inc_ap=False,
    )
    assert expr.format() == "jmp label"
    # Make sure the following are not OK.
    with pytest.raises(ParserError):
        parse_instruction("jmp [fp]")
    with pytest.raises(ParserError):
        parse_instruction("jmp 7")

    # Jnz.
    expr = parse_instruction("jmp rel [ap] + x if [fp + 3] != 0")
    assert expr == InstructionAst(
        body=JnzInstruction(
            jump_offset=ExprOperator(
                a=ExprDeref(addr=ExprReg(reg=Register.AP)), op="+", b=ExprIdentifier(name="x")
            ),
            condition=ExprDeref(
                addr=ExprOperator(a=ExprReg(reg=Register.FP), op="+", b=ExprConst(val=3))
            ),
        ),
        inc_ap=False,
    )
    assert expr.format() == "jmp rel [ap] + x if [fp + 3] != 0"
    assert (
        parse_instruction(" jmp   rel 17  if[fp]!=0,ap++").format()
        == "jmp rel 17 if [fp] != 0, ap++"
    )
    # Make sure the following are not OK.
    with pytest.raises(ParserError):
        parse_instruction("jmprel 17 if x != 0")
    with pytest.raises(ParserError):
        parse_instruction("jmp 17 if x")
    with pytest.raises(ParserError, match="!= 0"):
        parse_instruction("jmp rel 17 if x != 2")
    with pytest.raises(ParserError):
        parse_instruction("jmp rel [fp] ifx != 0")

    # Jnz to label.
    expr = parse_instruction("jmp label if [fp] != 0")
    assert expr == InstructionAst(
        body=JumpToLabelInstruction(
            label=ExprIdentifier("label"), condition=ExprDeref(addr=ExprReg(reg=Register.FP))
        ),
        inc_ap=False,
    )
    assert expr.format() == "jmp label if [fp] != 0"
    # Make sure the following are not OK.
    with pytest.raises(ParserError):
        parse_instruction("jmp [fp] if [fp] != 0")
    with pytest.raises(ParserError):
        parse_instruction("jmp 7 if [fp] != 0")

    # Call abs.
    expr = parse_instruction("call abs [fp] + x")
    assert expr == InstructionAst(
        body=CallInstruction(
            val=ExprOperator(
                a=ExprDeref(addr=ExprReg(reg=Register.FP)), op="+", b=ExprIdentifier(name="x")
            ),
            relative=False,
        ),
        inc_ap=False,
    )
    assert expr.format() == "call abs [fp] + x"
    assert parse_instruction("call   abs   17,ap++").format() == "call abs 17, ap++"
    # Make sure the following are not OK.
    with pytest.raises(ParserError):
        parse_instruction("call abs")
    with pytest.raises(ParserError):
        parse_instruction("callabs 7")

    # Call rel.
    expr = parse_instruction("call rel [ap] + x")
    assert expr == InstructionAst(
        body=CallInstruction(
            val=ExprOperator(
                a=ExprDeref(addr=ExprReg(reg=Register.AP)), op="+", b=ExprIdentifier(name="x")
            ),
            relative=True,
        ),
        inc_ap=False,
    )
    assert expr.format() == "call rel [ap] + x"
    assert parse_instruction("call   rel   17,ap++").format() == "call rel 17, ap++"
    # Make sure the following are not OK.
    with pytest.raises(ParserError):
        parse_instruction("call rel")
    with pytest.raises(ParserError):
        parse_instruction("callrel 7")

    # Call label.
    expr = parse_instruction("call label")
    assert expr == InstructionAst(
        body=CallLabelInstruction(label=ExprIdentifier(name="label")), inc_ap=False
    )
    assert expr.format() == "call label"
    assert parse_instruction("call   label ,ap++").format() == "call label, ap++"
    # Make sure the following are not OK.
    with pytest.raises(ParserError):
        parse_instruction("call [fp]")
    with pytest.raises(ParserError):
        parse_instruction("call 7")

    # Ret.
    expr = parse_instruction("ret")
    assert expr == InstructionAst(body=RetInstruction(), inc_ap=False)
    assert expr.format() == "ret"

    # AddAp.
    expr = parse_instruction("ap += [fp] + 2")
    assert expr == InstructionAst(
        body=AddApInstruction(
            expr=ExprOperator(
                a=ExprDeref(addr=ExprReg(reg=Register.FP)), op="+", b=ExprConst(val=2)
            )
        ),
        inc_ap=False,
    )
    assert expr.format() == "ap += [fp] + 2"
    assert parse_instruction("ap  +=[ fp]+   2").format() == "ap += [fp] + 2"
    assert parse_instruction("ap  +=[ fp]+   2,ap ++").format() == "ap += [fp] + 2, ap++"

    # Data word.
    assert parse_instruction("dw  0x123").format() == "dw 0x123"


def test_label():
    assert parse_code_element("test  :").format(100) == "test:"
    verify_exception(
        "test.a:\n",
        """
file:?:?: Unexpected '.' in label name.
test.a:
^****^
""",
    )


def test_import():
    # Test module names without periods.
    res = parse_code_element("from   a    import  b")
    assert res == CodeElementImport(
        path=ExprIdentifier(name="a"),
        import_items=[AliasedIdentifier(orig_identifier=ExprIdentifier(name="b"), local_name=None)],
    )
    assert res.format(allowed_line_length=100) == "from a import b"

    # Test module names without periods, with aliasing.
    res = parse_code_element("from   a    import  b   as   c")
    assert res == CodeElementImport(
        path=ExprIdentifier(name="a"),
        import_items=[
            AliasedIdentifier(
                orig_identifier=ExprIdentifier(name="b"), local_name=ExprIdentifier(name="c")
            )
        ],
    )
    assert res.format(allowed_line_length=100) == "from a import b as c"

    # Test module names with periods.
    res = parse_code_element("from   a.b12.c4    import  lib345")
    assert res == CodeElementImport(
        path=ExprIdentifier(name="a.b12.c4"),
        import_items=[
            AliasedIdentifier(orig_identifier=ExprIdentifier(name="lib345"), local_name=None)
        ],
    )
    assert res.format(allowed_line_length=100) == "from a.b12.c4 import lib345"

    # Test multiple imports.
    res = parse_code_element("from  lib    import  a,b as    b2,   c")

    assert res == CodeElementImport(
        path=ExprIdentifier(name="lib"),
        import_items=[
            AliasedIdentifier(orig_identifier=ExprIdentifier(name="a"), local_name=None),
            AliasedIdentifier(
                orig_identifier=ExprIdentifier(name="b"), local_name=ExprIdentifier(name="b2")
            ),
            AliasedIdentifier(orig_identifier=ExprIdentifier(name="c"), local_name=None),
        ],
    )
    assert res.format(allowed_line_length=100) == "from lib import a, b as b2, c"
    assert (
        res.format(allowed_line_length=20)
        == """\
from lib import (
    a,
    b as b2,
    c,
)"""
    )

    assert res == parse_code_element("from lib import (\n    a, b as b2, c)")

    # Test module with bad identifier (with periods).
    with pytest.raises(ParserError):
        parse_expr("from a.b import c.d")

    # Test module with bad local name (with periods).
    with pytest.raises(ParserError):
        parse_expr("from a.b import c as d.d")


def test_return_value_reference():
    res = parse_code_element("let   z=call  x;")
    assert res.format(allowed_line_length=100) == "let z = call x;"

    res = parse_code_element("let   z:y.z=call  x;")
    assert res.format(allowed_line_length=100) == "let z: y.z = call x;"

    res = parse_code_element("let   z:y.z=call rel x;")
    assert res.format(allowed_line_length=100) == "let z: y.z = call rel x;"

    res = parse_code_element(
        "let very_long_prefix = foo(a=1, b=  1,     very_long_arg_1=1, very_long_arg_2   =1);"
    )
    assert (
        res.format(allowed_line_length=40)
        == """\
let very_long_prefix = foo(
    a=1,
    b=1,
    very_long_arg_1=1,
    very_long_arg_2=1,
);"""
    )

    res = parse_code_element(
        "let (very_long_prefix ,b,c:   T) = foo(a=1, b=  1, very_long_arg_1=1, very_long_arg_2 =1);"
    )
    assert (
        res.format(allowed_line_length=40)
        == """\
let (very_long_prefix, b, c: T) = foo(
    a=1,
    b=1,
    very_long_arg_1=1,
    very_long_arg_2=1,
);"""
    )

    with pytest.raises(ParserError):
        # Const in the unpacking tuple.
        parse_expr("let (1,b,c) = foo(a=1, b=  1)")

    with pytest.raises(ParserError):
        # Missing identifier after call.
        parse_expr("let z = call")

    with pytest.raises(ParserError):
        # 'ap++' cannot be used in the return value reference syntax.
        parse_expr("let z = call x, ap++")


def test_new_operator():
    expr = parse_expr("new Struct(a = 1, b= 2  )")
    assert expr.format() == "new Struct(a=1, b=2)"

    res = parse_code_element("new (    a = 1, b= 2  ) + 5     = 17 + new 7 + 2;")
    assert res.format(allowed_line_length=100) == "(new (a=1, b=2)) + 5 = 17 + (new 7) + 2;"


def test_return():
    res = parse_code_element("return(  1, \na= 2  );")
    assert res.format(allowed_line_length=100) == "return (1, a=2);"


def test_empty_return():
    res = parse_code_element("return( ) ;")
    assert res.format(allowed_line_length=100) == "return ();"


def test_code_element_return():
    res = parse_code_element("return     (res   );")
    assert res.format(allowed_line_length=100) == "return (res);"
    assert isinstance(res, CodeElementReturn)
    assert isinstance(res.expr, ExprParentheses)

    res = parse_code_element("return     (res,);")
    assert res.format(allowed_line_length=100) == "return (res,);"
    assert isinstance(res, CodeElementReturn)
    assert isinstance(res.expr, ExprTuple)

    res = parse_code_element("return  res   *  5;")
    assert res.format(allowed_line_length=100) == "return res * 5;"
    assert isinstance(res, CodeElementReturn)
    assert isinstance(res.expr, ExprOperator)

    code = """\
return (
    res=Point(
    x=points[0].x + points[1].x,
    y=points[0].y + points[1].y),
);"""

    res = parse_code_element(code)
    assert res.format(allowed_line_length=40) == code


def test_func_call():
    res = parse_code_element("fibonacci(  1, \na= 2  );")
    assert res.format(allowed_line_length=100) == "fibonacci(1, a=2);"

    res = parse_code_element("fibonacci  {a=b,c = d}(  1, \na= 2  );")
    assert res.format(allowed_line_length=100) == "fibonacci{a=b, c=d}(1, a=2);"
    assert res.format(allowed_line_length=20) == "fibonacci{a=b, c=d}(\n    1, a=2\n);"
    assert res.format(allowed_line_length=15) == "fibonacci{\n    a=b, c=d\n}(1, a=2);"


def test_tail_call():
    res = parse_code_element("return    fibonacci(  1, \na= 2  );")
    assert isinstance(res, CodeElementTailCall)
    assert res.format(allowed_line_length=100) == "return fibonacci(1, a=2);"

    res = parse_code_element("return    (fibonacci(  1, \na= 2  ));")
    assert isinstance(res, CodeElementReturn)
    assert isinstance(res.expr, ExprParentheses)
    assert (
        res.format(allowed_line_length=100)
        == """\
return (fibonacci(1,
    a=2));"""
    )


def test_func_with_args():
    def def_func(args_str):
        return f"""\
func myfunc{args_str} {{
    [ap] = 4;
}}"""

    def test_format(args_str_wrong, args_str_right="", allowed_line_length=100):
        assert parse_code_element(def_func(args_str_wrong)).format(
            allowed_line_length=allowed_line_length
        ) == def_func(args_str_right)

    test_format("     ( x : T,  y : S,  z    )   ", "(x: T, y: S, z)")
    test_format("(x,y,z)", "(x, y, z)")
    test_format("(x,y,z,)", "(x, y, z)")
    test_format("(x,\ny,\nz)", "(x, y, z)")
    test_format("(\nx,\ny,\nz)", "(x, y, z)")
    test_format("(      )", "()")
    test_format("(\n\n)", "()")

    test_format("(x,y,z,)->   (a,b,c)", "(x, y, z) -> (a, b, c)")
    test_format("()->(a,b,c)", "() -> (a, b, c)")
    test_format("(x,y,z)      ->()", "(x, y, z) -> ()")

    # Implicit arguments.
    test_format("{x,y\n\n}(z,w)->()", "{x, y}(z, w) -> ()")

    # Test that we don't split the line between the '->' and the return type.
    args_str = "{a}(z, w) -> felt"
    splitting_line_length = len(def_func(args_str).splitlines()[0]) - 2
    test_format(args_str, "{a}(\n    z, w\n) -> felt", allowed_line_length=splitting_line_length)

    with pytest.raises(ParserError):
        test_format("")

    with pytest.raises(ParserError):
        # Argument name cannot contain dots.
        test_format("(x.y, z)")

    with pytest.raises(ParserError):
        # Arguments must be separated by a comma.
        test_format("(x y)")

    with pytest.raises(ParserError):
        # Double trailing comma is not allowed.
        test_format("(x,y,z,,)")

    with pytest.raises(FormattingError):
        test_format("(x //comment\n,y,z)->()")


def test_decoractor():
    code = """\
@hello @world


@external func myfunc() {
     return ();
}"""

    assert (
        parse_code_element(code=code).format(allowed_line_length=100)
        == """\
@hello
@world
@external
func myfunc() {
    return ();
}"""
    )


def test_decoractor_errors():
    verify_exception(
        """
@hello world
func myfunc() {
    return ();
}
""",
        """
file:?:?: Unexpected token Token('IDENTIFIER', \'world\'). Expected one of: "@", "func", \
"namespace", "struct".
@hello world
       ^***^
""",
    )

    verify_exception(
        """
@hello-world
func myfunc() {
    return ();
}
""",
        """
file:?:?: Unexpected token Token('MINUS', \'-\'). Expected one of: "@", "func", "namespace", \
"struct".
@hello-world
      ^
""",
    )


def test_reference_type_annotation():
    res = parse_code_element("let s : T *   = ap;")
    assert res.format(allowed_line_length=100) == "let s: T* = ap;"

    with pytest.raises(ParserError):
        parse_expr("local x : = 0;")


def test_addressof():
    res = parse_code_element("static_assert &     s.SIZE ==  ap  ; ")
    assert res.format(allowed_line_length=100) == "static_assert &s.SIZE == ap;"


def test_func_expr():
    res = parse_code_element("let x = f();")
    assert isinstance(res, CodeElementReturnValueReference)
    assert res.format(allowed_line_length=100) == "let x = f();"

    res = parse_code_element("let x = (f());")
    assert isinstance(res, CodeElementReference)
    assert res.format(allowed_line_length=100) == "let x = (f());"


def test_parent_location():
    location = parse_expr("1 + 2").location
    assert location is not None
    parent_location = (location, "An error ocurred while processing:")

    code_element = parse_code_element(
        "let x = 3 + 4;", parser_context=ParserContext(parent_location=parent_location)
    )
    assert isinstance(code_element, CodeElementReference)
    location = code_element.expr.location
    location_err = LocationError(message="Error", location=location)
    assert (
        str(location_err)
        == """\
:1:1: An error ocurred while processing:
1 + 2
^***^
:1:9: Error
let x = 3 + 4;
        ^***^\
"""
    )


def test_locations():
    code_with_marks = """\
 [ap ] = [ fp + 2],  ap ++
 ^***********************^
 ^***************^
 ^***^
  ^^
         ^*******^
           ^****^
           ^^
                ^
"""

    lines = code_with_marks.splitlines()
    code, marks = lines[0], lines[1:]
    expr = parse_instruction(code=code)
    for inner_expr, mark in safe_zip(expr.get_subtree(), marks):
        location = getattr(inner_expr, "location")
        assert isinstance(location, Location)
        assert get_location_marks(content=code, location=location) == code + "\n" + mark


def test_pointer():
    code_with_marks = """\
 felt** ***
 ^********^
 ^*******^
 ^******^
 ^****^
 ^***^
 ^**^
"""

    lines = code_with_marks.splitlines()
    code, marks = lines[0], lines[1:]
    typ = parse_type(code)
    types: List[CairoType] = [
        typ,
    ]
    for _ in range(len(marks) - 1):
        typ = types[-1]
        assert isinstance(typ, TypePointer)
        types.append(typ.pointee)
    for typ, mark in safe_zip(types, marks):
        assert typ.location is not None
        assert get_location_marks(code, typ.location) == code + "\n" + mark


def test_if_and():
    code = """\
if (a == 0 and b == 0) {
    alloc_locals;
}\
"""
    ret = parse_code_element(code)
    assert isinstance(ret, CodeElementIf)
    assert ret.condition == BoolAndExpr(
        a=BoolEqExpr(
            a=ExprIdentifier(name="a"),
            b=ExprConst(val=0),
            eq=True,
        ),
        b=BoolEqExpr(
            a=ExprIdentifier(name="b"),
            b=ExprConst(val=0),
            eq=True,
        ),
    )
    assert ret.format(allowed_line_length=100) == code


def test_if_and_is_left_to_right_associative():
    code = """\
if (a == 0 and b == 0 and c == 0) {
    alloc_locals;
}\
"""
    ret = parse_code_element(code)
    assert isinstance(ret, CodeElementIf)
    assert ret.condition == BoolAndExpr(
        a=BoolAndExpr(
            a=BoolEqExpr(
                a=ExprIdentifier(name="a"),
                b=ExprConst(val=0),
                eq=True,
            ),
            b=BoolEqExpr(
                a=ExprIdentifier(name="b"),
                b=ExprConst(val=0),
                eq=True,
            ),
        ),
        b=BoolEqExpr(
            a=ExprIdentifier(name="c"),
            b=ExprConst(val=0),
            eq=True,
        ),
    )
    assert ret.format(allowed_line_length=100) == code


def test_if_multiline_and():
    code = """\
if (a == 0 and b == 0 and c == 0 and
    d == 0 and e == 0) {
    alloc_locals;
}\
"""
    ret = parse_code_element(code)
    assert ret.format(allowed_line_length=40) == code
