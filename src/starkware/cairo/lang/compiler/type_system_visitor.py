import dataclasses
from typing import Optional, Tuple

from starkware.cairo.lang.compiler.ast.cairo_types import (
    CairoType,
    TypeCodeoffset,
    TypeFelt,
    TypePointer,
    TypeStruct,
    TypeTuple,
)
from starkware.cairo.lang.compiler.ast.expr import (
    ExprAddressOf,
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
    ExprReg,
    ExprSubscript,
    ExprTuple,
)
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.expression_simplifier import ExpressionSimplifier
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.identifier_utils import get_struct_definition
from starkware.cairo.lang.compiler.preprocessor.identifier_aware_visitor import (
    IdentifierAwareVisitor,
)
from starkware.cairo.lang.compiler.type_casts import CairoTypeError, check_cast
from starkware.python.utils import safe_zip


def get_expr_addr(expr: Expression):
    if not isinstance(expr, ExprDeref):
        raise CairoTypeError("Expression has no address.", location=expr.location)
    return expr.addr


class TypeSystemVisitor(IdentifierAwareVisitor):
    """
    Helper class for simplify_type_system().
    """

    def __init__(self, identifiers: Optional[IdentifierManager] = None):
        super().__init__(identifiers)
        self.identifiers_initalized = identifiers is not None

    def visit_ExprConst(self, expr: ExprConst) -> Tuple[ExprConst, TypeFelt]:
        return expr, TypeFelt(location=expr.location)

    def visit_ExprHint(self, expr: ExprHint) -> Tuple[ExprHint, TypeFelt]:
        return expr, TypeFelt(location=expr.location)

    def visit_ExprFutureLabel(self, expr: ExprFutureLabel) -> Tuple[ExprFutureLabel, CairoType]:
        type_cls = TypeCodeoffset if expr.is_typed else TypeFelt
        return (dataclasses.replace(expr, is_typed=False), type_cls(location=expr.location))

    def visit_ExprIdentifier(self, expr: ExprIdentifier) -> Tuple[Expression, CairoType]:
        raise CairoTypeError(
            f"Identifier '{expr.format()}' is not allowed in this context.", location=expr.location
        )

    def visit_ExprReg(self, expr: ExprReg) -> Tuple[ExprReg, TypeFelt]:
        return expr, TypeFelt(location=expr.location)

    def visit_ExprOperator(self, expr: ExprOperator) -> Tuple[ExprOperator, CairoType]:
        a_expr, a_type = self.visit(expr.a)
        b_expr, b_type = self.visit(expr.b)
        op = expr.op

        result_type: CairoType
        if isinstance(a_type, TypeFelt) and isinstance(b_type, TypeFelt):
            result_type = TypeFelt(location=expr.location)
        elif isinstance(a_type, TypePointer) and isinstance(b_type, TypeFelt) and op in ["+", "-"]:
            result_type = a_type
        elif isinstance(a_type, TypeFelt) and isinstance(b_type, TypePointer) and op == "+":
            result_type = b_type
        elif isinstance(a_type, (TypePointer, TypeCodeoffset)) and a_type == b_type and op == "-":
            result_type = TypeFelt(location=expr.location)
        else:
            raise CairoTypeError(
                f"Operator '{op}' is not implemented for types "
                f"'{a_type.format()}' and '{b_type.format()}'.",
                location=expr.location,
            )
        return dataclasses.replace(expr, a=a_expr, b=b_expr), result_type

    def visit_ExprPow(self, expr: ExprOperator) -> Tuple[ExprOperator, CairoType]:
        a_expr, a_type = self.visit(expr.a)
        b_expr, b_type = self.visit(expr.b)

        if not isinstance(a_type, TypeFelt) and isinstance(b_type, TypeFelt):
            raise CairoTypeError(
                f"Operator '**' is not implemented for types "
                f"'{a_type.format()}' and '{b_type.format()}'.",
                location=expr.location,
            )
        return dataclasses.replace(expr, a=a_expr, b=b_expr), TypeFelt(location=expr.location)

    def visit_ExprAddressOf(self, expr: ExprAddressOf) -> Tuple[Expression, TypePointer]:
        inner_expr, inner_type = self.visit(expr.expr)
        return get_expr_addr(inner_expr), TypePointer(pointee=inner_type)

    def visit_ExprNeg(self, expr: ExprNeg) -> Tuple[ExprNeg, TypeFelt]:
        inner_expr, inner_type = self.visit(expr.val)
        if not isinstance(inner_type, TypeFelt):
            raise CairoTypeError(
                f"Unary '-' is not supported for type '{inner_type.format()}'.",
                location=expr.location,
            )

        return dataclasses.replace(expr, val=inner_expr), TypeFelt(location=expr.location)

    def visit_ExprParentheses(self, expr: ExprParentheses) -> Tuple[Expression, CairoType]:
        return self.visit(expr.val)

    def visit_ExprDeref(self, expr: ExprDeref) -> Tuple[ExprDeref, CairoType]:
        addr_expr, addr_type = self.visit(expr.addr)
        if isinstance(addr_type, TypeFelt):
            return dataclasses.replace(expr, addr=addr_expr), TypeFelt(location=expr.location)
        elif isinstance(addr_type, TypePointer):
            return dataclasses.replace(expr, addr=addr_expr), addr_type.pointee
        else:
            raise CairoTypeError(
                f"Cannot dereference type '{addr_type.format()}'.", location=expr.location
            )

    @staticmethod
    def verify_offset_is_felt(offset_type: CairoType, offset_location: Location):
        if not isinstance(offset_type, TypeFelt):
            raise CairoTypeError(
                "Cannot apply subscript-operator with offset of non-felt type "
                f"'{offset_type.format()}'.",
                location=offset_location,
            )

    def visit_ExprSubscript(self, expr: ExprSubscript) -> Tuple[Expression, CairoType]:
        inner_expr, inner_type = self.visit(expr.expr)
        offset_expr, offset_type = self.visit(expr.offset)

        if isinstance(inner_type, TypeTuple):
            self.verify_offset_is_felt(offset_type, offset_expr.location)
            offset_expr = ExpressionSimplifier().visit(offset_expr)
            if not isinstance(offset_expr, ExprConst):
                raise CairoTypeError(
                    "Subscript-operator for tuples supports only constant offsets, found "
                    f"'{type(offset_expr).__name__}'.",
                    location=offset_expr.location,
                )
            offset_value = offset_expr.val

            tuple_len = len(inner_type.members)
            if not 0 <= offset_value < tuple_len:
                raise CairoTypeError(
                    f"Tuple index {offset_value} is out of range [0, {tuple_len}).",
                    location=expr.location,
                )

            item_type = inner_type.members[offset_value].typ

            if isinstance(inner_expr, ExprTuple):
                assert len(inner_expr.members.args) == tuple_len
                return (
                    # Take the inner item, but keep the original expression's location.
                    dataclasses.replace(
                        inner_expr.members.args[offset_value].expr, location=expr.location
                    ),
                    item_type,
                )
            elif isinstance(inner_expr, ExprDeref):
                # Handles pointers cast as tuples*, e.g. `[cast(ap, (felt, felt)*][0]`.
                addr = inner_expr.addr
                offset_in_felts = ExprConst(
                    val=sum(map(self.get_size, inner_type.types[:offset_value])),
                    location=offset_expr.location,
                )
                addr_with_offset = ExprOperator(
                    a=addr, op="+", b=offset_in_felts, location=expr.location
                )
                return ExprDeref(addr=addr_with_offset, location=expr.location), item_type
            else:
                raise CairoTypeError(
                    "Unexpected expression typed as TypeTuple. Expected ExprTuple or ExprDeref, "
                    f"found '{type(inner_expr).__name__}'.",
                    location=expr.location,
                )
        elif isinstance(inner_type, TypePointer):
            self.verify_offset_is_felt(offset_type, offset_expr.location)
            try:
                # If pointed type is struct, get_size could throw IdentifierErrors. We catch and
                # convert them to CairoTypeErrors.
                element_size = self.get_size(inner_type.pointee)
            except Exception as exc:
                raise CairoTypeError(str(exc), location=expr.location)

            element_size_expr = ExprConst(val=element_size, location=expr.location)
            modified_offset_expr = ExprOperator(
                a=offset_expr, op="*", b=element_size_expr, location=expr.location
            )
            simplified_expr = ExprDeref(
                addr=ExprOperator(
                    a=inner_expr, op="+", b=modified_offset_expr, location=expr.location
                ),
                location=expr.location,
            )

            return simplified_expr, inner_type.pointee
        else:
            raise CairoTypeError(
                "Cannot apply subscript-operator to non-pointer, non-tuple type "
                f"'{inner_type.format()}'.",
                location=expr.location,
            )

    def verify_identifier_manager_initialized(self, location: Optional[Location]):
        if self.identifiers_initalized:
            return
        raise CairoTypeError(
            "Identifiers must be initialized for type-simplification of dot-operator "
            "expressions.",
            location=location,
        )

    def visit_ExprDot(self, expr: ExprDot) -> Tuple[ExprDeref, CairoType]:
        self.verify_identifier_manager_initialized(location=expr.location)

        inner_expr, inner_type = self.visit(expr.expr)
        if isinstance(inner_type, TypePointer):
            if not isinstance(inner_type.pointee, (TypeStruct, TypeTuple)):
                raise CairoTypeError(
                    f"Cannot apply dot-operator to pointer-to-non-struct type "
                    f"'{inner_type.format()}'.",
                    location=expr.location,
                )
            # Allow for . as ->, once.
            inner_type = inner_type.pointee
        elif isinstance(inner_type, (TypeStruct, TypeTuple)):
            if isinstance(inner_expr, ExprTuple):
                raise CairoTypeError(
                    "Accessing struct/tuple members for r-value structs is not supported yet.",
                    location=expr.location,
                )
            # Get the address, to evaluate . as ->.
            inner_expr = get_expr_addr(inner_expr)
        else:
            raise CairoTypeError(
                f"Cannot apply dot-operator to non-struct type '{inner_type.format()}'.",
                location=expr.location,
            )

        if isinstance(inner_type, TypeStruct):
            try:
                struct_def = get_struct_definition(
                    struct_name=inner_type.resolved_scope, identifier_manager=self.identifiers
                )
            except Exception as exc:
                raise CairoTypeError(str(exc), location=expr.location)

            if expr.member.name not in struct_def.members:
                raise CairoTypeError(
                    f"Member '{expr.member.name}' does not appear in definition of struct "
                    f"'{inner_type.format()}'.",
                    location=expr.location,
                )

            member_definition = struct_def.members[expr.member.name]
            member_type = member_definition.cairo_type
            member_offset = member_definition.offset
        else:
            if isinstance(inner_type, TypeTuple) and not inner_type.is_named:
                raise CairoTypeError(
                    f"Cannot apply dot-operator to unnamed tuple type '{inner_type.format()}'.",
                    location=expr.location,
                )

            assert isinstance(inner_type, TypeTuple)
            member_offset = 0
            for i, member in enumerate(inner_type.members):
                if member.name == expr.member.name:
                    member_type = member.typ
                    break

                member_offset += self.get_size(member.typ)
            else:
                raise CairoTypeError(
                    f"Member '{expr.member.name}' does not appear in definition of tuple type "
                    f"'{inner_type.format()}'.",
                    location=expr.location,
                )

        if member_offset == 0:
            simplified_expr = ExprDeref(addr=inner_expr, location=expr.location)
        else:
            mem_offset_expr = ExprConst(val=member_offset, location=expr.location)
            simplified_expr = ExprDeref(
                addr=ExprOperator(a=inner_expr, op="+", b=mem_offset_expr, location=expr.location),
                location=expr.location,
            )

        return simplified_expr, member_type

    def visit_ExprCast(self, expr: ExprCast) -> Tuple[Expression, CairoType]:
        inner_expr, src_type = self.visit(expr.expr)
        dest_type = expr.dest_type

        if not check_cast(
            src_type=src_type,
            dest_type=dest_type,
            identifier_manager=self.identifiers,
            cast_type=expr.cast_type,
            location=expr.location,
            expr=inner_expr,
        ):
            raise CairoTypeError(
                f"Cannot cast '{src_type.format()}' to '{dest_type.format()}'.",
                location=expr.location,
            )

        # Remove the cast() from the expression, but keep its original location.
        return dataclasses.replace(inner_expr, location=expr.location), dest_type

    def visit_ExprTuple(self, expr: ExprTuple) -> Tuple[ExprTuple, TypeTuple]:
        args = expr.members.args
        # Call visit on each member to obtain a list of the form (expr, type).
        member_expr_types = [self.visit(arg.expr) for arg in args]
        # Replace each tuple item with the corresponding type-simplified expression from
        # member_expr_types, and remove the name (as the name is part of the type rather than
        # the type-simplified expression).
        result_members = [
            dataclasses.replace(arg, identifier=None, expr=expr)
            for arg, (expr, _) in zip(args, member_expr_types)
        ]
        result_expr = dataclasses.replace(
            expr, members=dataclasses.replace(expr.members, args=result_members)
        )
        # Construct the resulting type. Include the names of the tuple items in the returned
        # named tuple type.
        cairo_type = TypeTuple.from_members(
            members=[
                TypeTuple.Item(
                    name=(None if arg.identifier is None else arg.identifier.name),
                    typ=expr_type,
                    location=arg.location,
                )
                for arg, (expr, expr_type) in safe_zip(args, member_expr_types)
            ],
            location=expr.location,
        )
        return result_expr, cairo_type

    def visit_ExprNewOperator(self, expr: ExprNewOperator) -> Tuple[ExprNewOperator, CairoType]:
        inner_expr, inner_expr_type = self.visit(expr.expr)
        expr_type = (
            TypePointer(pointee=inner_expr_type, location=expr.location)
            if expr.is_typed
            else TypeFelt(location=expr.location)
        )
        return ExprNewOperator(expr=inner_expr, is_typed=False, location=expr.location), expr_type


def simplify_type_system(
    expr: Expression, identifiers: Optional[IdentifierManager] = None
) -> Tuple[Expression, CairoType]:
    """
    Given an expression returns a type-simplified expression and its Cairo type.
    This includes checking types in operations, removing casts, and expanding dot and subscript
    operators. For example:
      - expr=[cast(fp, T*)] will be transformed into ([fp], T);
      - If T is a struct type with member x of type S at offset 2, then expr=[cast(fp, T*)].x will
        be transformed into ([[fp] + 2], S);
      - If T is a struct of size 3, then expr=cast(fp, T*)[5] will be transformed into
        ([fp + 5 * 3], T).
    In the second and third examples, the defintion of struct T is looked up, and must be present,
    in the IdentifierManager 'identifiers'.
    """
    return TypeSystemVisitor(identifiers=identifiers).visit(expr)
