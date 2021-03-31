import pytest

from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt, TypePointer, TypeStruct
from starkware.cairo.lang.compiler.identifier_definition import (
    DefinitionError, MemberDefinition, ReferenceDefinition, StructDefinition)
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.offset_reference import OffsetReferenceDefinition
from starkware.cairo.lang.compiler.parser import parse_expr
from starkware.cairo.lang.compiler.preprocessor.flow import (
    FlowTrackingDataActual, ReferenceManager, RegTrackingData)
from starkware.cairo.lang.compiler.references import Reference
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.type_system_visitor import mark_types_in_expr_resolved

scope = ScopedName.from_string


def test_offset_reference_definition_typed_members():
    t = TypeStruct(scope=scope('T'), is_fully_resolved=True)
    t_star = TypePointer(pointee=t)
    s_star = TypePointer(pointee=TypeStruct(scope=scope('S'), is_fully_resolved=True))
    reference_manager = ReferenceManager()
    identifiers = IdentifierManager.from_dict({
        scope('T'): StructDefinition(
            full_name='T',
            members={
                'x': MemberDefinition(offset=3, cairo_type=s_star),
                'flt': MemberDefinition(offset=4, cairo_type=TypeFelt()),
            },
            size=5,
        ),
        scope('S'): StructDefinition(
            full_name='S',
            members={
                'x': MemberDefinition(offset=10, cairo_type=t),
            },
            size=15,
        ),
    })
    main_reference = ReferenceDefinition(full_name=scope('a'), cairo_type=t_star, references=[])
    references = {
        scope('a'): reference_manager.alloc_id(Reference(
            pc=0,
            value=mark_types_in_expr_resolved(parse_expr('cast(ap, T*)')),
            ap_tracking_data=RegTrackingData(group=0, offset=0),
        )),
    }

    flow_tracking_data = FlowTrackingDataActual(
        ap_tracking=RegTrackingData(group=0, offset=1),
        reference_ids=references,
    )

    # Create OffsetReferenceDefinition instances for expressions of the form "a.<member_path>",
    # such as a.x and a.x.x, and check the result of evaluation those expressions.
    for member_path, expected_result in [
            ('x', 'cast([ap - 1 + 3], S*)'),
            ('x.x', 'cast([[ap - 1 + 3] + 10], T)'),
            ('x.x.x', 'cast([&[[ap - 1 + 3] + 10] + 3], S*)'),
            ('x.x.flt', 'cast([&[[ap - 1 + 3] + 10] + 4], felt)')]:
        definition = OffsetReferenceDefinition(
            parent=main_reference, identifiers=identifiers, member_path=scope(member_path))
        definition.eval(
            reference_manager=reference_manager,
            flow_tracking_data=flow_tracking_data).format() == expected_result

    definition = OffsetReferenceDefinition(
        parent=main_reference, identifiers=identifiers, member_path=scope('x.x.flt.x'))
    with pytest.raises(DefinitionError, match='Member access requires a type of the form Struct*.'):
        definition.eval(reference_manager=reference_manager, flow_tracking_data=flow_tracking_data)

    definition = OffsetReferenceDefinition(
        parent=main_reference, identifiers=identifiers, member_path=scope('x.y'))
    with pytest.raises(DefinitionError, match="'y' is not a member of 'S'."):
        definition.eval(reference_manager=reference_manager, flow_tracking_data=flow_tracking_data)
