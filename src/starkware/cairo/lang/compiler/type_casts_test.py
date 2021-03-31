import pytest

from starkware.cairo.lang.compiler.ast.cairo_types import CastType
from starkware.cairo.lang.compiler.parser import parse_expr, parse_type
from starkware.cairo.lang.compiler.type_casts import check_cast


@pytest.mark.parametrize('src, dest, explicit_cast, unpacking_cast, assign_cast', [
    ['T', 'T', True, True, True],
    ['felt', 'felt*', True, True, False],
    ['felt*', 'felt', True, True, False],
    ['felt*', 'T*', True, True, False],
    ['T*', 'felt*', True, True, True],
    ['felt*', 'T', True, False, False],
    ['T', 'felt*', False, False, False],
    ['felt', '(felt,felt)', False, False, False],
])
def test_type_casts(
        src: str, dest: str, explicit_cast: bool, unpacking_cast: bool, assign_cast: bool):
    src_type = parse_type(src)
    dest_type = parse_type(dest)
    expr = parse_expr('[ap]')

    actual_results = [
        check_cast(src_type=src_type, dest_type=dest_type, cast_type=cast_type, expr=expr)
        for cast_type in [CastType.EXPLICIT, CastType.UNPACKING, CastType.ASSIGN]]
    expected_results = [explicit_cast, unpacking_cast, assign_cast]
    assert actual_results == expected_results
