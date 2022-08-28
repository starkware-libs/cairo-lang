import pytest

from starkware.cairo.lang.builtins.builtin_runner_test_utils import compile_and_run
from starkware.cairo.lang.vm.vm_exceptions import VmException
from starkware.crypto.signature.signature import (
    ALPHA,
    EC_GEN,
    FIELD_PRIME,
    MINUS_SHIFT_POINT,
    SHIFT_POINT,
)
from starkware.python.math_utils import ec_add, ec_double, ec_mult


def test_validation_rules():
    CODE_FORMAT = """
%builtins ec_op
from starkware.cairo.common.cairo_builtins import EcOpBuiltin
from starkware.cairo.common.ec_point import EcPoint

func main{{ec_op_ptr: EcOpBuiltin*}}() {{
    assert ec_op_ptr.p.x = {p[0]};
    assert ec_op_ptr.p.y = {p[1]};
    assert ec_op_ptr.q.x = {q[0]};
    assert ec_op_ptr.q.y = {q[1]};
    assert ec_op_ptr.m = {m};
    with_attr error_message("Wrong result") {{
        tempvar r = ec_op_ptr.r;
        assert r.x = {r[0]};
        assert r.y = {r[1]};
    }}
    let ec_op_ptr = ec_op_ptr + 7;
    return ();
}}
"""

    # A valid computation.
    compile_and_run(
        CODE_FORMAT.format(
            p=SHIFT_POINT,
            m=3,
            q=EC_GEN,
            r=ec_add(SHIFT_POINT, ec_mult(3, EC_GEN, ALPHA, FIELD_PRIME), FIELD_PRIME),
        ),
        layout="all",
    )

    # Test that the runner fails when the computaiton is successful but an incorrect r is given.
    with pytest.raises(VmException, match="Wrong result"):
        compile_and_run(CODE_FORMAT.format(p=SHIFT_POINT, m=3, q=EC_GEN, r=(0, 0)), layout="all")

    # Test that the runner fails when either point is not on the curve.
    with pytest.raises(VmException, match="is not on the curve"):
        compile_and_run(
            CODE_FORMAT.format(p=SHIFT_POINT, m=3, q=(123, 456), r=(0, 0)), layout="all"
        )

    with pytest.raises(VmException, match="is not on the curve"):
        compile_and_run(
            CODE_FORMAT.format(p=(123, 456), m=3, q=SHIFT_POINT, r=(0, 0)), layout="all"
        )

    # Test that the runner fails when the builtin would try to add two points with the same x.
    with pytest.raises(VmException, match="Cannot apply EC operation"):
        compile_and_run(
            CODE_FORMAT.format(p=SHIFT_POINT, m=3, q=MINUS_SHIFT_POINT, r=(0, 0)), layout="all"
        )

    with pytest.raises(VmException, match="Cannot apply EC operation"):
        compile_and_run(
            CODE_FORMAT.format(p=SHIFT_POINT, m=3, q=SHIFT_POINT, r=(0, 0)), layout="all"
        )

    with pytest.raises(VmException, match="Cannot apply EC operation"):
        compile_and_run(
            CODE_FORMAT.format(
                p=ec_double(SHIFT_POINT, ALPHA, FIELD_PRIME), m=8, q=SHIFT_POINT, r=(0, 0)
            ),
            layout="all",
        )

    # This should work because the partial sum changes after the first addition.
    with pytest.raises(VmException, match="Wrong result"):
        compile_and_run(
            CODE_FORMAT.format(
                p=ec_double(SHIFT_POINT, ALPHA, FIELD_PRIME), m=9, q=SHIFT_POINT, r=(0, 0)
            ),
            layout="all",
        )
