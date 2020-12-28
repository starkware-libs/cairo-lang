from starkware.cairo.lang.compiler.ast.expr import (
    ExprAddressOf, ExprCast, ExprConst, ExprDeref, ExprFutureLabel, ExprNeg, ExprOperator,
    ExprParentheses, ExprPyConst, ExprReg)


class ConstExprChecker:
    """
    A visitor class to check whether an expression contains only numeric and symbolic constants.
    """

    def visit(self, obj):
        return getattr(self, f'visit_{type(obj).__name__}')(obj)

    def visit_ExprConst(self, expr: ExprConst):
        return True

    def visit_ExprPyConst(self, expr: ExprPyConst):
        return True

    def visit_ExprFutureLabel(self, expr: ExprFutureLabel):
        return True

    def visit_ExprReg(self, expr: ExprReg):
        return False

    def visit_ExprOperator(self, expr: ExprOperator):
        return self.visit(expr.a) and self.visit(expr.b)

    def visit_ExprNeg(self, expr: ExprNeg):
        return self.visit(expr.val)

    def visit_ExprParentheses(self, expr: ExprParentheses):
        return self.visit(expr.val)

    def visit_ExprDeref(self, expr: ExprDeref):
        return False

    def visit_ExprAddressOf(self, expr: ExprAddressOf):
        return False

    def visit_ExprCast(self, expr: ExprCast):
        return self.visit(expr)


def is_const_expr(expr):
    """
    Checks whether an expression contains only numeric and symbolic constants.
    """
    return ConstExprChecker().visit(expr)
