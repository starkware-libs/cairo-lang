import pytest

from starkware.cairo.lang.compiler.expression_simplifier import (
    ExpressionSimplifier,
    SimplifierError,
)
from starkware.cairo.lang.compiler.parser import parse_expr
from starkware.cairo.lang.compiler.substitute_identifiers import substitute_identifiers


@pytest.mark.parametrize("prime", [None, 3 * 2**30 + 1])
def test_simplifier(prime):
    assignments = {"x": 10, "y": 3, "z": -2, "w": -60}
    simplifier = ExpressionSimplifier(prime)
    simplify = lambda expr: simplifier.visit(
        substitute_identifiers(expr=expr, get_identifier_callback=lambda var: assignments[var.name])
    )
    assert simplify(parse_expr("fp + x * (y + -1)")).format() == "fp + 20"
    assert simplify(parse_expr("[fp + x] + [ap - (-z)]")).format() == "[fp + 10] + [ap + (-2)]"
    assert simplify(parse_expr("fp + x - y")).format() == "fp + 7"
    assert simplify(parse_expr("[1 + fp + 5]")).format() == "[fp + 6]"
    assert simplify(parse_expr("[fp] - 3")).format() == "[fp] + (-3)"
    if prime is not None:
        assert simplify(parse_expr("fp * (x - 1) / y")).format() == "fp * 3"
        assert simplify(parse_expr("fp * w / x / y / z")).format() == "fp"
    else:
        assert simplify(parse_expr("fp * (x - 1) / y")).format() == "fp * 9 / 3"
        assert simplify(parse_expr("fp * w / x / y / z")).format() == "fp * (-60) / 10 / 3 / (-2)"
    assert simplify(parse_expr("fp * 1")).format() == "fp"
    assert simplify(parse_expr("1 * fp")).format() == "fp"


@pytest.mark.parametrize("prime", [None, 3 * 2**30 + 1])
def test_pow(prime):
    simplifier = ExpressionSimplifier(prime)
    assert simplifier.visit(parse_expr("4 ** 3 ** 2")).format() == "262144"
    if prime is not None:
        # Make sure the exponent is not computed modulo prime (if it were,
        # the result would have been 1).
        assert simplifier.visit(parse_expr("(3 * 2**30 + 4) ** (3 * 2**30 + 1)")).format() == "3"

    with pytest.raises(SimplifierError, match="Power is not supported with a negative exponent"):
        simplifier.visit(parse_expr("2 ** (-1)"))


def test_modulo():
    PRIME = 19
    simplifier = ExpressionSimplifier(PRIME)
    # Check that the range is (-PRIME/2, PRIME/2).
    assert simplifier.visit(parse_expr("-9")).format() == "-9"
    assert simplifier.visit(parse_expr("-10")).format() == "9"
    assert simplifier.visit(parse_expr("9")).format() == "9"
    assert simplifier.visit(parse_expr("10")).format() == "-9"

    # Check value which is bigger than PRIME.
    assert simplifier.visit(parse_expr("20")).format() == "1"

    # Check operators.
    assert simplifier.visit(parse_expr("10 + 10")).format() == "1"
    assert simplifier.visit(parse_expr("10 - 30")).format() == "-1"
    assert simplifier.visit(parse_expr("10 * 10")).format() == "5"
    assert simplifier.visit(parse_expr("2 / 3")).format() == "7"


@pytest.mark.parametrize("prime", [None, 3 * 2**30 + 1])
def test_rotation(prime):
    simplifier = ExpressionSimplifier(prime)
    assert simplifier.visit(parse_expr("(fp + 10) + 1")).format() == "fp + 11"
    assert simplifier.visit(parse_expr("(fp + 10) - 1")).format() == "fp + 9"
    assert simplifier.visit(parse_expr("(fp - 10) + 1")).format() == "fp + (-9)"
    assert simplifier.visit(parse_expr("(fp - 10) - 1")).format() == "fp + (-11)"

    assert simplifier.visit(parse_expr("(10 + fp) - 1")).format() == "fp + 9"
    assert simplifier.visit(parse_expr("10 + (fp - 1)")).format() == "fp + 9"
    assert simplifier.visit(parse_expr("10 + (1 + fp)")).format() == "fp + 11"
    assert simplifier.visit(parse_expr("10 + (1 + fp) + 100")).format() == "fp + 111"
    assert simplifier.visit(parse_expr("10 + (1 + (fp + 100))")).format() == "fp + 111"


@pytest.mark.parametrize("prime", [None, 3 * 2**30 + 1])
def test_division_by_zero(prime):
    simplifier = ExpressionSimplifier(prime)
    with pytest.raises(SimplifierError, match="Division by zero"):
        simplifier.visit(parse_expr("fp / 0"))
    with pytest.raises(SimplifierError, match="Division by zero"):
        simplifier.visit(parse_expr("5 / 0"))
    if prime is not None:
        with pytest.raises(SimplifierError, match="Division by zero"):
            simplifier.visit(parse_expr(f"fp / {prime}"))
