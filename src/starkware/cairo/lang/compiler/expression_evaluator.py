from typing import Dict, Optional

from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt, TypePointer
from starkware.cairo.lang.compiler.ast.expr import ExprConst, ExprDeref, Expression, ExprReg
from starkware.cairo.lang.compiler.error_handling import LocationError
from starkware.cairo.lang.compiler.expression_simplifier import ExpressionSimplifier
from starkware.cairo.lang.compiler.instruction import Register
from starkware.cairo.lang.compiler.type_system_visitor import simplify_type_system


class ExpressionEvaluatorError(LocationError):
    pass


class ExpressionEvaluator(ExpressionSimplifier):
    prime: int

    def __init__(self, prime: int, ap: Optional[int], fp: int, memory: Dict[int, int]):
        super().__init__(prime=prime)
        assert self.prime is not None
        self.ap = ap
        self.fp = fp
        self.memory = memory

    def eval(self, expr: Expression) -> int:
        expr, expr_type = simplify_type_system(expr)
        assert isinstance(expr_type, (TypeFelt, TypePointer)), \
            f"Unable to evaluate expression of type '{expr_type.format()}'."
        res = self.visit(expr)
        assert isinstance(res, ExprConst), f"Unable to evaluate expression '{expr.format()}'."
        assert self.prime is not None
        return res.val % self.prime

    def visit_ExprReg(self, expr: ExprReg) -> ExprConst:
        if expr.reg is Register.AP:
            assert self.ap is not None, 'Cannot substitute ap in the expression.'
            return ExprConst(val=self.ap, location=expr.location)
        elif expr.reg is Register.FP:
            return ExprConst(val=self.fp, location=expr.location)
        else:
            raise NotImplementedError(f'Register of type {expr.reg} is not supported')

    def visit_ExprDeref(self, expr: ExprDeref) -> Expression:
        addr = self.visit(expr.addr)
        if not isinstance(addr, ExprConst):
            return expr
        assert self.prime is not None
        try:
            return ExprConst(val=self.memory[addr.val % self.prime], location=expr.location)
        except Exception as exc:
            raise ExpressionEvaluatorError(str(exc), location=expr.location)
