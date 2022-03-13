from typing import Optional

from starkware.cairo.lang.compiler.ast.expr import (
    ArgList,
    ExprAddressOf,
    ExprAssignment,
    ExprCast,
    ExprConst,
    ExprDeref,
    ExprDot,
    Expression,
    ExprFutureLabel,
    ExprHint,
    ExprIdentifier,
    ExprNeg,
    ExprNewOperator,
    ExprOperator,
    ExprParentheses,
    ExprPow,
    ExprReg,
    ExprSubscript,
    ExprTuple,
)
from starkware.cairo.lang.compiler.ast.expr_func_call import ExprFuncCall
from starkware.cairo.lang.compiler.ast.rvalue import RvalueFuncCall
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
        funcname = f"visit_{type(expr).__name__}"
        return getattr(self, funcname)(expr)

    def visit_ExprConst(self, expr: ExprConst):
        return ExprConst(
            val=expr.val, format_str=expr.format_str, location=self.location_modifier(expr.location)
        )

    def visit_ExprHint(self, expr: ExprHint):
        return ExprHint(
            hint_code=expr.hint_code,
            n_prefix_newlines=expr.n_prefix_newlines,
            location=self.location_modifier(expr.location),
        )

    def visit_ExprIdentifier(self, expr: ExprIdentifier):
        return ExprIdentifier(name=expr.name, location=self.location_modifier(expr.location))

    def visit_ExprFutureLabel(self, expr: ExprFutureLabel):
        return ExprFutureLabel(
            identifier=self.visit(expr.identifier),
            is_typed=expr.is_typed,
            location=self.location_modifier(expr.location),
        )

    def visit_ExprReg(self, expr: ExprReg):
        return ExprReg(reg=expr.reg, location=self.location_modifier(expr.location))

    def visit_ExprOperator(self, expr: ExprOperator):
        return ExprOperator(
            a=self.visit(expr.a),
            op=expr.op,
            b=self.visit(expr.b),
            location=self.location_modifier(expr.location),
        )

    def visit_ExprPow(self, expr: ExprPow):
        return ExprPow(
            a=self.visit(expr.a),
            b=self.visit(expr.b),
            location=self.location_modifier(expr.location),
        )

    def visit_ExprNeg(self, expr: ExprNeg):
        return ExprNeg(val=self.visit(expr.val), location=self.location_modifier(expr.location))

    def visit_ExprParentheses(self, expr: ExprParentheses):
        return ExprParentheses(
            val=self.visit(expr.val), location=self.location_modifier(expr.location)
        )

    def visit_ExprDeref(self, expr: ExprDeref):
        return ExprDeref(addr=self.visit(expr.addr), location=self.location_modifier(expr.location))

    def visit_ExprSubscript(self, expr: ExprSubscript):
        return ExprSubscript(
            expr=self.visit(expr.expr),
            offset=self.visit(expr.offset),
            location=self.location_modifier(expr.location),
        )

    def visit_ExprDot(self, expr: ExprDot):
        return ExprDot(
            expr=self.visit(expr.expr),
            # Avoid visiting 'member' with an overridden visit_ExprIdentifier, as it is not a
            # proper identifier.
            member=ExpressionTransformer.visit_ExprIdentifier(self, expr.member),
            location=self.location_modifier(expr.location),
        )

    def visit_ExprAddressOf(self, expr: ExprAddressOf):
        inner_expr = self.visit(expr.expr)
        return ExprAddressOf(expr=inner_expr, location=self.location_modifier(expr.location))

    def visit_ExprCast(self, expr: ExprCast):
        inner_expr = self.visit(expr.expr)
        return ExprCast(
            expr=inner_expr,
            dest_type=expr.dest_type,
            cast_type=expr.cast_type,
            location=self.location_modifier(expr.location),
        )

    def visit_ArgList(self, arg_list: ArgList):
        return ArgList(
            args=[
                ExprAssignment(
                    identifier=item.identifier,
                    expr=self.visit(item.expr),
                    location=self.location_modifier(item.location),
                )
                for item in arg_list.args
            ],
            notes=arg_list.notes,
            has_trailing_comma=arg_list.has_trailing_comma,
            location=self.location_modifier(arg_list.location),
        )

    def visit_ExprTuple(self, expr: ExprTuple):
        return ExprTuple(
            members=self.visit_ArgList(expr.members), location=self.location_modifier(expr.location)
        )

    def visit_RvalueFuncCall(self, rvalue: RvalueFuncCall):
        return RvalueFuncCall(
            func_ident=self.visit(rvalue.func_ident),
            arguments=self.visit_ArgList(rvalue.arguments),
            implicit_arguments=None
            if rvalue.implicit_arguments is None
            else self.visit_ArgList(rvalue.implicit_arguments),
            location=self.location_modifier(rvalue.location),
        )

    def visit_ExprFuncCall(self, expr: ExprFuncCall):
        return ExprFuncCall(
            rvalue=self.visit_RvalueFuncCall(expr.rvalue),
            location=self.location_modifier(expr.location),
        )

    def visit_ExprNewOperator(self, expr: ExprNewOperator):
        return ExprNewOperator(
            expr=self.visit(expr.expr),
            is_typed=expr.is_typed,
            location=self.location_modifier(expr.location),
        )

    def location_modifier(self, location: Optional[Location]) -> Optional[Location]:
        """
        This function can be overridden by subclasses to modify location information.
        """
        return location
