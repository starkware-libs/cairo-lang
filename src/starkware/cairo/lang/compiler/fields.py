import marshmallow.fields as mfields

from starkware.cairo.lang.compiler.ast.cairo_types import CairoType
from starkware.cairo.lang.compiler.parser import parse_expr, parse_type
from starkware.cairo.lang.compiler.type_system import (
    is_type_resolved, mark_type_resolved, mark_types_in_expr_resolved)


class ExpressionAsStr(mfields.Field):
    """
    A field that behaves like an Expression, but serializes to a string.
    """

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        assert mark_types_in_expr_resolved(value) == value, \
            f"Expected types in '{value}' to be resolved."
        return value.format()

    def _deserialize(self, value, attr, data, **kwargs):
        return mark_types_in_expr_resolved(parse_expr(value))


class CairoTypeAsStr(mfields.Field):
    """
    A field that behaves like a CairoType, but serializes to a string.
    """

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        assert isinstance(value, CairoType), f'Expected CairoType, found: {type(value).__name__}.'
        assert is_type_resolved(value), f"Cairo type '{value}' must be resolved."
        return value.format()

    def _deserialize(self, value, attr, data, **kwargs):
        return mark_type_resolved(parse_type(value))
