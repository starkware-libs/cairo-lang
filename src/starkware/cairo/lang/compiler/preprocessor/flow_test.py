from types import SimpleNamespace

import pytest

from starkware.cairo.lang.compiler.parser import parse_expr
from starkware.cairo.lang.compiler.preprocessor.flow import FlowTracking
from starkware.cairo.lang.compiler.preprocessor.reg_tracking import RegChangeKnown, RegChangeUnknown
from starkware.cairo.lang.compiler.references import FlowTrackingError, Reference
from starkware.cairo.lang.compiler.scoped_name import ScopedName


def test_flow_tracking():
    flow_tracking = FlowTracking()
    loc1 = flow_tracking.get_ap_tracking()
    flow_tracking.add_ap(3)
    assert flow_tracking.get_ap_tracking() - loc1 == RegChangeKnown(3)
    flow_tracking.add_ap(2)
    assert flow_tracking.get_ap_tracking() - loc1 == RegChangeKnown(5)
    # Adding an unknown value will revoke().
    flow_tracking.add_ap(RegChangeUnknown())
    loc2 = flow_tracking.get_ap_tracking()
    assert flow_tracking.get_ap_tracking() - loc1 == RegChangeUnknown()
    assert flow_tracking.get_ap_tracking() - loc2 == RegChangeKnown(0)
    flow_tracking.add_ap(10)
    flow_tracking.add_ap(1)
    assert flow_tracking.get_ap_tracking() - loc2 == RegChangeKnown(11)


@pytest.mark.parametrize('changes', [
    # Good case.
    SimpleNamespace(valid=True, label0=3, body0=1, label1=2, body1=2),
    # Bad case - one mismatching jump.
    SimpleNamespace(valid=False, label0=3, body0=1, label1=5, body1=2),
    # Bad case - jump mismatch with current.
    SimpleNamespace(valid=False, label0=3, body0=1, label1=2, body1=5),
])
def test_flow_tracking_labels(changes):
    # Good case.
    flow_tracking = FlowTracking()
    flow_tracking.add_flow_to_label(ScopedName.from_string('a'), changes.label0)
    flow_tracking.add_ap(changes.body0)
    flow_tracking.add_flow_to_label(ScopedName.from_string('a'), changes.label1)
    flow_tracking.add_ap(changes.body1)
    current_data = flow_tracking.get()
    flow_tracking.converge_with_label(ScopedName.from_string('a'))

    assert (flow_tracking.get() == current_data) is changes.valid


@pytest.mark.parametrize('changes', [
    SimpleNamespace(valid=True, to_a=1, to_b=4, at_a=7, at_b=4),
    SimpleNamespace(valid=False, to_a=1, to_b=4, at_a=6, at_b=4),
    SimpleNamespace(valid=False, to_a=1, to_b=4, at_a=6, at_b=5),
    SimpleNamespace(valid=False, to_a=2, to_b=4, at_a=6, at_b=5),
    SimpleNamespace(valid=False, to_a=1, to_b=3, at_a=6, at_b=5),
])
def test_flow_tracking_labels_diverge(changes):
    """
    Tests a case of divergence. Diverge to a, b with different ap diffs, then converge at c.
    """
    flow_tracking = FlowTracking()
    flow_tracking.add_flow_to_label(ScopedName.from_string('a'), changes.to_a)
    flow_tracking.add_flow_to_label(ScopedName.from_string('b'), changes.to_b)

    # Label a.
    flow_tracking.revoke()
    flow_tracking.converge_with_label(ScopedName.from_string('a'))
    flow_tracking.add_ap(changes.at_a)
    data_after_a = flow_tracking.get()
    flow_tracking.add_flow_to_label(ScopedName.from_string('c'), 0)

    # Label b.
    flow_tracking.revoke()
    flow_tracking.converge_with_label(ScopedName.from_string('b'))
    flow_tracking.add_ap(changes.at_b)
    data_after_b = flow_tracking.get()
    flow_tracking.add_flow_to_label(ScopedName.from_string('c'), 0)

    # Label c.
    flow_tracking.revoke()
    flow_tracking.converge_with_label(ScopedName.from_string('c'))
    data_at_c = flow_tracking.get()

    if changes.valid:
        assert data_after_a == data_after_b == data_at_c
    else:
        assert data_after_a != data_at_c and data_after_b != data_at_c


@pytest.mark.parametrize('refs', [
    SimpleNamespace(valid=True, expr_a=parse_expr('[fp+3]*2'), expr_b=parse_expr('[fp+3]*2')),
    SimpleNamespace(valid=False, expr_a=parse_expr('[fp+3]*2'), expr_b=parse_expr('[fp+2]*2')),
    SimpleNamespace(valid=True, expr_a=parse_expr('[ap-3]*2'), expr_b=parse_expr('[ap-1]*2')),
    SimpleNamespace(valid=False, expr_a=parse_expr('[ap-3]*2'), expr_b=parse_expr('[ap-3]*2')),
])
def test_flow_tracking_converge_references(refs):
    flow_tracking = FlowTracking()
    flow_tracking.add_flow_to_label(ScopedName.from_string('a'), RegChangeUnknown())
    flow_tracking.add_flow_to_label(ScopedName.from_string('b'), RegChangeUnknown())

    # Label a.
    flow_tracking.revoke()
    flow_tracking.converge_with_label(ScopedName.from_string('a'))
    flow_tracking.add_reference(
        name=ScopedName.from_string('x'),
        ref=Reference(
            pc=0,
            value=refs.expr_a,
            ap_tracking_data=flow_tracking.get_ap_tracking(),
        ))
    flow_tracking.add_ap(13)
    flow_tracking.add_flow_to_label(ScopedName.from_string('c'), 0)

    # Label b.
    flow_tracking.revoke()
    flow_tracking.converge_with_label(ScopedName.from_string('b'))
    flow_tracking.add_reference(
        name=ScopedName.from_string('x'),
        ref=Reference(
            pc=0,
            value=refs.expr_b,
            ap_tracking_data=flow_tracking.get_ap_tracking(),
        ))
    flow_tracking.add_ap(15)
    flow_tracking.add_flow_to_label(ScopedName.from_string('c'), 0)

    # Label c - convergence.
    flow_tracking.revoke()
    flow_tracking.converge_with_label(ScopedName.from_string('c'))

    if refs.valid:
        flow_tracking.resolve_reference(ScopedName.from_string('x'))
    else:
        with pytest.raises(FlowTrackingError):
            flow_tracking.resolve_reference(ScopedName.from_string('x'))
