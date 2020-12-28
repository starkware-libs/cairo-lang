from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import List, Optional, Tuple, Union

from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt
from starkware.cairo.lang.compiler.ast.code_elements import (
    CodeElement, CodeElementTemporaryVariable)
from starkware.cairo.lang.compiler.ast.expr import (
    ExprConst, ExprDeref, Expression, ExprIdentifier, ExprNeg, ExprOperator, ExprReg)
from starkware.cairo.lang.compiler.ast.types import TypedIdentifier
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.instruction import Register
from starkware.cairo.lang.compiler.instruction_builder import (
    InstructionBuilderError, _parse_offset, _parse_register_offset)
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.references import translate_ap


class SimplicityLevel(Enum):
    # An expression of the form [reg + offset].
    DEREF = 0
    # An expression of the form DEREF or [reg + offset] + offset.
    DEREF_OFFSET = auto()
    # An expression of the form DEREF or a constant.
    DEREF_CONST = auto()
    # An expression of the form DEREF_CONST or with one operation.
    OPERATION = auto()


class CompoundExpressionContext(ABC):
    @abstractmethod
    def new_tempvar_name(self) -> str:
        """
        Allocates a new tempvar name.
        """

    @abstractmethod
    def get_fp_val(self, location: Optional[Location]) -> Expression:
        """
        Returns an expression with the current value of fp.
        Usually, this should resolve the expression "__fp__".
        """


def is_simple_deref(expr: Expression):
    """
    Returns True if expr is of the form [reg + offset].
    """
    if not isinstance(expr, ExprDeref):
        return False
    try:
        # Try to write expr.addr as "reg + off".
        _parse_register_offset(expr.addr)
        return True
    except InstructionBuilderError:
        return False


class CompoundExpressionVisitor:
    """
    Helper class for process_compound_expressions().
    Don't use this class directly, use process_compound_expressions() instead.
    Rewrites expressions by adding temporary variables (tempvar).
    """

    def __init__(self, context: CompoundExpressionContext):
        """
        Constructs a CompoundExpressionVisitor.
        """
        self.code_elements: List[CodeElement] = []
        self.context = context
        # Number of variables created so far.
        self.n_vars: int = 0

    def rewrite(self, expr: Expression, sim: SimplicityLevel):
        """
        Rewrites the given expression in the given simplicity level.
        For example, the expression "5" will be left unchanged for DEREF_CONST and OPERATION, but
        will be replaced by a variable for DEREF. The expression "[ap] + 6" will be left unchanged
        for OPERATION but will be replaced by a variable for DEREF and DEREF_CONST.
        """
        funcname = f'rewrite_{type(expr).__name__}'
        return getattr(self, funcname)(expr, sim)

    def rewrite_ExprConst(self, expr: ExprConst, sim: SimplicityLevel):
        if sim in [SimplicityLevel.DEREF_CONST, SimplicityLevel.OPERATION]:
            return expr
        return self.wrap(expr)

    def rewrite_ExprReg(self, expr: ExprReg, sim: SimplicityLevel):
        if expr.reg is Register.AP:
            raise PreprocessorError(
                'ap may only be used in an expression of the form [ap + <const>].',
                location=expr.location)
        elif expr.reg is Register.FP:
            return self.rewrite(expr=self.context.get_fp_val(expr.location), sim=sim)
        else:
            raise NotImplementedError(f'Unknown register {expr.reg}.')

    def rewrite_ExprOperator(self, expr: ExprOperator, sim: SimplicityLevel):
        expr = ExprOperator(
            a=self.rewrite(expr.a, SimplicityLevel.DEREF),
            op=expr.op,
            b=self.rewrite(expr.b, SimplicityLevel.DEREF_CONST),
            location=expr.location)

        if sim is SimplicityLevel.OPERATION:
            return expr

        if sim is SimplicityLevel.DEREF_OFFSET:
            # Check if it's of the form [reg + offset] + offset.
            try:
                inner_expr, offset = _parse_offset(expr)
            except InstructionBuilderError:
                pass
            else:
                assert inner_expr == expr.a
                return expr

        return self.wrap(expr)

    def rewrite_ExprNeg(self, expr: ExprNeg, sim: SimplicityLevel):
        # Treat "-val" as "val * (-1)".
        return self.rewrite(ExprOperator(
            a=expr.val,
            op='*',
            b=ExprConst(val=-1, location=expr.location),
            location=expr.location), sim)

    def rewrite_ExprDeref(self, expr: ExprDeref, sim: SimplicityLevel):
        if is_simple_deref(expr):
            # This is already a simple expression, just return it.
            return expr

        expr = ExprDeref(
            addr=self.rewrite(expr.addr, SimplicityLevel.DEREF_OFFSET), location=expr.location)
        return expr if sim is SimplicityLevel.OPERATION else self.wrap(expr)

    def wrap(self, expr: Expression) -> ExprIdentifier:
        identifier = ExprIdentifier(name=self.context.new_tempvar_name(), location=expr.location)

        expr = self.translate_ap(expr)
        self.n_vars += 1

        self.code_elements.append(CodeElementTemporaryVariable(
            typed_identifier=TypedIdentifier(
                identifier=identifier, expr_type=TypeFelt(location=expr.location)),
            expr=expr,
            location=expr.location))
        return identifier

    def translate_ap(self, expr):
        return translate_ap(expr, self.n_vars)


def process_compound_expressions(
        exprs: List[Expression], simplicity: Union[SimplicityLevel, List[SimplicityLevel]],
        context: CompoundExpressionContext) \
        -> Tuple[List[CodeElement], List[Expression], Optional[Expression]]:
    """
    Rewrites the given list of expressions, by adding temporary variables, in the required
    simiplicity levels.
    For example, in SimplicityLevel.OPERATION, the expression "[[ap + 3]]" will be left unchanged,
    and "[ap] + [ap] + [ap]" will be replaced by "__temp0 + [ap]" where __temp0 is a new temporary
    variable.

    'simplicity' may be one SimplicityLevel for all the expressions or a list of SimplicityLevel
    for each expression separately.
    Returns a list of code elements with the temporary variables, the list of simplified expression,
    and the first expression from exprs which required simplification (or None if all the
    expressions were already at the required simplicity level).
    """
    if isinstance(simplicity, SimplicityLevel):
        simplicity = [simplicity] * len(exprs)
    assert isinstance(simplicity, list) and len(simplicity) == len(exprs)

    visitor = CompoundExpressionVisitor(context=context)
    # First, visit all of the expressions.
    simplified_exprs = []
    first_compound_expr = None
    for expr, sim in zip(exprs, simplicity):
        simplified_exprs.append(visitor.rewrite(expr, sim))
        # Check if this is the first compound expression.
        if len(visitor.code_elements) > 0 and first_compound_expr is None:
            first_compound_expr = expr

    # Second, translate ap according to the total number of instructions.
    simplified_exprs = [visitor.translate_ap(expr) for expr in simplified_exprs]
    return visitor.code_elements, simplified_exprs, first_compound_expr


def process_compound_assert(
        expr_a: Expression, expr_b: Expression, context: CompoundExpressionContext):
    """
    A version of process_compound_expressions() for assert instructions. Takes two expressions
    and returns them simplified to levels [DEREF, OPERATION] or [OPERATION, DEREF],
    so that the following will hold:
    1. If expr_a = expr_b or expr_b = expr_a is already a valid Cairo instruction, it will not be
       modified.
    2. If expr_a is assignable (that is, a dereference), then the assignment is treated as
       right-to-left: the right-hand side is simplified to DEREF to avoid unnecessary
       computations on the left-hand side (this allows the assignment without hints).
    """

    if is_simple_deref(expr_a):
        # In this case, the left-hand side does not require any simplification, so there is room
        # for complexity on the right-hand side.
        simplicity = [SimplicityLevel.DEREF, SimplicityLevel.OPERATION]
    else:
        # Left-hand side is already too complicated for DEREF.
        simplicity = [SimplicityLevel.OPERATION, SimplicityLevel.DEREF]

    code_elements, exprs, _ = process_compound_expressions(
        exprs=[expr_a, expr_b], simplicity=simplicity, context=context)
    return code_elements, exprs
