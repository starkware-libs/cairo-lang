from dataclasses import field
from typing import Callable, ClassVar, List, Optional, Type

import marshmallow
import marshmallow_dataclass

from starkware.cairo.lang.compiler.ast.cairo_types import CairoType, TypePointer
from starkware.cairo.lang.compiler.ast.expr import (
    ExprCast, ExprConst, ExprDeref, Expression, ExprOperator, ExprReg)
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.expression_transformer import ExpressionTransformer
from starkware.cairo.lang.compiler.fields import ExpressionAsStr
from starkware.cairo.lang.compiler.instruction import Register
from starkware.cairo.lang.compiler.preprocessor.reg_tracking import (
    RegChange, RegChangeKnown, RegChangeLike, RegTrackingData)


class FlowTrackingError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.notes: List[str] = []


def create_simple_ref_expr(
        reg: Register, offset: int, cairo_type: CairoType,
        location: Optional[Location]) -> Expression:
    """
    Creates an expression of the form '[cast(reg + offset, cairo_type*)]'.
    """
    return ExprDeref(
        addr=ExprCast(
            expr=ExprOperator(
                a=ExprReg(reg=reg, location=location),
                op='+',
                b=ExprConst(val=offset, location=location),
                location=location),
            dest_type=TypePointer(pointee=cairo_type, location=location),
            location=location),
        location=location)


@marshmallow_dataclass.dataclass
class Reference:
    """
    A reference to a memory address that is defined for a specific location in the program (pc).
    The reference may be evaluated for other locations in the program, as long as its value is well
    defined.
    For example,
      let x = ap   # Defines a reference to ap, that is attached to the following instruction.
      [ap] = 5; ap++
      # Since ap increased, the reference evaluated now should be (ap - 1), rather than ap.
      [ap] = [x] * 2; ap++ # Thus, this instruction will translate to '[ap] = [ap - 1] * 2; ap++'
                           # and will set [ap] to 10.
    """
    pc: int
    value: Expression = field(metadata=dict(marshmallow_field=ExpressionAsStr(required=True)))
    # The value of flow_tracking when this reference was defined.
    ap_tracking_data: RegTrackingData

    # A list of definition sites for the reference.
    # The list may hold more then once location if the reference is defined from the
    # convergence of multiple reference definitions.
    locations: List[Location] = field(default_factory=list, compare=False, metadata=dict(
        marshmallow_field=marshmallow.fields.Field(load_only=True, dump_only=True)))

    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema

    def eval(self, ap_tracking_data: RegTrackingData):
        """
        Evaluates this reference with respect to the given RegTrackingData instance.
        """
        ap_diff = ap_tracking_data - self.ap_tracking_data
        try:
            return translate_ap(self.value, ap_diff)
        except FlowTrackingError as exc:
            if len(self.locations) > 0:
                exc.notes.append('Reference was defined here:')
                for location in self.locations:
                    exc.notes.append(location.topmost_location().to_string_with_content(''))
            raise


def translate_ap(expr, ap_diff: RegChangeLike):
    ap: Optional[Callable]
    ap_diff = RegChange.from_expr(ap_diff)
    if isinstance(ap_diff, RegChangeKnown):
        diff = ap_diff.value

        def ap(location):
            return ExprOperator(
                ExprReg(reg=Register.AP, location=location),
                '-',
                ExprConst(val=diff, location=location),
                location=location)
    else:
        ap = None
    fp = (lambda location: ExprReg(reg=Register.FP, location=location))
    return SubstituteRegisterTransformer(ap, fp).visit(expr)


class SubstituteRegisterTransformer(ExpressionTransformer):
    def __init__(
            self, ap: Optional[Callable[[Optional[Location]], Expression]],
            fp: Callable[[Optional[Location]], Expression]):
        self.ap = ap
        self.fp = fp

    def visit_ExprReg(self, expr: ExprReg):
        if expr.reg is Register.AP:
            if self.ap is None:
                raise FlowTrackingError('Failed to deduce ap.')
            return self.ap(expr.location)
        elif expr.reg is Register.FP:
            return self.fp(expr.location)
        else:
            raise NotImplementedError(f'Register of type {expr.reg} is not supported')
