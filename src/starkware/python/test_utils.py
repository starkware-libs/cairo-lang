import re
from contextlib import nullcontext
from typing import ContextManager, Optional

import pytest


def maybe_raises(
        expected_exception, error_message: Optional[str],
        escape_error_message: bool = True) -> ContextManager:
    """
    A utility function for parameterized tests with both positive and negative cases.
    If error_message is None, it expects no error,
    otherwise it expects an error of the given type with the given message.
    Unless 'escape_error_message' is set to False, the error message will be escaped.

    See:
    https://docs.pytest.org/en/stable/example/parametrize.html#parametrizing-conditional-raising.

    The typical use case is:
        with as_expectation(error_message) as ex:
            runner.run('tested_function', *args)

        if ex is not None:
            return

        # Extra validation logic.
    """
    if error_message is None:
        return nullcontext()

    error_message = re.escape(error_message) if escape_error_message else error_message
    return pytest.raises(expected_exception, match=error_message)
