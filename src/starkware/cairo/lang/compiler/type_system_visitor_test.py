import re
from typing import Optional

import pytest

from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt, TypePointer, TypeStruct
from starkware.cairo.lang.compiler.ast.expr import ExprFutureLabel, ExprNewOperator
from starkware.cairo.lang.compiler.ast_objects_test import remove_parentheses
from starkware.cairo.lang.compiler.expression_transformer import ExpressionTransformer
from starkware.cairo.lang.compiler.identifier_definition import MemberDefinition, StructDefinition
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.parser import parse_expr
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.type_system import mark_types_in_expr_resolved
from starkware.cairo.lang.compiler.type_system_visitor import CairoTypeError, simplify_type_system

scope = ScopedName.from_string


class FixIsTypedVisitor(ExpressionTransformer):
    """
    A utility class the sets expr.is_typed to false.

    This is useful for getting parsed expressions with is_typed = False to compare
    against type system simplified expressions.
    """

    def visit_ExprNewOperator(self, expr: ExprNewOperator) -> ExprNewOperator:
        return ExprNewOperator(
            expr=self.visit(expr=expr.expr),
            is_typed=False,
            location=self.location_modifier(expr.location),
        )

    def visit_ExprFutureLabel(self, expr: ExprFutureLabel) -> ExprFutureLabel:
        return ExprFutureLabel(
            identifier=self.visit(expr.identifier),
            is_typed=False,
            location=self.location_modifier(expr.location),
        )


def simplify_type_system_test(
    orig_expr: str,
    simplified_expr: str,
    simplified_type: str,
    identifiers: Optional[IdentifierManager] = None,
):
    parsed_expr = mark_types_in_expr_resolved(parse_expr(orig_expr))
    expr, typ = simplify_type_system(parsed_expr, identifiers=identifiers)
    expected_expr = FixIsTypedVisitor().visit(
        expr=remove_parentheses(expr=parse_expr(simplified_expr))
    )
    assert expr == expected_expr, f"{expr.format()} != {expected_expr.format()}"
    assert typ.format() == simplified_type


def test_type_visitor():
    simplify_type_system_test("fp + 3 + [ap]", "fp + 3 + [ap]", "felt")
    simplify_type_system_test("cast(fp + 3 + [ap], T*)", "fp + 3 + [ap]", "T*")
    # Two casts.
    simplify_type_system_test("cast(cast(fp, T*), felt)", "fp", "felt")
    # Cast from T to T.
    simplify_type_system_test("cast([cast(fp, T*)], T)", "[fp]", "T")
    # Dereference.
    simplify_type_system_test("[cast(fp, T**)]", "[fp]", "T*")
    simplify_type_system_test("[[cast(fp, T**)]]", "[[fp]]", "T")
    # Address of.
    simplify_type_system_test("&([[cast(fp, T**)]])", "[fp]", "T*")
    simplify_type_system_test("&&[[cast(fp, T**)]]", "fp", "T**")


def test_type_tuples():
    # Simple tuple.
    simplify_type_system_test(
        "(fp, [cast(fp, T*)], cast(fp,T*))",
        "(fp, [fp], fp)",
        "(felt, T, T*)",
    )

    # Named tuple.
    simplify_type_system_test(
        "(a=fp, b=[cast(fp, T*)], c=cast(fp,T*))",
        "(fp, [fp], fp)",
        "(a: felt, b: T, c: T*)",
    )

    # Nested.
    simplify_type_system_test(
        "(fp, (), ([cast(fp, T*)],))",
        "(fp, (), ([fp],))",
        "(felt, (), (T,))",
    )


def test_type_tuples_failures():
    identifier_dict = {
        scope("T"): StructDefinition(
            full_name=scope("T"),
            members={
                "x": MemberDefinition(offset=0, cairo_type=TypeFelt()),
                "y": MemberDefinition(offset=1, cairo_type=TypeFelt()),
            },
            size=2,
        ),
    }
    identifiers = IdentifierManager.from_dict(identifier_dict)

    verify_exception(
        "1 + cast((1, 2), T).x",
        """
file:?:?: Accessing struct/tuple members for r-value structs is not supported yet.
1 + cast((1, 2), T).x
    ^***************^
""",
        identifiers=identifiers,
    )


def test_type_subscript_op():
    t = TypeStruct(scope=scope("T"))

    identifier_dict = {scope("T"): StructDefinition(full_name=scope("T"), members={}, size=7)}
    identifiers = IdentifierManager.from_dict(identifier_dict)

    simplify_type_system_test("cast(fp, felt*)[3]", "[fp + 3 * 1]", "felt")
    simplify_type_system_test("cast(fp, felt***)[0]", "[fp + 0 * 1]", "felt**")
    simplify_type_system_test("[cast(fp, T****)][ap][ap]", "[[[fp] + ap * 1] + ap * 1]", "T*")
    simplify_type_system_test(
        "cast(fp, T**)[1][2]", "[[fp + 1 * 1] + 2 * 7]", "T", identifiers=identifiers
    )

    # Test that 'cast(fp, T*)[2 * ap + 3]' simplifies into '[fp + (2 * ap + 3) * 7]', but without
    # the parentheses.
    assert simplify_type_system(
        mark_types_in_expr_resolved(parse_expr("cast(fp, T*)[2 * ap + 3]")), identifiers=identifiers
    ) == (remove_parentheses(parse_expr("[fp + (2 * ap + 3) * 7]")), t)

    # Test subscript operator for tuples.
    simplify_type_system_test("(cast(fp, felt**), fp, cast(fp, T*))[2]", "fp", "T*")
    simplify_type_system_test("(cast(fp, felt**), fp, cast(fp, T*))[0]", "fp", "felt**")
    simplify_type_system_test("(cast(fp, felt**), ap, cast(fp, T*))[3*4 - 11]", "ap", "felt")
    simplify_type_system_test("[cast(ap, (felt, felt)*)][0]", "[ap + 0]", "felt")
    simplify_type_system_test(
        "[cast(ap, (T*, T, felt, T*, felt*)*)][3]", "[ap + 9]", "T*", identifiers=identifiers
    )

    # Test failures.

    verify_exception(
        "(fp, fp, fp)[cast(ap, felt*)]",
        """
file:?:?: Cannot apply subscript-operator with offset of non-felt type 'felt*'.
(fp, fp, fp)[cast(ap, felt*)]
             ^*************^
""",
    )

    verify_exception(
        "(fp, fp, fp)[[ap]]",
        """
file:?:?: Subscript-operator for tuples supports only constant offsets, found 'ExprDeref'.
(fp, fp, fp)[[ap]]
             ^**^
""",
    )

    verify_exception(
        "(fp, fp, fp)[3]",
        """
file:?:?: Tuple index 3 is out of range [0, 3).
(fp, fp, fp)[3]
^*************^
""",
    )

    verify_exception(
        "[cast(fp, (T*, T, felt)*)][-1]",
        """
file:?:?: Tuple index -1 is out of range [0, 3).
[cast(fp, (T*, T, felt)*)][-1]
^****************************^
""",
    )

    verify_exception(
        "cast(fp, felt)[0]",
        """
file:?:?: Cannot apply subscript-operator to non-pointer, non-tuple type 'felt'.
cast(fp, felt)[0]
^***************^
""",
    )

    verify_exception(
        "[cast(fp, T*)][0]",
        """
file:?:?: Cannot apply subscript-operator to non-pointer, non-tuple type 'T'.
[cast(fp, T*)][0]
^***************^
""",
    )

    verify_exception(
        "cast(fp, felt*)[[cast(ap, T*)]]",
        """
file:?:?: Cannot apply subscript-operator with offset of non-felt type 'T'.
cast(fp, felt*)[[cast(ap, T*)]]
                ^************^
""",
    )

    verify_exception(
        "cast(fp, Z*)[0]",
        """
file:?:?: Unknown identifier 'Z'.
cast(fp, Z*)[0]
^*************^
""",
        identifiers=identifiers,
    )

    verify_exception(
        "cast(fp, T*)[0]",
        """
file:?:?: Unknown identifier 'T'.
cast(fp, T*)[0]
^*************^
""",
        identifiers=None,
    )


def test_type_dot_op():
    """
    Tests type_system_visitor for ExprDot-s, in the following struct architecture:

    struct S {
        x: felt,
        y: felt,
    }

    struct T {
        t: felt,
        s: S,
        sp: S*,
    }

    struct R {
        r: R*,
    }
    """
    t = TypeStruct(scope=scope("T"))
    s = TypeStruct(scope=scope("S"))
    s_star = TypePointer(pointee=s)
    r = TypeStruct(scope=scope("R"))
    r_star = TypePointer(pointee=r)

    identifier_dict = {
        scope("T"): StructDefinition(
            full_name=scope("T"),
            members={
                "t": MemberDefinition(offset=0, cairo_type=TypeFelt()),
                "s": MemberDefinition(offset=1, cairo_type=s),
                "sp": MemberDefinition(offset=3, cairo_type=s_star),
            },
            size=4,
        ),
        scope("S"): StructDefinition(
            full_name=scope("S"),
            members={
                "x": MemberDefinition(offset=0, cairo_type=TypeFelt()),
                "y": MemberDefinition(offset=1, cairo_type=TypeFelt()),
            },
            size=2,
        ),
        scope("R"): StructDefinition(
            full_name=scope("R"),
            members={
                "r": MemberDefinition(offset=0, cairo_type=r_star),
            },
            size=1,
        ),
    }

    identifiers = IdentifierManager.from_dict(identifier_dict)

    for (orig_expr, simplified_expr, simplified_type) in [
        ("[cast(fp, T*)].t", "[fp]", "felt"),
        ("[cast(fp, T*)].s", "[fp + 1]", "S"),
        ("[cast(fp, T*)].sp", "[fp + 3]", "S*"),
        ("[cast(fp, T*)].s.x", "[fp + 1]", "felt"),
        ("[cast(fp, T*)].s.y", "[fp + 1 + 1]", "felt"),
        ("[[cast(fp, T*)].sp].x", "[[fp + 3]]", "felt"),
        ("[cast(fp, R*)]", "[fp]", "R"),
        ("[cast(fp, R*)].r", "[fp]", "R*"),
        ("[[[cast(fp, R*)].r].r].r", "[[[fp]]]", "R*"),
        # Test . as ->
        ("cast(fp, T*).t", "[fp]", "felt"),
        ("cast(fp, T*).sp.y", "[[fp + 3] + 1]", "felt"),
        ("cast(fp, R*).r.r.r", "[[[fp]]]", "R*"),
        # More tests.
        ("(cast(fp, T*).s)", "[fp + 1]", "S"),
        ("(cast(fp, T*).s).x", "[fp + 1]", "felt"),
        ("(&(cast(fp, T*).s)).x", "[fp + 1]", "felt"),
    ]:
        simplify_type_system_test(
            orig_expr, simplified_expr, simplified_type, identifiers=identifiers
        )

    # Test failures.

    verify_exception(
        "cast(fp, felt).x",
        """
file:?:?: Cannot apply dot-operator to non-struct type 'felt'.
cast(fp, felt).x
^**************^
""",
        identifiers=identifiers,
    )

    verify_exception(
        "cast(fp, felt*).x",
        """
file:?:?: Cannot apply dot-operator to pointer-to-non-struct type 'felt*'.
cast(fp, felt*).x
^***************^
""",
        identifiers=identifiers,
    )

    verify_exception(
        "cast(fp, T*).x",
        """
file:?:?: Member 'x' does not appear in definition of struct 'T'.
cast(fp, T*).x
^************^
""",
        identifiers=identifiers,
    )

    verify_exception(
        "cast(fp, Z*).x",
        """
file:?:?: Unknown identifier 'Z'.
cast(fp, Z*).x
^************^
""",
        identifiers=identifiers,
    )

    verify_exception(
        "cast(fp, T*).x",
        """
file:?:?: Identifiers must be initialized for type-simplification of dot-operator expressions.
cast(fp, T*).x
^************^
""",
        identifiers=None,
    )

    verify_exception(
        "cast(fp, Z*).x",
        """
file:?:?: Type is expected to be fully resolved at this point.
cast(fp, Z*).x
         ^
""",
        identifiers=identifiers,
        resolve_types=False,
    )


def test_type_dot_op_named_tuples():
    """
    Tests type_system_visitor for ExprDot-s for named tuples.
    """
    identifiers = IdentifierManager()
    tuple_ref = "[cast(fp, (x: felt, y: (a: felt, b: felt), z: felt)*)]"
    tuple_ptr = "cast(fp, (x: felt, y: (a: felt, b: felt)*, z: felt)*)"
    for (orig_expr, simplified_expr, simplified_type) in [
        (f"{tuple_ref}.x", "[fp]", "felt"),
        (f"{tuple_ref}.y", "[fp + 1]", "(a: felt, b: felt)"),
        (f"{tuple_ref}.y.a", "[fp + 1]", "felt"),
        (f"{tuple_ref}.y.b", "[fp + 1 + 1]", "felt"),
        (f"{tuple_ref}.z", "[fp + 3]", "felt"),
        # Test . as ->
        (f"{tuple_ptr}.y.b", "[[fp + 1] + 1]", "felt"),
    ]:
        simplify_type_system_test(
            orig_expr, simplified_expr, simplified_type, identifiers=identifiers
        )

    # Test failures.

    verify_exception(
        "[cast(fp, (felt, felt)*)].x",
        """
file:?:?: Cannot apply dot-operator to unnamed tuple type '(felt, felt)'.
[cast(fp, (felt, felt)*)].x
^*************************^
""",
        identifiers=identifiers,
    )
    verify_exception(
        "[cast(fp, (a: felt, b: felt)*)].x",
        """
file:?:?: Member 'x' does not appear in definition of tuple type '(a: felt, b: felt)'.
[cast(fp, (a: felt, b: felt)*)].x
^*******************************^
""",
        identifiers=identifiers,
    )

    verify_exception(
        "(x=1, y=(a=2,b=3), z=4).y.b",
        """
file:?:?: Accessing struct/tuple members for r-value structs is not supported yet.
(x=1, y=(a=2,b=3), z=4).y.b
^***********************^
""",
        identifiers=identifiers,
    )


def test_type_visitor_failures():
    verify_exception(
        "[cast(fp, T*)] + 3",
        """
file:?:?: Operator '+' is not implemented for types 'T' and 'felt'.
[cast(fp, T*)] + 3
^****************^
""",
    )
    verify_exception(
        "[[cast(fp, T*)]]",
        """
file:?:?: Cannot dereference type 'T'.
[[cast(fp, T*)]]
^**************^
""",
    )
    verify_exception(
        "[cast(fp, T)]",
        """
file:?:?: Cannot cast 'felt' to 'T'.
[cast(fp, T)]
 ^*********^
""",
    )
    verify_exception(
        "&(cast(fp, T*) + 3)",
        """
file:?:?: Expression has no address.
&(cast(fp, T*) + 3)
  ^**************^
""",
    )


def test_type_visitor_pointer_arithmetic():
    simplify_type_system_test("cast(fp, T*) + 3", "fp + 3", "T*")
    simplify_type_system_test("cast(fp, T*) - 3", "fp - 3", "T*")
    simplify_type_system_test("cast(fp, T*) - cast(3, T*)", "fp - 3", "felt")


def test_type_visitor_new_operator():
    simplify_type_system_test("new (3 + 4)", "new (3 + 4)", "felt*")
    simplify_type_system_test("new [cast(fp, T*)]", "new [fp]", "T*")
    simplify_type_system_test("new (ap, cast(fp, felt*))", "new (ap, fp)", "(felt, felt*)*")


def test_type_visitor_pointer_arithmetic_failures():
    verify_exception(
        "cast(fp, T*) + cast(fp, T*)",
        """
file:?:?: Operator '+' is not implemented for types 'T*' and 'T*'.
cast(fp, T*) + cast(fp, T*)
^*************************^
""",
    )
    verify_exception(
        "cast(fp, T*) - cast(fp, S*)",
        """
file:?:?: Operator '-' is not implemented for types 'T*' and 'S*'.
cast(fp, T*) - cast(fp, S*)
^*************************^
""",
    )
    verify_exception(
        "fp - cast(fp, T*)",
        """
file:?:?: Operator '-' is not implemented for types 'felt' and 'T*'.
fp - cast(fp, T*)
^***************^
""",
    )


def verify_exception(
    expr_str: str, error: str, identifiers: Optional[IdentifierManager] = None, resolve_types=True
):
    """
    Verifies that calling simplify_type_system() on the code results in the given error.
    """
    with pytest.raises(CairoTypeError) as e:
        parsed_expr = parse_expr(expr_str)
        if resolve_types:
            parsed_expr = mark_types_in_expr_resolved(parsed_expr)
        simplify_type_system(parsed_expr, identifiers)
    # Remove line and column information from the error using a regular expression.
    assert re.sub(":[0-9]+:[0-9]+: ", "file:?:?: ", str(e.value)) == error.strip()
