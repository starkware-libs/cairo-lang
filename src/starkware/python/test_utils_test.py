import dataclasses
import math

import pytest

from starkware.python.test_utils import WithoutValidations, maybe_raises, without_validations


def maybe_trigger_exception(error_message):
    assert error_message is None, error_message


@pytest.mark.parametrize(
    "error_message, res_type",
    [
        (None, None),
        ("test", pytest.raises(AssertionError, maybe_trigger_exception, "test")),
    ],
)
def test_maybe_raises(error_message, res_type):
    with maybe_raises(AssertionError, error_message) as ex:
        maybe_trigger_exception(error_message)

    assert type(ex) == type(res_type)


@dataclasses.dataclass(frozen=True)
class PolarRepresentation:
    radius: float
    angle: float

    def __post_init__(self):
        assert 0 <= self.angle < 2 * math.pi


@dataclasses.dataclass(frozen=True)
class Line:
    point1: PolarRepresentation
    point2: PolarRepresentation


def test_without_validations():
    PolarRepresentationWithoutValidations = without_validations(PolarRepresentation)

    good_representation = PolarRepresentationWithoutValidations(radius=1, angle=0)
    bad_representation = PolarRepresentationWithoutValidations(radius=1, angle=2 * math.pi)

    assert isinstance(good_representation, WithoutValidations)
    assert isinstance(bad_representation, WithoutValidations)

    good_representation.perform_validations()
    with pytest.raises(AssertionError):
        bad_representation.perform_validations()


def test_recursive_without_validations():
    LineWithoutValidations = without_validations(Line)
    good_line = LineWithoutValidations(
        without_validations(PolarRepresentation)(radius=1, angle=math.pi),
        without_validations(PolarRepresentation)(radius=1, angle=0),
    )
    bad_line = LineWithoutValidations(
        without_validations(PolarRepresentation)(radius=1, angle=math.pi),
        without_validations(PolarRepresentation)(radius=1, angle=2 * math.pi),
    )

    assert isinstance(good_line, WithoutValidations)
    assert isinstance(bad_line, WithoutValidations)

    good_line.perform_validations()
    with pytest.raises(AssertionError):
        bad_line.perform_validations()
