from typing import Generic, Mapping, Optional, TypeVar, cast

from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt, TypePointer
from starkware.cairo.lang.compiler.ast.expr import ExprConst, ExprDeref, Expression, ExprReg
from starkware.cairo.lang.compiler.error_handling import Location, LocationError
from starkware.cairo.lang.compiler.expression_simplifier import ExpressionSimplifier
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.instruction import Register
from starkware.cairo.lang.compiler.type_system_visitor import simplify_type_system

T = TypeVar("T")


class ExpressionEvaluatorError(LocationError):
    pass


class ExpressionEvaluator(Generic[T], ExpressionSimplifier):
    prime: int

    def __init__(
        self,
        prime: int,
        ap: Optional[T],
        fp: T,
        memory: Mapping[T, T],
        identifiers: Optional[IdentifierManager] = None,
    ):
        super().__init__(prime=prime)
        assert self.prime is not None
        self.ap = ap
        self.fp = fp
        self.memory = memory
        self.identifiers = identifiers

    def eval(self, expr: Expression) -> T:
        expr, expr_type = simplify_type_system(expr, identifiers=self.identifiers)
        assert isinstance(
            expr_type, (TypeFelt, TypePointer)
        ), f"Unable to evaluate expression of type '{expr_type.format()}'."
        res = self.visit(expr)
        assert isinstance(res, ExprConst), f"Unable to evaluate expression '{expr.format()}'."
        assert self.prime is not None
        return cast(T, res.val % self.prime)

    def visit_ExprReg(self, expr: ExprReg) -> ExprConst:
        if expr.reg is Register.AP:
            assert self.ap is not None, "Cannot substitute ap in the expression."
            return self.to_expr_const(val=self.ap, location=expr.location)
        elif expr.reg is Register.FP:
            return self.to_expr_const(val=self.fp, location=expr.location)
        else:
            raise NotImplementedError(f"Register of type {expr.reg} is not supported")

    def visit_ExprDeref(self, expr: ExprDeref) -> Expression:
        addr = self.visit(expr.addr)
        if not isinstance(addr, ExprConst):
            return expr
        assert self.prime is not None
        try:
            return self.to_expr_const(
                val=self.memory[cast(T, addr.val % self.prime)], location=expr.location
            )
        except Exception as exc:
            raise ExpressionEvaluatorError(str(exc), location=expr.location)

    def to_expr_const(self, val: T, location: Optional[Location]) -> ExprConst:
        return ExprConst(val=cast(int, val), location=location)
