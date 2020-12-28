import re

import pytest

from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt, TypePointer, TypeStruct
from starkware.cairo.lang.compiler.identifier_definition import (
    ConstDefinition, DefinitionError, MemberDefinition, OffsetReferenceDefinition,
    ReferenceDefinition, ScopeDefinition, get_struct_size)
from starkware.cairo.lang.compiler.parser import parse_expr
from starkware.cairo.lang.compiler.preprocessor.flow import (
    FlowTrackingDataActual, ReferenceManager, RegTrackingData)
from starkware.cairo.lang.compiler.references import Reference
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.type_system_visitor import mark_types_in_expr_resolved

scope = ScopedName.from_string


def test_offset_reference_definition_typed_members():
    t = TypeStruct(scope=scope('T'), is_fully_resolved=True)
    s_star = TypePointer(pointee=TypeStruct(scope=scope('S'), is_fully_resolved=True))
    reference_manager = ReferenceManager()
    identifiers = {
        scope('T'): ScopeDefinition(),
        scope('T.x'): MemberDefinition(offset=3, cairo_type=s_star),
        scope('T.flt'): MemberDefinition(offset=4, cairo_type=TypeFelt()),
        scope('S'): ScopeDefinition(),
        scope('S.x'): MemberDefinition(offset=10, cairo_type=t),
    }
    main_reference = ReferenceDefinition(full_name=scope('a'), references=[])
    references = {
        scope('a'): reference_manager.get_id(Reference(
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
            parent=main_reference, identifier_values=identifiers, member_path=scope(member_path))
        assert definition.eval(
            reference_manager=reference_manager,
            flow_tracking_data=flow_tracking_data).format() == expected_result

    definition = OffsetReferenceDefinition(
        parent=main_reference, identifier_values=identifiers, member_path=scope('x.x.flt.x'))
    with pytest.raises(DefinitionError, match='Member access requires a type of the form Struct*.'):
        assert definition.eval(
            reference_manager=reference_manager,
            flow_tracking_data=flow_tracking_data).format() == expected_result


def test_get_struct_size():
    identifiers = {
        scope('T'): ScopeDefinition(),
        scope('T.SIZE'): ConstDefinition(value=2),

        scope('S'): ScopeDefinition(),
        scope('S.SIZE'): ScopeDefinition(),
    }

    assert get_struct_size(ScopedName.from_string('T'), identifiers) == 2

    with pytest.raises(
            DefinitionError, match=re.escape("The identifier 'abc.SIZE' was not found.")):
        get_struct_size(ScopedName.from_string('abc'), identifiers)

    with pytest.raises(
            DefinitionError,
            match=re.escape(f"Expected 'S.SIZE' to be a const, but it is a scope.")):
        get_struct_size(ScopedName.from_string('S'), identifiers)
