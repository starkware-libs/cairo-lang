from src.starkware.cairo.common.cairo_ec_op.ec_op import ec_mul_cairo

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import ModBuiltin, UInt384
from starkware.cairo.common.ec import StarkCurve, ec_add, ec_sub, is_x_on_curve, recover_y
from starkware.cairo.common.ec_point import EcPoint
from starkware.cairo.common.registers import get_label_location

// StarkCurve.ORDER partitioned into 4 96-bit limbs, as required by the ModBuiltin.
const ORDER0 = 0xcae7b2321e66a241adc64d2f;
const ORDER1 = 0xffffffffffffffffb781126d;
const ORDER2 = 0x800000000000010;
const ORDER3 = 0;

// Checks if (signature_r, signature_s) is a valid signature for the given public_key
// on the given message.
//
// Arguments:
//   message - the signed message.
//   public_key - the public key corresponding to the key with which the message was signed.
//   signature_r - the r component of the ECDSA signature.
//   signature_s - the s component of the ECDSA signature.
//
// Returns:
//   res - TRUE if the signature is valid, FALSE otherwise.
func check_ecdsa_signature_cairo{range_check96_ptr, mul_mod_ptr: ModBuiltin*}(
    message, public_key, signature_r, signature_s
) -> (res: felt) {
    alloc_locals;
    // Check that s != 0 (mod StarkCurve.ORDER).
    if (signature_s == 0) {
        return (res=FALSE);
    }
    if (signature_s == StarkCurve.ORDER) {
        return (res=FALSE);
    }
    if (signature_r == StarkCurve.ORDER) {
        return (res=FALSE);
    }

    // Check that the public key is the x coordinate of a point on the curve.
    let on_curve: felt = is_x_on_curve(public_key);
    if (on_curve == FALSE) {
        return (res=FALSE);
    }
    // Check that r is the x coordinate of a point on the curve.
    // Note that this ensures that r != 0.
    let on_curve: felt = is_x_on_curve(signature_r);
    if (on_curve == FALSE) {
        return (res=FALSE);
    }

    // Compute w=1/s (mod StarkCurve.ORDER).
    // also compute wz = w * message and wr = w * signature_r.
    local w;
    local wz;
    local wr;
    %{
        # ids.StarkCurve.ORDER is parsed as a negative number.
        order = ids.StarkCurve.ORDER + PRIME
        ids.w = pow(ids.signature_s, -1, order)
        ids.wz = ids.w*ids.message % order
        ids.wr = ids.w*ids.signature_r % order
    %}
    verify_mod_curve_order_mul(a=signature_s, b=w, c=1);
    verify_mod_curve_order_mul(a=w, b=message, c=wz);
    verify_mod_curve_order_mul(a=w, b=signature_r, c=wr);

    // To verify ECDSA, obtain:
    //   wzG = wz * G, where G is a generator of the EC.
    //   wrQ = wr * Q, where Q.x = public_key.
    // and check that:
    //   wzG +/- wrQ = +/- R, or more efficiently that:
    //   (wzG +/- wrQ).x = R.x.
    let (wzG: EcPoint) = ec_mul_cairo(m=wz, p=EcPoint(x=StarkCurve.GEN_X, y=StarkCurve.GEN_Y));
    let (public_key_point: EcPoint) = recover_y(public_key);
    let (wrQ: EcPoint) = ec_mul_cairo(wr, public_key_point);

    let (candidate: EcPoint) = ec_add(wzG, wrQ);
    if (candidate.x == signature_r) {
        return (res=TRUE);
    }

    let (candidate: EcPoint) = ec_sub(wzG, wrQ);
    if (candidate.x == signature_r) {
        return (res=TRUE);
    }

    return (res=FALSE);
}

// Assert that the product of a and b modulo StarkCurve.ORDER is equal to c.
func verify_mod_curve_order_mul{range_check96_ptr, mul_mod_ptr: ModBuiltin*}(
    a: felt, b: felt, c: felt
) {
    alloc_locals;

    let (a384) = mod_curve_felt_to_uint384(a);
    let (b384) = mod_curve_felt_to_uint384(b);
    let (c384) = mod_curve_felt_to_uint384(c);

    let values_arr = cast(range_check96_ptr, UInt384*);
    assert values_arr[0] = a384;
    assert values_arr[1] = b384;
    assert values_arr[2] = c384;

    let (mul_mod_offsets_ptr) = get_label_location(mul_mod_offsets_values);

    assert mul_mod_ptr[0].p = UInt384(ORDER0, ORDER1, ORDER2, ORDER3);
    assert mul_mod_ptr[0].values_ptr = values_arr;
    assert mul_mod_ptr[0].offsets_ptr = mul_mod_offsets_ptr;
    assert mul_mod_ptr[0].n = 1;

    let range_check96_ptr = range_check96_ptr + 12;
    let mul_mod_ptr = mul_mod_ptr + ModBuiltin.SIZE;

    return ();

    mul_mod_offsets_values:
    dw 0;  // a384
    dw 4;  // b384
    dw 8;  // a384 * b384.
}

// Partitions a felt into 4 96-bit limbs as required by the ModBuiltin and verifies that partition.
// Assumes that the limbs of the output will be range checked 96 by the caller.
// Under that assumption it also verifies the partition represents a number in the range [0, PRIME).
func mod_curve_felt_to_uint384{range_check96_ptr}(num: felt) -> (res: UInt384) {
    alloc_locals;
    let (local res_96_felts: felt*) = alloc();
    %{
        num = ids.num
        memory[ids.res_96_felts] = num % (2**96)
        memory[ids.res_96_felts+1] = (num>>96) % (2**96)
        memory[ids.res_96_felts+2] = (num>>(2*96)) % (2**96)
    %}
    assert res_96_felts[0] + res_96_felts[1] * (2 ** 96) + res_96_felts[2] * (2 ** 192) = num;
    let res = UInt384(d0=res_96_felts[0], d1=res_96_felts[1], d2=res_96_felts[2], d3=0);
    if (res_96_felts[2] == (2 ** 59 + 17)) {
        assert res_96_felts[1] = 0;
        assert res_96_felts[0] = 0;
        return (res=res);
    }
    // res_96_felts[2] will be range checked 96 by the caller.
    assert [range_check96_ptr] = res_96_felts[2] + (2 ** 96 - 2 ** 59 - 17);
    let range_check96_ptr = range_check96_ptr + 1;
    return (res=res);
}
