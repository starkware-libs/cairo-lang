from typing import Optional

from starkware.cairo.lang.compiler.ast.expr import (
    ExprAddressOf, ExprCast, ExprConst, ExprDeref, Expression, ExprFutureLabel, ExprIdentifier,
    ExprNeg, ExprOperator, ExprParentheses, ExprPyConst, ExprReg, ExprTuple)
from starkware.cairo.lang.compiler.error_handling import Location, LocationError


class ExpressionTransformerError(LocationError):
    pass


class ExpressionTransformer:
    """
    A base transformer visitor for expressions.
    To implement a transformer, inherit from ExpressionTransformer and override the relevant
    visit_* methods.
    These methods should return an object of type Expression.
    Usually you should call self.visit() on the inner expressions. For example:
      def visit_ExprParentheses(self, expr: ExprParentheses):
          val = self.visit(expr.val)
          # This will remove the parentheses from the expression tree.
          return val
    """

    def visit(self, expr: Expression):
        funcname = f'visit_{type(expr).__name__}'
        return getattr(self, funcname)(expr)

    def visit_ExprConst(self, expr: ExprConst):
        return ExprConst(val=expr.val, location=self.location_modifier(expr.location))

    def visit_ExprPyConst(self, expr: ExprPyConst):
        return ExprPyConst(
            code=expr.code,
            location=self.location_modifier(expr.location))

    def visit_ExprIdentifier(self, expr: ExprIdentifier):
        return ExprIdentifier(name=expr.name, location=self.location_modifier(expr.location))

    def visit_ExprFutureLabel(self, expr: ExprFutureLabel):
        return ExprFutureLabel(self.visit(expr.identifier))

    def visit_ExprReg(self, expr: ExprReg):
        return ExprReg(reg=expr.reg, location=self.location_modifier(expr.location))

    def visit_ExprOperator(self, expr: ExprOperator):
        return ExprOperator(
            a=self.visit(expr.a), op=expr.op, b=self.visit(expr.b),
            location=self.location_modifier(expr.location))

    def visit_ExprNeg(self, expr: ExprNeg):
        return ExprNeg(val=self.visit(expr.val), location=self.location_modifier(expr.location))

    def visit_ExprParentheses(self, expr: ExprParentheses):
        return ExprParentheses(
            val=self.visit(expr.val), location=self.location_modifier(expr.location))

    def visit_ExprDeref(self, expr: ExprDeref):
        return ExprDeref(addr=self.visit(expr.addr), location=self.location_modifier(expr.location))

    def visit_ExprAddressOf(self, expr: ExprAddressOf):
        inner_expr = self.visit(expr.expr)
        return ExprAddressOf(
            expr=inner_expr, location=self.location_modifier(expr.location))

    def visit_ExprCast(self, expr: ExprCast):
        inner_expr = self.visit(expr.expr)
        return ExprCast(
            expr=inner_expr,
            dest_type=expr.dest_type,
            location=self.location_modifier(expr.location))

    def visit_ExprTuple(self, expr: ExprTuple):
        raise ExpressionTransformerError('Tuples are not supported yet.', location=expr.location)

    def location_modifier(self, location: Optional[Location]) -> Optional[Location]:
        """
        This function can be overridden by subclasses to modify location information.
        """
        return location
