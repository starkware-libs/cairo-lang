import operator
from typing import Optional

from starkware.cairo.lang.compiler.ast.expr import (
    ExprConst,
    ExprDeref,
    ExprNeg,
    ExprOperator,
    ExprParentheses,
    ExprPow,
)
from starkware.cairo.lang.compiler.error_handling import LocationError
from starkware.cairo.lang.compiler.expression_transformer import ExpressionTransformer
from starkware.python.math_utils import div_mod

OPERATOR_DICT = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
}


class SimplifierError(LocationError):
    pass


class ExpressionSimplifier(ExpressionTransformer):
    """
    Simplifies expressions by computing constant expressions and substituting variables.
    """

    def __init__(self, prime: Optional[int] = None):
        self.prime = prime

    def visit_ExprConst(self, expr: ExprConst):
        return ExprConst(val=self._to_field_element(expr.val), location=expr.location)

    def visit_ExprOperator(self, expr: ExprOperator):
        a = self.visit(expr.a)
        b = self.visit(expr.b)
        op = expr.op

        if isinstance(b, ExprConst) and op == "/" and b.val == 0:
            raise SimplifierError("Division by zero.", location=b.location)

        if isinstance(a, ExprConst) and isinstance(b, ExprConst):
            val = None
            if op == "/" and self.prime is not None:
                if b.val % self.prime == 0:
                    raise SimplifierError("Division by zero.", location=b.location)
                val = div_mod(a.val, b.val, self.prime)
            if op != "/":
                val = self._to_field_element(OPERATOR_DICT[op](a.val, b.val))
            if val is not None:
                return ExprConst(val, location=expr.location)

        if isinstance(a, ExprConst) and op == "+":
            assert not isinstance(b, ExprConst)
            # Move constant expression to the right. E.g., "5 + fp" -> "fp + 5"
            a, b = b, a

        if isinstance(b, ExprConst) and op == "-":
            # Replace x - y with x + (-y) for constant y.
            op = "+"
            b = ExprConst(val=self._to_field_element(-b.val), location=b.location)

        if isinstance(b, ExprConst) and op == "/" and self.prime is not None:
            # Replace x / y with x * (1/y) for constant y.
            op = "*"
            if b.val % self.prime == 0:
                raise SimplifierError("Division by zero.", location=b.location)
            inv_val = div_mod(1, b.val, self.prime)
            b = ExprConst(val=self._to_field_element(inv_val), location=b.location)

        if isinstance(b, ExprConst) and b.val == 0 and op in ["+", "-"]:
            # Replace x + 0 and x - 0 by x.
            return a

        if isinstance(b, ExprConst) and b.val == 1 and op in ["*", "/"]:
            # Replace x * 1 and x / 1 by x.
            return a

        if isinstance(a, ExprConst) and a.val == 1 and op == "*":
            # Replace 1 * x by x.
            return b

        if (
            isinstance(b, ExprConst)
            and isinstance(a, ExprOperator)
            and ((op == "+" and a.op in ["+", "-"]) or (op == "*" and a.op == "*"))
        ):
            # If the expression is of the form "(a + b) + c" where c is constant, change it to
            # "a + (b + c)", this allows compiling expressions of the form: "[fp + x + y]".

            # Rotate right.
            return self.visit(
                ExprOperator(
                    a=a.a,
                    op=a.op,
                    b=ExprOperator(a=a.b, op=a.op, b=b, location=expr.location),
                    location=expr.location,
                )
            )

        return ExprOperator(a=a, op=op, b=b, location=expr.location)

    def visit_ExprPow(self, expr: ExprPow):
        a = self.visit(expr.a)
        # The exponent must not be computed modulo prime (as b = c (mod prime) does not imply
        # a**b = a**c (mod prime)).
        no_prime_simplifier = type(self)(prime=None)
        b = no_prime_simplifier.visit(expr.b)

        if isinstance(a, ExprConst) and isinstance(b, ExprConst):
            if b.val < 0:
                raise SimplifierError(
                    "Power is not supported with a negative exponent.", location=expr.location
                )
            if self.prime is not None:
                val = pow(a.val, b.val, self.prime)
            else:
                val = a.val ** b.val
            return ExprConst(val=val, location=expr.location)

        return ExprPow(a=a, b=b, location=expr.location)

    def visit_ExprNeg(self, expr: ExprNeg):
        val = self.visit(expr.val)
        if isinstance(val, ExprConst):
            return ExprConst(val=self._to_field_element(-val.val), location=expr.location)
        return ExprNeg(val=val, location=expr.location)

    def visit_ExprParentheses(self, expr: ExprParentheses):
        return self.visit(expr.val)

    def visit_ExprDeref(self, expr: ExprDeref):
        return ExprDeref(addr=self.visit(expr.addr), location=expr.location)

    def _to_field_element(self, val: int) -> int:
        """
        Converts val to an integer in the range (-prime/2, prime/2) which is
        equivalent to val modulo prime.
        """
        return to_field_element(val=val, prime=self.prime)


def to_field_element(val: int, prime: Optional[int]) -> int:
    """
    Converts val to an integer in the range (-prime/2, prime/2) which is
    equivalent to val modulo prime.
    """
    if prime is None:
        return val
    half_prime = prime // 2
    return ((val + half_prime) % prime) - half_prime
