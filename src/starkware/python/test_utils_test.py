import pytest

from starkware.python.test_utils import maybe_raises


def maybe_trigger_exception(error_message):
    assert error_message is None, error_message


@pytest.mark.parametrize('error_message, res_type', [
    (None, None),
    ('test', pytest.raises(AssertionError, maybe_trigger_exception, 'test')),
])
def test_maybe_raises(error_message, res_type):
    with maybe_raises(AssertionError, error_message) as ex:
        maybe_trigger_exception(error_message)

    assert type(ex) == type(res_type)
