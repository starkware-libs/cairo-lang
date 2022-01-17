import dataclasses
import re
from abc import abstractmethod
from contextlib import nullcontext
from typing import ContextManager, Optional, Type, TypeVar

import pytest


def maybe_raises(
    expected_exception, error_message: Optional[str], escape_error_message: bool = True
) -> ContextManager:
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


T = TypeVar("T")


class WithoutValidations:
    @abstractmethod
    def perform_validations(self):
        pass


def without_validations(base: Type[T]) -> Type[T]:
    """
    Receives a class and returns the same class but with __post_init__ disabled. This is useful in
    order to create an invalid object for negative tests.
    """

    class _WithoutValidations(base, WithoutValidations):  # type: ignore
        def __post_init__(self):
            pass

        def perform_validations(self):
            """
            Performs the validations that were skipped in the constructor.
            """
            if hasattr(base, "__post_init__"):
                super().__post_init__()

            for field_info in dataclasses.fields(self):
                field = getattr(self, field_info.name)
                if isinstance(field, WithoutValidations):
                    field.perform_validations()

    return _WithoutValidations
