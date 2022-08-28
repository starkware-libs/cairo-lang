from typing import Union

import pytest

from starkware.cairo.lang.compiler.ast.cairo_types import CastType
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.parser import parse_expr, parse_type
from starkware.cairo.lang.compiler.preprocessor.preprocessor_test_utils import PRIME, preprocess_str
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.type_casts import CairoTypeError, check_cast
from starkware.cairo.lang.compiler.type_system import mark_type_resolved
from starkware.python.test_utils import maybe_raises


@pytest.fixture(scope="session")
def identifier_manager() -> IdentifierManager:
    code = """
struct T {
    x: (felt, felt),
}
"""
    return preprocess_str(code, PRIME, main_scope=ScopedName()).identifiers


@pytest.mark.parametrize(
    "src, dest, explicit_cast, unpacking_cast, assign_cast",
    [
        ["T", "T", True, True, True],
        ["felt", "felt*", True, True, False],
        ["felt*", "felt", True, True, False],
        ["felt*", "T*", True, True, False],
        ["T*", "felt*", True, True, True],
        ["felt*", "T", False, False, False],
        ["T", "felt*", False, False, False],
        # Tuples and named tuples.
        ["felt", "(felt,felt)", False, False, False],
        ["((felt, felt))", "T", True, False, False],
        ["(x: (felt, felt))", "T", True, False, False],
        ["(y: (felt, felt))", "T", "Expected argument name 'x'. Found: 'y'.", False, False],
        ["(felt)", "(a: felt)", True, True, True],
        ["(a: felt)", "(felt)", True, True, True],
        ["(a: felt, b: felt)", "(a: felt, c: felt)"]
        + ["Expected argument name 'c'. Found: 'b'."] * 3,
    ],
)
def test_type_casts(
    identifier_manager: IdentifierManager,
    src: str,
    dest: str,
    explicit_cast: Union[bool, str],
    unpacking_cast: Union[bool, str],
    assign_cast: Union[bool, str],
):
    src_type = mark_type_resolved(parse_type(src))
    dest_type = mark_type_resolved(parse_type(dest))
    expr = parse_expr("[ap]")

    for cast_type, expected_result in zip(
        [CastType.EXPLICIT, CastType.UNPACKING, CastType.ASSIGN],
        [explicit_cast, unpacking_cast, assign_cast],
    ):
        error_message = expected_result if isinstance(expected_result, str) else None
        with maybe_raises(CairoTypeError, error_message):
            actual_result = check_cast(
                src_type=src_type,
                dest_type=dest_type,
                identifier_manager=identifier_manager,
                cast_type=cast_type,
                location=None,
                expr=expr,
            )
            assert actual_result == expected_result
