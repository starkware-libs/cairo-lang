from starkware.cairo.lang.compiler.ast.expr import (
    ExprAddressOf,
    ExprDot,
    Expression,
    ExprNeg,
    ExprNewOperator,
    ExprOperator,
    ExprParentheses,
    ExprPow,
    ExprSubscript,
)
from starkware.cairo.lang.compiler.expression_transformer import ExpressionTransformer
from starkware.python.expression_string import OperatorPrecedence


def maybe_add_parentheses(expr: Expression, operator_precedence: OperatorPrecedence) -> Expression:
    """
    Adds parentheses if the given operator_precedence is higher than the expression's
    outmost operator precedence.
    """
    if expr.get_outmost_operator_precedence() < operator_precedence:
        return ExprParentheses(val=expr, location=expr.location)
    return expr


class ParenthesesExpressionWrapper(ExpressionTransformer):
    """
    Adds parentheses to expressions according to their arithmetic precedence.
    For example, if a=4*19 and b=20*54 are two expressions, then the lowest operation in both
    is '*'. In this case a + b and a * b do not require parentheses:
        a + b: 4 * 19 + 20 * 54
        a * b: 4 * 19 * 20 * 54
    whereas a**b and a / b do:
        a**b: (4 * 19)**(20 * 54)
        a / b: 4 * 19 / (20 * 54)
    """

    def visit_ExprOperator(self, expr: ExprOperator):
        if expr.op == "+":
            a = maybe_add_parentheses(self.visit(expr.a), OperatorPrecedence.PLUS)
            b = maybe_add_parentheses(self.visit(expr.b), OperatorPrecedence.PLUS)
        elif expr.op == "-":
            a = maybe_add_parentheses(self.visit(expr.a), OperatorPrecedence.PLUS)
            b = maybe_add_parentheses(self.visit(expr.b), OperatorPrecedence.MUL)
        elif expr.op == "*":
            a = maybe_add_parentheses(self.visit(expr.a), OperatorPrecedence.MUL)
            b = maybe_add_parentheses(self.visit(expr.b), OperatorPrecedence.MUL)
        elif expr.op == "/":
            a = maybe_add_parentheses(self.visit(expr.a), OperatorPrecedence.MUL)
            b = maybe_add_parentheses(self.visit(expr.b), OperatorPrecedence.POW)
        else:
            raise NotImplementedError(f"Unexpected operator '{expr.op}'.")

        return ExprOperator(
            a=a,
            op=expr.op,
            b=b,
            notes=expr.notes,
            location=self.location_modifier(expr.location),
        )

    def visit_ExprPow(self, expr: ExprPow):
        # For the two expressions (a ** b) ** c and a ** (b ** c), parentheses will always be added.
        return ExprPow(
            a=maybe_add_parentheses(self.visit(expr.a), OperatorPrecedence.HIGHEST),
            b=maybe_add_parentheses(self.visit(expr.b), OperatorPrecedence.HIGHEST),
            notes=expr.notes,
            location=self.location_modifier(expr.location),
        )

    def visit_ExprNeg(self, expr: ExprNeg):
        return ExprNeg(
            val=maybe_add_parentheses(self.visit(expr.val), OperatorPrecedence.ADDROF),
            location=self.location_modifier(expr.location),
        )

    def visit_ExprSubscript(self, expr: ExprSubscript):
        # If expr is not an atom, add parentheses.
        return ExprSubscript(
            expr=maybe_add_parentheses(self.visit(expr.expr), OperatorPrecedence.HIGHEST),
            offset=self.visit(expr.offset),
            notes=expr.notes,
            location=self.location_modifier(expr.location),
        )

    def visit_ExprDot(self, expr: ExprDot):
        # If expr is not an atom, add parentheses.
        return ExprDot(
            expr=maybe_add_parentheses(self.visit(expr.expr), OperatorPrecedence.HIGHEST),
            # Avoid visiting 'member' with an overridden visit_ExprIdentifier, as it is not a
            # proper identifier.
            member=ExpressionTransformer.visit_ExprIdentifier(self, expr.member),
            location=self.location_modifier(expr.location),
        )

    def visit_ExprAddressOf(self, expr: ExprAddressOf):
        return ExprAddressOf(
            expr=maybe_add_parentheses(self.visit(expr.expr), OperatorPrecedence.ADDROF),
            location=self.location_modifier(expr.location),
        )

    def visit_ExprNewOperator(self, expr: ExprNewOperator):
        return ExprNewOperator(
            expr=maybe_add_parentheses(self.visit(expr.expr), OperatorPrecedence.ADDROF),
            is_typed=expr.is_typed,
            location=self.location_modifier(expr.location),
        )


def parenthesize_expression(expr: Expression):
    parentheses_wrapper = ParenthesesExpressionWrapper()
    return parentheses_wrapper.visit(expr)
