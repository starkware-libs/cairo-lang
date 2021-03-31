import dataclasses
from typing import Tuple, cast

from starkware.cairo.lang.compiler.ast.cairo_types import (
    CairoType, TypeFelt, TypePointer, TypeStruct, TypeTuple)
from starkware.cairo.lang.compiler.ast.expr import (
    ExprAddressOf, ExprAssignment, ExprCast, ExprConst, ExprDeref, Expression, ExprFutureLabel,
    ExprIdentifier, ExprNeg, ExprOperator, ExprParentheses, ExprPyConst, ExprReg, ExprTuple)
from starkware.cairo.lang.compiler.ast.visitor import Visitor
from starkware.cairo.lang.compiler.expression_transformer import ExpressionTransformer
from starkware.cairo.lang.compiler.type_casts import CairoTypeError, check_cast


def get_expr_addr(expr: Expression):
    if not isinstance(expr, ExprDeref):
        raise CairoTypeError('Expression has no address.', location=expr.location)
    return expr.addr


class TypeSystemVisitor(Visitor):
    """
    Helper class for simplify_type_system().
    """

    def visit_ExprConst(self, expr: ExprConst) -> Tuple[Expression, CairoType]:
        return expr, TypeFelt(location=expr.location)

    def visit_ExprPyConst(self, expr: ExprPyConst) -> Tuple[Expression, CairoType]:
        return expr, TypeFelt(location=expr.location)

    def visit_ExprFutureLabel(self, expr: ExprFutureLabel) -> Tuple[Expression, CairoType]:
        return expr, TypeFelt(location=expr.identifier.location)

    def visit_ExprIdentifier(self, expr: ExprIdentifier) -> Tuple[Expression, CairoType]:
        raise CairoTypeError(
            f'Unexpected unresolved identifier {expr.format()}.', location=expr.location)

    def visit_ExprReg(self, expr: ExprReg) -> Tuple[Expression, CairoType]:
        return expr, TypeFelt(location=expr.location)

    def visit_ExprOperator(self, expr: ExprOperator) -> Tuple[Expression, CairoType]:
        a_expr, a_type = self.visit(expr.a)
        b_expr, b_type = self.visit(expr.b)
        op = expr.op

        result_type: CairoType
        if isinstance(a_type, TypeFelt) and isinstance(b_type, TypeFelt):
            result_type = TypeFelt(location=expr.location)
        elif isinstance(a_type, TypePointer) and isinstance(b_type, TypeFelt) and op in ['+', '-']:
            result_type = a_type
        elif isinstance(a_type, TypeFelt) and isinstance(b_type, TypePointer) and op == '+':
            result_type = b_type
        elif isinstance(a_type, TypePointer) and a_type == b_type and op == '-':
            result_type = TypeFelt(location=expr.location)
        else:
            raise CairoTypeError(
                f"Operator '{op}' is not implemented for types "
                f"'{a_type.format()}' and '{b_type.format()}'.",
                location=expr.location)
        return dataclasses.replace(expr, a=a_expr, b=b_expr), result_type

    def visit_ExprAddressOf(self, expr: ExprAddressOf) -> Tuple[Expression, CairoType]:
        inner_expr, inner_type = self.visit(expr.expr)
        return get_expr_addr(inner_expr), TypePointer(pointee=inner_type)

    def visit_ExprNeg(self, expr: ExprNeg) -> Tuple[Expression, CairoType]:
        inner_expr, inner_type = self.visit(expr.val)
        if not isinstance(inner_type, TypeFelt):
            raise CairoTypeError(
                f"Unary '-' is not supported for type '{inner_type.format()}'.",
                location=expr.location)

        return dataclasses.replace(expr, val=inner_expr), TypeFelt(location=expr.location)

    def visit_ExprParentheses(self, expr: ExprParentheses) -> Tuple[Expression, CairoType]:
        return self.visit(expr.val)

    def visit_ExprDeref(self, expr: ExprDeref) -> Tuple[Expression, CairoType]:
        addr_expr, addr_type = self.visit(expr.addr)
        if isinstance(addr_type, TypeFelt):
            return dataclasses.replace(expr, addr=addr_expr), TypeFelt(location=expr.location)
        elif isinstance(addr_type, TypePointer):
            return dataclasses.replace(expr, addr=addr_expr), addr_type.pointee
        else:
            raise CairoTypeError(
                f"Cannot dereference type '{addr_type.format()}'.",
                location=expr.location)

    def visit_ExprCast(self, expr: ExprCast) -> Tuple[Expression, CairoType]:
        inner_expr, inner_type = self.visit(expr.expr)
        dest_type = expr.dest_type

        if not check_cast(
                src_type=inner_type, dest_type=dest_type, expr=inner_expr,
                cast_type=expr.cast_type):
            raise CairoTypeError(
                f"Cannot cast '{inner_type.format()}' to '{dest_type.format()}'.",
                location=expr.location)

        # Remove the cast() from the expression.
        return inner_expr, dest_type

    def visit_ExprTuple(self, expr: ExprTuple) -> Tuple[Expression, CairoType]:
        args = expr.members.args
        member_expr_types = [self.visit(cast(ExprAssignment, arg).expr) for arg in args]
        result_members = [
            dataclasses.replace(arg, expr=expr) for arg, (expr, _) in zip(args, member_expr_types)]
        result_expr = dataclasses.replace(
            expr, members=dataclasses.replace(expr.members, args=result_members))
        cairo_type = TypeTuple(
            members=[expr_type for expr, expr_type in member_expr_types],
            location=expr.location)
        return result_expr, cairo_type


def simplify_type_system(expr: Expression) -> Tuple[Expression, CairoType]:
    """
    Given an expression returns a type-simplified expression and its Cairo type.
    This includes, checking types in operations and removing casts.
    For example, for the input [cast(fp, T*)] the result will be ([fp], T).
    """
    return TypeSystemVisitor().visit(expr)


def mark_type_resolved(cairo_type: CairoType) -> CairoType:
    """
    Marks the given type as resolved (struct names are absolute).
    This function can be used after parsing a string which is known to contain resolved types.
    """
    if isinstance(cairo_type, TypeFelt):
        return cairo_type
    elif isinstance(cairo_type, TypePointer):
        return dataclasses.replace(cairo_type, pointee=mark_type_resolved(cairo_type.pointee))
    elif isinstance(cairo_type, TypeStruct):
        if cairo_type.is_fully_resolved:
            return cairo_type
        return dataclasses.replace(
            cairo_type,
            is_fully_resolved=True)
    else:
        raise NotImplementedError(f'Type {type(cairo_type).__name__} is not supported.')


def is_type_resolved(cairo_type: CairoType) -> bool:
    """
    Returns true if the type is resolved (struct names are absolute).
    """
    if isinstance(cairo_type, TypeFelt):
        return True
    elif isinstance(cairo_type, TypePointer):
        return is_type_resolved(cairo_type.pointee)
    elif isinstance(cairo_type, TypeStruct):
        return cairo_type.is_fully_resolved
    else:
        raise NotImplementedError(f'Type {type(cairo_type).__name__} is not supported.')


class MarkResolved(ExpressionTransformer):
    def visit_ExprCast(self, expr: ExprCast):
        return dataclasses.replace(
            expr, expr=self.visit(expr.expr), dest_type=mark_type_resolved(expr.dest_type))


def mark_types_in_expr_resolved(expr: Expression):
    """
    Same as mark_type_resolved() except that it operates on all types within an expression.
    """
    return MarkResolved().visit(expr)
