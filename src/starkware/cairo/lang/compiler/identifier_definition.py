import dataclasses
from abc import ABC, abstractmethod
from dataclasses import field
from typing import ClassVar, Dict, List, Type

import marshmallow
import marshmallow_dataclass
from marshmallow_oneofschema import OneOfSchema

from starkware.cairo.lang.compiler.ast.cairo_types import CairoType, TypePointer, TypeStruct
from starkware.cairo.lang.compiler.ast.expr import (
    ExprAddressOf, ExprCast, ExprConst, ExprDeref, Expression, ExprOperator)
from starkware.cairo.lang.compiler.constants import SIZE_CONSTANT
from starkware.cairo.lang.compiler.fields import CairoTypeAsStr
from starkware.cairo.lang.compiler.preprocessor.flow import (
    FlowTrackingData, FlowTrackingDataActual, ReferenceManager)
from starkware.cairo.lang.compiler.references import Reference
from starkware.cairo.lang.compiler.scoped_name import ScopedName, ScopedNameAsStr
from starkware.cairo.lang.compiler.type_system_visitor import simplify_type_system


class DefinitionError(Exception):
    pass


class IdentifierDefinition(ABC):
    @property  # type: ignore
    @abstractmethod
    def TYPE(self):
        pass


@dataclasses.dataclass
class FutureIdentifierDefinition(IdentifierDefinition):
    """
    Represents an identifier that will be defined later in the code.
    """

    TYPE: ClassVar[str] = 'future'
    identifier_type: type


@marshmallow_dataclass.dataclass
class AliasDefinition(IdentifierDefinition):
    TYPE: ClassVar[str] = 'alias'
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema

    destination: ScopedName = field(metadata=dict(marshmallow_field=ScopedNameAsStr()))


@marshmallow_dataclass.dataclass
class ConstDefinition(IdentifierDefinition):
    TYPE: ClassVar[str] = 'const'
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema

    value: int


@marshmallow_dataclass.dataclass
class MemberDefinition(IdentifierDefinition):
    TYPE: ClassVar[str] = 'member'
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema

    offset: int
    cairo_type: CairoType = field(
        metadata=dict(marshmallow_field=CairoTypeAsStr(required=True)))


@marshmallow_dataclass.dataclass
class LabelDefinition(IdentifierDefinition):
    TYPE: ClassVar[str] = 'label'
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema

    pc: int


@marshmallow_dataclass.dataclass
class ReferenceDefinition(IdentifierDefinition):
    TYPE: ClassVar[str] = 'reference'
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema

    full_name: ScopedName = field(metadata=dict(marshmallow_field=ScopedNameAsStr()))
    references: List[Reference]

    def eval(
            self, reference_manager: ReferenceManager, flow_tracking_data: FlowTrackingData) -> \
            Expression:
        reference = flow_tracking_data.resolve_reference(
            reference_manager=reference_manager,
            name=self.full_name)
        assert isinstance(flow_tracking_data, FlowTrackingDataActual), \
            'Resolved references can only come from FlowTrackingDataActual.'
        expr = reference.eval(flow_tracking_data.ap_tracking)

        return expr


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
    identifier_values: Dict[ScopedName, IdentifierDefinition]
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

            qualified_member = expr_type.pointee.resolved_scope + member_name
            if qualified_member not in self.identifier_values:
                raise DefinitionError(f"Member '{qualified_member}' was not found.")
            member_definition = self.identifier_values[qualified_member]

            if not isinstance(member_definition, MemberDefinition):
                raise DefinitionError(
                    f"Expected reference offset '{qualified_member}' to be a member, "
                    f'found {member_definition.TYPE}.')
            offset_value = member_definition.offset
            expr_type = member_definition.cairo_type

            expr = ExprDeref(addr=ExprOperator(a=to_addr(expr), op='+', b=ExprConst(offset_value)))

        return ExprCast(
            expr=expr,
            dest_type=expr_type,
        )


@marshmallow_dataclass.dataclass
class ScopeDefinition(IdentifierDefinition):
    TYPE: ClassVar[str] = 'scope'
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema


class IdentifierDefinitionSchema(OneOfSchema):
    """
    Schema for IdentifierDefinition.
    OneOfSchema adds a "type" field.
    """

    type_schemas: Dict[str, Type[marshmallow.Schema]] = {
        AliasDefinition.TYPE: AliasDefinition.Schema,
        ConstDefinition.TYPE: ConstDefinition.Schema,
        MemberDefinition.TYPE: MemberDefinition.Schema,
        LabelDefinition.TYPE: LabelDefinition.Schema,
        ReferenceDefinition.TYPE: ReferenceDefinition.Schema,
        ScopeDefinition.TYPE: ScopeDefinition.Schema,
    }

    def get_obj_type(self, obj):
        return obj.TYPE


def get_struct_size(
        struct_name: ScopedName,
        identifier_values: Dict[ScopedName, IdentifierDefinition]) -> int:
    """
    Returns the size of the struct.
    """

    name = struct_name + SIZE_CONSTANT
    size_const = identifier_values.get(name)
    if size_const is None:
        raise DefinitionError(f"The identifier '{name}' was not found.")

    if not isinstance(size_const, ConstDefinition):
        raise DefinitionError(
            f"Expected '{name}' to be a const, but it is a {size_const.TYPE}.")
    return size_const.value
