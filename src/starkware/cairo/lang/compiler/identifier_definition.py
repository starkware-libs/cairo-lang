import dataclasses
from abc import ABC, abstractmethod
from dataclasses import field
from typing import ClassVar, Dict, List, Optional, Type

import marshmallow
import marshmallow_dataclass
from marshmallow_oneofschema import OneOfSchema

from starkware.cairo.lang.compiler.ast.cairo_types import CairoType
from starkware.cairo.lang.compiler.ast.expr import Expression
from starkware.cairo.lang.compiler.ast.formatting_utils import LocationField
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.fields import CairoTypeAsStr
from starkware.cairo.lang.compiler.preprocessor.flow import (
    FlowTrackingData, FlowTrackingDataActual, ReferenceManager)
from starkware.cairo.lang.compiler.references import Reference
from starkware.cairo.lang.compiler.scoped_name import ScopedName, ScopedNameAsStr


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

    location: Optional[Location] = LocationField


@marshmallow_dataclass.dataclass
class StructDefinition(IdentifierDefinition):
    """
    Represents a struct definition.

    struct MyStruct:
        ...
    end
    """
    TYPE: ClassVar[str] = 'struct'
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema

    full_name: ScopedName = field(metadata=dict(marshmallow_field=ScopedNameAsStr()))

    # members sorted by member offset, note the sort_members post_load function.
    members: Dict[str, MemberDefinition]
    size: int
    location: Optional[Location] = LocationField

    @marshmallow.post_load
    def sort_members(self, item, many, **kwargs):
        """
        Sorts the members according to their offset.
        """
        item['members'] = dict(
            sorted(item['members'].items(), key=lambda key_value: key_value[1].offset))
        return item


@marshmallow_dataclass.dataclass
class LabelDefinition(IdentifierDefinition):
    TYPE: ClassVar[str] = 'label'
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema

    pc: int


@marshmallow_dataclass.dataclass
class FunctionDefinition(LabelDefinition):
    TYPE: ClassVar[str] = 'function'
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema

    decorators: List[str]


@marshmallow_dataclass.dataclass
class ReferenceDefinition(IdentifierDefinition):
    TYPE: ClassVar[str] = 'reference'
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema

    full_name: ScopedName = field(metadata=dict(marshmallow_field=ScopedNameAsStr()))
    cairo_type: CairoType = field(
        metadata=dict(marshmallow_field=CairoTypeAsStr(required=True)))
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
        FunctionDefinition.TYPE: FunctionDefinition.Schema,
        ReferenceDefinition.TYPE: ReferenceDefinition.Schema,
        ScopeDefinition.TYPE: ScopeDefinition.Schema,
        StructDefinition.TYPE: StructDefinition.Schema,
    }

    def get_obj_type(self, obj):
        return obj.TYPE
