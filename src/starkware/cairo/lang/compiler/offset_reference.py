import dataclasses
from typing import ClassVar, Type

import marshmallow

from starkware.cairo.lang.compiler.ast.cairo_types import TypePointer, TypeStruct
from starkware.cairo.lang.compiler.ast.expr import (
    ExprAddressOf, ExprCast, ExprConst, ExprDeref, Expression, ExprOperator)
from starkware.cairo.lang.compiler.identifier_definition import (
    DefinitionError, IdentifierDefinition, ReferenceDefinition, StructDefinition)
from starkware.cairo.lang.compiler.identifier_manager import (
    IdentifierManager, MissingIdentifierError)
from starkware.cairo.lang.compiler.preprocessor.flow import (
    FlowTrackingData, FlowTrackingDataActual, ReferenceManager)
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.type_system_visitor import simplify_type_system


@dataclasses.dataclass
class OffsetReferenceDefinition(IdentifierDefinition):
    """
    Represents an expression of the form "x.y.z" where "x" is a typed reference.
    For example, if 'x' is a typed reference with type 'T*', then 'x.y' is translated to
    '[x + T.y]'.
    If 'x.y' is of type 'S*' then 'x.y.z' is translated to '[[x + T.y] + S.z]'.
    In the example, 'x' is the parent reference and 'y.z' is the member path.
    When eval() is called, both 'x' and 'T.y' are evaluated and '[x + T.y]' is returned.
    """
    TYPE: ClassVar[str] = 'offset-reference'
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema

    parent: ReferenceDefinition
    identifiers: IdentifierManager
    member_path: ScopedName

    def eval(
            self, reference_manager: ReferenceManager, flow_tracking_data: FlowTrackingData) -> \
            Expression:
        reference = flow_tracking_data.resolve_reference(
            reference_manager=reference_manager,
            name=self.parent.full_name)
        assert isinstance(flow_tracking_data, FlowTrackingDataActual), \
            'Resolved references can only come from FlowTrackingDataActual.'
        expr, expr_type = simplify_type_system(reference.eval(flow_tracking_data.ap_tracking))
        for member_name in self.member_path.path:
            if isinstance(expr_type, TypeStruct):
                expr_type = expr_type.get_pointer_type()
                # In this case, take the address of the reference value.
                to_addr = lambda expr: ExprAddressOf(expr=expr)
            else:
                to_addr = lambda expr: expr

            if not isinstance(expr_type, TypePointer) or \
                    not isinstance(expr_type.pointee, TypeStruct):
                raise DefinitionError('Member access requires a type of the form Struct*.')

            struct_name = expr_type.pointee.resolved_scope
            struct_def = self.identifiers.get_by_full_name(name=struct_name)
            if struct_def is None:
                raise MissingIdentifierError(struct_name)

            if not isinstance(struct_def, StructDefinition):
                raise DefinitionError(f"""\
Expected '{struct_name}' to be a {StructDefinition.TYPE}. Found: '{struct_def.TYPE}'.""")

            member_definition = struct_def.members.get(member_name)
            if member_definition is None:
                raise DefinitionError(
                    f"'{member_name}' is not a member of '{struct_def.full_name}'.")
            offset_value = member_definition.offset
            expr_type = member_definition.cairo_type

            expr = ExprDeref(addr=ExprOperator(a=to_addr(expr), op='+', b=ExprConst(offset_value)))

        return ExprCast(
            expr=expr,
            dest_type=expr_type,
        )
