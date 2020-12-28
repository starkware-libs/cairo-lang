import pytest

from starkware.cairo.lang.compiler.parser import parse_expr
from starkware.cairo.lang.compiler.preprocessor.reg_tracking import RegTrackingData
from starkware.cairo.lang.compiler.references import FlowTrackingError, Reference


def test_eval_reference():
    x = Reference(
        pc=0,
        value=parse_expr('2 * ap + 3 * fp - 5'),
        ap_tracking_data=RegTrackingData(group=1, offset=5))
    with pytest.raises(FlowTrackingError):
        x.eval(RegTrackingData(group=2, offset=5))
    assert x.eval(RegTrackingData(group=1, offset=8)).format() == '2 * (ap - 3) + 3 * fp - 5'


def test_eval_reference_fp_only():
    x = Reference(
        pc=0,
        value=parse_expr('3 * fp - 5 + fp * fp'),
        ap_tracking_data=RegTrackingData(group=1, offset=5))
    assert x.eval(RegTrackingData(group=2, offset=7)) == parse_expr('3 * fp - 5 + fp * fp')
