import itertools

import pytest

from starkware.cairo.lang.compiler.ast.expr import ExprConst, ExprIdentifier
from starkware.cairo.lang.compiler.preprocessor.reg_tracking import (
    RegChange, RegChangeKnown, RegChangeUnconstrained, RegChangeUnknown, RegTrackingData)


def test_from_expr():
    assert RegChange.from_expr(5) == RegChangeKnown(5)
    assert RegChange.from_expr(RegChangeKnown(6)) == RegChangeKnown(6)
    assert RegChange.from_expr(ExprConst(7)) == RegChangeKnown(7)
    assert RegChange.from_expr(ExprIdentifier('asd')) == RegChangeUnknown()

    with pytest.raises(TypeError):
        RegChange.from_expr('wrong type')


def test_reg_change_add():
    assert RegChangeKnown(1) + 5 == RegChangeKnown(6)
    assert 3 + RegChangeKnown(4) == RegChangeKnown(7)
    assert RegChangeUnknown() + RegChangeKnown(2) == RegChangeUnknown()

    with pytest.raises(TypeError):
        RegChangeKnown(3) + 'asd'

    with pytest.raises(TypeError):
        RegChangeUnconstrained() + RegChangeKnown(0)


def test_reg_change_and():
    assert RegChangeKnown(1) & 5 == RegChangeUnknown()
    assert 3 & RegChangeKnown(3) == RegChangeKnown(3)
    assert 1 & RegChangeUnconstrained() == RegChangeKnown(1)


def test_reg_tracking_data():
    assert RegTrackingData(group=3, offset=5) - RegTrackingData(group=3, offset=17) == \
        RegChangeKnown(-12)
    assert RegTrackingData(group=3, offset=5) - RegTrackingData(group=4, offset=17) == \
        RegChangeUnknown()


def test_reg_tracking_data_add():
    initial_data = RegTrackingData(group=3, offset=5)
    groups = itertools.count(4)

    def group_alloc():
        return next(groups)
    assert initial_data.add(3, group_alloc) == RegTrackingData(group=3, offset=8)
    assert initial_data.add(RegChangeUnknown(), group_alloc) == RegTrackingData(group=4, offset=0)
    assert initial_data.add(RegChangeUnknown(), group_alloc) == RegTrackingData(group=5, offset=0)
    with pytest.raises(NotImplementedError):
        initial_data.add(RegChangeUnconstrained(), group_alloc)
