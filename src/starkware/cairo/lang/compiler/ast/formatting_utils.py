"""
Contains utils that help with formatting of Cairo code.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import field

import marshmallow

from starkware.cairo.lang.compiler.error_handling import LocationError
from starkware.starkware_utils.marshmallow_dataclass_fields import additional_metadata

INDENTATION = 4
LocationField = field(
    default=None,
    hash=False,
    compare=False,
    metadata=additional_metadata(
        marshmallow_field=marshmallow.fields.Field(load_only=True, dump_only=True)
    ),
)
max_line_length_ctx_var: ContextVar[int] = ContextVar("max_line_length", default=100)
one_item_per_line_ctx_var: ContextVar[bool] = ContextVar("one_item_per_line", default=True)


def get_max_line_length():
    return max_line_length_ctx_var.get()


@contextmanager
def set_max_line_length(line_length: int):
    """
    Context manager that sets max_line_length context variable.
    """
    token = max_line_length_ctx_var.set(line_length)
    try:
        yield
    finally:
        max_line_length_ctx_var.reset(token)


@contextmanager
def set_one_item_per_line(value: bool):
    """
    Context manager that sets one_item_per_line context variable.
    If true, each list item (e.g., function arguments) will be put in a separate line,
    if the list doesn't fit a single line.
    """
    token = one_item_per_line_ctx_var.set(value)
    try:
        yield
    finally:
        one_item_per_line_ctx_var.reset(token)


class FormattingError(LocationError):
    pass
