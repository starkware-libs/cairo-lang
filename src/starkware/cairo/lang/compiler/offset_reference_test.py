from starkware.cairo.lang.compiler.ast.cairo_types import TypePointer, TypeStruct
from starkware.cairo.lang.compiler.identifier_definition import ReferenceDefinition
from starkware.cairo.lang.compiler.offset_reference import OffsetReferenceDefinition
from starkware.cairo.lang.compiler.parser import parse_expr
from starkware.cairo.lang.compiler.preprocessor.flow import (
    FlowTrackingDataActual,
    ReferenceManager,
    RegTrackingData,
)
from starkware.cairo.lang.compiler.references import Reference
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.type_system import mark_types_in_expr_resolved

scope = ScopedName.from_string


def test_offset_reference_definition_typed_members():
    t = TypeStruct(scope=scope("T"))
    t_star = TypePointer(pointee=t)
    reference_manager = ReferenceManager()

    main_reference = ReferenceDefinition(full_name=scope("a"), cairo_type=t_star, references=[])
    references = {
        scope("a"): reference_manager.alloc_id(
            Reference(
                pc=0,
                value=mark_types_in_expr_resolved(parse_expr("cast(ap, T*)")),
                ap_tracking_data=RegTrackingData(group=0, offset=0),
            )
        ),
    }

    flow_tracking_data = FlowTrackingDataActual(
        ap_tracking=RegTrackingData(group=0, offset=1),
        reference_ids=references,
    )

    # Create OffsetReferenceDefinition instance for an expression of the form "a.<member_path>",
    # in this case a.x.y.z, and check the result of evaluation of this expression.
    definition = OffsetReferenceDefinition(parent=main_reference, member_path=scope("x.y.z"))
    assert (
        definition.eval(
            reference_manager=reference_manager, flow_tracking_data=flow_tracking_data
        ).format()
        == "cast(ap - 1, T*).x.y.z"
    )
