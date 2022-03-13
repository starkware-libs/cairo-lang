from starkware.cairo.lang.compiler.ast.expr import (
    ExprAddressOf,
    ExprDeref,
    ExprDot,
    ExprNeg,
    ExprNewOperator,
    ExprOperator,
    ExprParentheses,
    ExprSubscript,
)


def remove_parentheses(expr):
    """
    Removes the parentheses (ExprParentheses) from an arithmetic expression.
    """
    if isinstance(expr, ExprParentheses):
        return remove_parentheses(expr.val)
    if isinstance(expr, ExprOperator):
        return ExprOperator(a=remove_parentheses(expr.a), op=expr.op, b=remove_parentheses(expr.b))
    if isinstance(expr, ExprAddressOf):
        return ExprAddressOf(expr=remove_parentheses(expr.expr))
    if isinstance(expr, ExprNeg):
        return ExprNeg(val=remove_parentheses(expr.val))
    if isinstance(expr, ExprDeref):
        return ExprDeref(addr=remove_parentheses(expr.addr))
    if isinstance(expr, ExprDot):
        return ExprDot(expr=remove_parentheses(expr.expr), member=expr.member)
    if isinstance(expr, ExprNewOperator):
        return ExprNewOperator(expr=remove_parentheses(expr.expr), is_typed=expr.is_typed)
    if isinstance(expr, ExprSubscript):
        return ExprSubscript(
            expr=remove_parentheses(expr.expr), offset=remove_parentheses(expr.offset)
        )
    return expr
