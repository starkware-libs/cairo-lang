from typing import Callable, List, Optional, Union

from starkware.cairo.lang.compiler.ast.cairo_types import CairoType, TypeStruct
from starkware.cairo.lang.compiler.ast.expr import (
    ExprCast,
    ExprConst,
    Expression,
    ExprFutureLabel,
    ExprIdentifier,
    ExprPow,
    ExprTuple,
)
from starkware.cairo.lang.compiler.ast.expr_func_call import ExprFuncCall
from starkware.cairo.lang.compiler.ast.rvalue import RvalueFuncCall
from starkware.cairo.lang.compiler.expression_transformer import ExpressionTransformer
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.type_casts import CairoTypeError

GetIdentifierCallback = Callable[[ExprIdentifier], Union[int, Expression]]
ResolveTypeCallback = Optional[Callable[[CairoType], CairoType]]
GetStructMembersCallback = Optional[Callable[[TypeStruct], List[str]]]


class SubstituteIdentifiers(ExpressionTransformer):
    def __init__(
        self,
        get_identifier_callback: GetIdentifierCallback,
        resolve_type_callback: ResolveTypeCallback = None,
        get_struct_members_callback: GetStructMembersCallback = None,
    ):
        super().__init__()
        self.get_identifier_callback = get_identifier_callback
        self.resolve_type_callback = (
            resolve_type_callback
            if resolve_type_callback is not None
            else (lambda cairo_type: cairo_type)
        )
        self.get_struct_members_callback = get_struct_members_callback

    def visit_ExprIdentifier(self, expr: ExprIdentifier) -> Expression:
        val = self.get_identifier_callback(expr)
        if isinstance(val, int):
            return ExprConst(val, location=expr.location)
        return val

    def visit_ExprCast(self, expr: ExprCast):
        return ExprCast(
            expr=self.visit(expr.expr),
            dest_type=self.resolve_type_callback(expr.dest_type),
            cast_type=expr.cast_type,
            notes=expr.notes,
            location=expr.location,
        )

    def visit_ExprPow(self, expr: ExprPow):
        # Same as super().visit_ExprPow, except that we don't visit expr.b.
        # The reason is that the exponent shouldn't be taken modulo PRIME, so we don't allow
        # using identifiers in the exponent.
        return ExprPow(
            a=self.visit(expr.a), b=expr.b, location=self.location_modifier(expr.location)
        )

    def visit_RvalueFuncCall(self, rvalue: RvalueFuncCall):
        # Same as super().visit_RvalueFuncCall, except that we don't visit rvalue.func_ident.
        # The reason is that function names do not constitute as expressions in Cairo,
        # and visiting them in this visitor results in an error.
        return RvalueFuncCall(
            func_ident=rvalue.func_ident,
            arguments=self.visit_ArgList(rvalue.arguments),
            implicit_arguments=None
            if rvalue.implicit_arguments is None
            else self.visit_ArgList(rvalue.implicit_arguments),
            location=rvalue.location,
        )

    def visit_ExprFuncCall(self, expr: ExprFuncCall):
        # Convert ExprFuncCall to ExprCast.
        rvalue = expr.rvalue
        if rvalue.implicit_arguments is not None:
            raise CairoTypeError(
                "Implicit arguments cannot be used with struct constructors.",
                location=rvalue.implicit_arguments.location,
            )

        struct_type = self.resolve_type_callback(
            TypeStruct(
                scope=ScopedName.from_string(rvalue.func_ident.name),
                is_fully_resolved=False,
                location=expr.location,
            )
        )

        # Verify named arguments in struct constructor.
        if self.get_struct_members_callback is not None:
            assert isinstance(struct_type, TypeStruct)
            struct_members = self.get_struct_members_callback(struct_type)
            # Note that it's OK if len(struct_members) != len(rvalue.arguments.args) as
            # length compatibility of cast is checked later on.
            for member, expr_assignment in zip(struct_members, rvalue.arguments.args):
                identifier = expr_assignment.identifier
                if identifier is None:
                    continue

                call_member = identifier.name
                if call_member != member:
                    raise CairoTypeError(
                        f"Argument name mismatch for '{struct_type.format()}': "
                        f"expected '{member}', found '{call_member}'.",
                        location=identifier.location,
                    )

        return self.visit(
            ExprCast(
                expr=ExprTuple(rvalue.arguments, location=expr.location),
                dest_type=struct_type,
                location=expr.location,
            )
        )

    def visit_ExprFutureLabel(self, expr: ExprFutureLabel):
        res = self.visit(expr.identifier)
        if isinstance(res, ExprFutureLabel):
            # If expr.identifier remains unresolved, return the original expression to keep track
            # of expr.is_typed.
            return expr
        return res


def substitute_identifiers(
    expr: Expression,
    get_identifier_callback: GetIdentifierCallback,
    resolve_type_callback: ResolveTypeCallback = None,
    get_struct_members_callback: GetStructMembersCallback = None,
) -> Expression:
    """
    Replaces identifiers by other expressions according to the given callback.
    """
    return SubstituteIdentifiers(
        get_identifier_callback=get_identifier_callback,
        resolve_type_callback=resolve_type_callback,
        get_struct_members_callback=get_struct_members_callback,
    ).visit(expr)
