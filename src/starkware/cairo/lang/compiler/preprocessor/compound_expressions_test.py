import itertools
from typing import List, Optional

import pytest

from starkware.cairo.lang.compiler.ast.code_elements import (
    CodeElement,
    CodeElementTemporaryVariable,
)
from starkware.cairo.lang.compiler.ast.expr import Expression
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.parser import parse_expr
from starkware.cairo.lang.compiler.preprocessor.compound_expressions import (
    CompoundExpressionContext,
    CompoundExpressionVisitor,
    SimplicityLevel,
    process_compound_expressions,
)
from starkware.cairo.lang.compiler.preprocessor.preprocessor_test_utils import (
    PRIME,
    preprocess_str,
    strip_comments_and_linebreaks,
    verify_exception,
)
from starkware.cairo.lang.compiler.preprocessor.reg_tracking import RegTrackingData


class CompoundExpressionTestContext(CompoundExpressionContext):
    def __init__(self):
        self.tempvar_name_counter = itertools.count(0)
        self.code_elements: List[CodeElement] = []
        self.ap_tracking = RegTrackingData()

    def new_tempvar_name(self) -> str:
        return f"x{next(self.tempvar_name_counter)}"

    def get_fp_val(self, location: Optional[Location]) -> Expression:
        raise NotImplementedError("fp is not supported in the test.")

    def visit(self, elm: CodeElement):
        def group_alloc():
            raise NotImplementedError("group_alloc() is not expected to be called.")

        assert isinstance(elm, CodeElementTemporaryVariable)
        self.ap_tracking = self.ap_tracking.add(1, group_alloc=group_alloc)
        self.code_elements.append(elm)

    def get_ap_tracking(self) -> RegTrackingData:
        return self.ap_tracking


@pytest.mark.parametrize(
    "expr_str, to_operation, to_deref_const, to_deref_offset, to_deref",
    [
        [
            "5",
            "5",
            "5",
            "tempvar x0: felt = 5; x0",
            "tempvar x0: felt = 5; x0",
        ],
        [
            "[ap + 5]",
            "[ap + 5]",
            "[ap + 5]",
            "[ap + 5]",
            "[ap + 5]",
        ],
        [
            "[ap + 5] + 3",
            "[ap + 5] + 3",
            "tempvar x0: felt = [ap - 0 + 5] + 3; x0",
            "[ap + 5] + 3",
            "tempvar x0: felt = [ap - 0 + 5] + 3; x0",
        ],
        [
            "3 + [ap + 5]",
            "tempvar x0: felt = 3; x0 + [ap + 5]",
            "tempvar x0: felt = 3; tempvar x1: felt = x0 + [ap - 1 + 5]; x1",
            "tempvar x0: felt = 3; tempvar x1: felt = x0 + [ap - 1 + 5]; x1",
            "tempvar x0: felt = 3; tempvar x1: felt = x0 + [ap - 1 + 5]; x1",
        ],
        [
            "[[ap + 5]]",
            "[[ap + 5]]",
            "tempvar x0: felt = [[ap - 0 + 5]]; x0",
            "tempvar x0: felt = [[ap - 0 + 5]]; x0",
            "tempvar x0: felt = [[ap - 0 + 5]]; x0",
        ],
        [
            "[[[ap + 5]]]",
            "tempvar x0: felt = [[ap - 0 + 5]]; [x0]",
            "tempvar x0: felt = [[ap - 0 + 5]]; tempvar x1: felt = [x0]; x1",
            "tempvar x0: felt = [[ap - 0 + 5]]; tempvar x1: felt = [x0]; x1",
            "tempvar x0: felt = [[ap - 0 + 5]]; tempvar x1: felt = [x0]; x1",
        ],
        [
            "[3]",
            "tempvar x0: felt = 3; [x0]",
            "tempvar x0: felt = 3; tempvar x1: felt = [x0]; x1",
            "tempvar x0: felt = 3; tempvar x1: felt = [x0]; x1",
            "tempvar x0: felt = 3; tempvar x1: felt = [x0]; x1",
        ],
        [
            "-[ap + 3]",
            "[ap + 3] * (-1)",
            "tempvar x0: felt = [ap - 0 + 3] * (-1); x0",
            "tempvar x0: felt = [ap - 0 + 3] * (-1); x0",
            "tempvar x0: felt = [ap - 0 + 3] * (-1); x0",
        ],
    ],
)
def test_compound_expression_visitor(
    expr_str: str, to_operation: str, to_deref_const: str, to_deref_offset: str, to_deref: str
):
    """
    Tests rewriting various expression, to the different simplicity levels.
    For example, to_operation is the expected result when the simplicity level is OPERATION.
    """
    expr = parse_expr(expr_str)
    for sim, expected_result in [
        (SimplicityLevel.OPERATION, to_operation),
        (SimplicityLevel.DEREF_CONST, to_deref_const),
        (SimplicityLevel.DEREF_OFFSET, to_deref_offset),
        (SimplicityLevel.DEREF, to_deref),
    ]:
        context = CompoundExpressionTestContext()
        visitor = CompoundExpressionVisitor(context=context)
        res = visitor.rewrite(expr, sim)
        assert (
            "".join(
                code_element.format(allowed_line_length=100) + " "
                for code_element in context.code_elements
            )
            + res.format()
            == expected_result
        )


def test_compound_expression_visitor_long():
    context = CompoundExpressionTestContext()
    visitor = CompoundExpressionVisitor(context=context)
    res = visitor.rewrite(
        parse_expr("[ap + 100] - [fp] * [[-[ap + 200] / [ap + 300]]] + [ap] * [ap]"),
        SimplicityLevel.OPERATION,
    )
    assert (
        "".join(
            code_element.format(allowed_line_length=100) + "\n"
            for code_element in context.code_elements
        )
        == """\
tempvar x0: felt = [ap - 0 + 200] * (-1);
tempvar x1: felt = x0 / [ap - 1 + 300];
tempvar x2: felt = [x1];
tempvar x3: felt = [x2];
tempvar x4: felt = [fp] * x3;
tempvar x5: felt = [ap - 5 + 100] - x4;
tempvar x6: felt = [ap - 6] * [ap - 6];
"""
    )
    assert res.format() == "x5 + x6"


def test_compound_expression_visitor_inverses():
    context = CompoundExpressionTestContext()
    visitor = CompoundExpressionVisitor(context=context)
    res = visitor.rewrite(parse_expr("2 - 1 / [ap] + [ap] / 3"), SimplicityLevel.DEREF)
    assert (
        "".join(
            code_element.format(allowed_line_length=100) + "\n"
            for code_element in context.code_elements
        )
        == """\
tempvar x0: felt = 2;
tempvar x1: felt = 1;
tempvar x2: felt = x1 / [ap - 2];
tempvar x3: felt = x0 - x2;
tempvar x4: felt = [ap - 4] / 3;
tempvar x5: felt = x3 + x4;
"""
    )
    assert res.format() == "x5"


def test_process_compound_expressions():
    context = CompoundExpressionTestContext()
    res = process_compound_expressions(
        list(
            map(
                parse_expr,
                [
                    "[ap - 1] + 5",
                    "[ap - 1] * [ap - 1]",
                    "[ap - 1] * [ap - 1]",
                    "[ap - 2] * [ap - 2] * [ap - 3]",
                    "[ap - 1]",
                ],
            )
        ),
        [
            SimplicityLevel.OPERATION,
            SimplicityLevel.OPERATION,
            SimplicityLevel.DEREF,
            SimplicityLevel.OPERATION,
            SimplicityLevel.OPERATION,
        ],
        context=context,
    )
    assert (
        "".join(
            code_element.format(allowed_line_length=100) + "\n"
            for code_element in context.code_elements
        )
        == """\
tempvar x0: felt = [ap - 0 - 1] * [ap - 0 - 1];
tempvar x1: felt = [ap - 1 - 2] * [ap - 1 - 2];
"""
    )
    assert [x.format() for x in res] == [
        "[ap - 2 - 1] + 5",
        "[ap - 2 - 1] * [ap - 2 - 1]",
        "x0",
        "x1 * [ap - 2 - 3]",
        "[ap - 2 - 1]",
    ]


def test_compound_expressions():
    code = """\
assert [ap] = [ap + 1] * [ap + 2];
assert 5 = [[ap - 1]];
assert [[ap - 1]] = 5;
assert [ap - 2] = [[ap - 1] - 5];
assert [ap - 2] = [[ap - 1] + 999999];
assert [[ap + 5 + 5]] = [ap - 1];
assert [ap - 1] = [[[ap + 5 + 5]]];
assert [[ap - 1]] = [[ap - 2]];

tempvar __fp__ = 100;
assert [fp] = fp + [fp + [fp]];

let __fp__ = [ap - 1] + [ap - 1];
assert [fp] = fp + fp;
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[ap] = [ap + 1] * [ap + 2];

[ap] = [[ap + (-1)]], ap++;
5 = [ap + (-1)];

[ap] = 5, ap++;
[[ap + (-2)]] = [ap + (-1)];

[ap + (-2)] = [[ap + (-1)] + (-5)];

[ap] = [ap + (-1)] + 999999, ap++;
[ap + (-3)] = [[ap + (-1)]];

[[ap + 10]] = [ap + (-1)];

[ap] = [[ap + 10]], ap++;
[ap + (-2)] = [[ap + (-1)]];

[ap] = [[ap + (-2)]], ap++;
[[ap + (-2)]] = [ap + (-1)];

[ap] = 100, ap++;
[ap] = [ap + (-1)] + [fp], ap++;
[ap] = [[ap + (-1)]], ap++;
[fp] = [ap + (-3)] + [ap + (-1)];

[ap] = [ap + (-1)] + [ap + (-1)], ap++;
[ap] = [ap + (-2)] + [ap + (-2)], ap++;
[fp] = [ap + (-2)] + [ap + (-1)];
""".replace(
            "\n\n", "\n"
        )
    )


def test_compound_expressions_long():
    code = """\
let x = [[ap - 1]];
let y = [fp];
let z = [ap + 100];
assert x + y * z + x / ((-x) - (y - z)) = x * x;
"""
    program = preprocess_str(code=code, prime=PRIME)
    expected_result = """\
[ap] = [[ap + (-1)]], ap++;  // Compute x.
[ap] = [fp] * [ap + 99], ap++;  // Compute y * z.
[ap] = [ap + (-2)] + [ap + (-1)], ap++;  // Compute x + y * z.
[ap] = [[ap + (-4)]], ap++;  // Compute x.
[ap] = [[ap + (-5)]], ap++;  // Compute x.
[ap] = [ap + (-1)] * (-1), ap++;  // Compute -x.
[ap] = [fp] - [ap + 94], ap++;  // Compute y - z
[ap] = [ap + (-2)] - [ap + (-1)], ap++;  // Compute -x - (y - z).
[ap] = [ap + (-5)] / [ap + (-1)], ap++;  // Compute x / (-x - (y - z)).
[ap] = [[ap + (-10)]], ap++;  // Compute x.
[ap] = [[ap + (-11)]], ap++;  // Compute x.
[ap] = [ap + (-2)] * [ap + (-1)], ap++;  // Compute x * x.
[ap + (-10)] + [ap + (-4)] = [ap + (-1)];  // Assert x + y * z + x / (-x - (y - z)) = x * x.
"""
    assert program.format() == strip_comments_and_linebreaks(expected_result)


def test_compound_expressions_tempvars():
    code = """\
tempvar x = [ap - 1] * [ap - 1] + [ap - 1] * [ap - 2];
tempvar y = x + x;
tempvar z = 5 + nondet %{ val %} * 15 + nondet %{ 1 %};
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[ap] = [ap + (-1)] * [ap + (-1)], ap++;
[ap] = [ap + (-2)] * [ap + (-3)], ap++;
[ap] = [ap + (-2)] + [ap + (-1)], ap++;

[ap] = [ap + (-1)] + [ap + (-1)], ap++;

%{ memory[ap] = to_felt_or_relocatable(val) %}
ap += 1;
[ap] = [ap + (-1)] * 15, ap++;
[ap] = [ap + (-1)] + 5, ap++;
%{ memory[ap] = to_felt_or_relocatable(1) %}
ap += 1;
[ap] = [ap + (-2)] + [ap + (-1)], ap++;
""".replace(
            "\n\n", "\n"
        )
    )


def test_compound_expressions_localvar():
    code = """\
func f() {
    alloc_locals;
    local x;
    local y = x * x + [ap - 1] * [ap - 2];
    local z = y + y;
    ret;
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    expected_result = """\
ap += 3;

[ap] = [fp] * [fp], ap++;  // x * x.
[ap] = [ap + (-2)] * [ap + (-3)], ap++;  // [ap - 1] * [ap - 2].
[fp + 1] = [ap + (-2)] + [ap + (-1)];  // x * x + [ap - 1] * [ap - 2].

[fp + 2] = [fp + 1] + [fp + 1];  // y + y.

ret;
"""
    assert program.format() == strip_comments_and_linebreaks(expected_result)


def test_compound_expressions_args():
    code = """\
func foo(a, b, c, d) -> (x: felt, y: felt) {
    return (a + b, c * c + d);
}

tempvar x = 5;
foo(x + x, x + x * x, x, 3 * x + x * x);
"""
    program = preprocess_str(code=code, prime=PRIME)
    expected_result = """\
[ap] = [fp + (-4)] * [fp + (-4)], ap++;  // Compute c * c.
[ap] = [fp + (-6)] + [fp + (-5)], ap++;  // Push a + b.
[ap] = [ap + (-2)] + [fp + (-3)], ap++;  // Push c * c + d.
ret;

[ap] = 5, ap++;

[ap] = [ap + (-1)] * [ap + (-1)], ap++;  // Compute x * x.
[ap] = 3, ap++;
[ap] = [ap + (-1)] * [ap + (-3)], ap++;  // Compute 3 * x.
[ap] = [ap + (-4)] * [ap + (-4)], ap++;  // Compute x * x.
[ap] = [ap + (-5)] + [ap + (-5)], ap++;  // Push x + x.
[ap] = [ap + (-6)] + [ap + (-5)], ap++;  // Push x + x * x.
[ap] = [ap + (-7)], ap++;  // Push x.
[ap] = [ap + (-5)] + [ap + (-4)], ap++;  // Push 3 * x + x * x.
call rel -15;
"""
    assert program.format() == strip_comments_and_linebreaks(expected_result)


def test_compound_expressions_failures():
    verify_exception(
        """\
assert [ap + [ap]] = [ap];
""",
        """
file:?:?: ap may only be used in an expression of the form [ap + <const>].
assert [ap + [ap]] = [ap];
        ^^
""",
    )
    verify_exception(
        """\
assert [[ap]] = ap;
""",
        """
file:?:?: ap may only be used in an expression of the form [ap + <const>].
assert [[ap]] = ap;
                ^^
""",
    )
    verify_exception(
        """\
assert [[fp]] = fp;
""",
        """
file:?:?: Using the value of fp directly, requires defining a variable named __fp__.
assert [[fp]] = fp;
                ^^
""",
    )
    verify_exception(
        """\
assert [ap] = [ap + 32768];  // Offset is out of bounds.
""",
        """
file:?:?: ap may only be used in an expression of the form [ap + <const>].
assert [ap] = [ap + 32768];  // Offset is out of bounds.
               ^^
""",
    )
    verify_exception(
        """\
struct T {
    a: felt,
}
assert 7 = cast(7, T*);
""",
        """
file:?:?: Cannot compare 'felt' and 'test_scope.T*'.
assert 7 = cast(7, T*);
^*********************^
""",
    )
