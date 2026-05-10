from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import EcOpBuiltin, ModBuiltin, UInt384
from starkware.cairo.common.ec import StarkCurve, ec_add, ec_mul, ec_sub, is_x_on_curve, recover_y
from starkware.cairo.common.ec_point import EcPoint
from starkware.cairo.common.registers import get_label_location

// StarkCurve.ORDER partitioned into 4 96-bit limbs, as required by the ModBuiltin.
const ORDER0 = 0xcae7b2321e66a241adc64d2f;
const ORDER1 = 0xffffffffffffffffb781126d;
const ORDER2 = 0x800000000000010;
const ORDER3 = 0;

// Checks if (signature_r, signature_s) is a valid signature for the given public_key
// on the given message. Fails if the signature is invalid.
//
// Arguments:
//   message - the signed message.
//   public_key - the public key corresponding to the key with which the message was signed.
//   signature_r - the r component of the ECDSA signature.
//   signature_s - the s component of the ECDSA signature.
//
// Note that the implementation in Stone forbids signatures where r >= 2**251 or w = 1/s >= 2**251.
func verify_ecdsa_signature_cairo{
    range_check96_ptr, mul_mod_ptr: ModBuiltin*, ec_op_ptr: EcOpBuiltin*
}(message, public_key, signature_r, signature_s) {
    alloc_locals;
    // Check that s != 0 (mod StarkCurve.ORDER).
    if (signature_s == 0) {
        [fp] = [fp] + 1;
    }
    if (signature_s == StarkCurve.ORDER) {
        [fp] = [fp] + 1;
    }
    if (signature_r == StarkCurve.ORDER) {
        [fp] = [fp] + 1;
    }
    // Check that r is the x coordinate of a point on the curve.
    // Note that this ensures that r != 0.
    let on_curve: felt = is_x_on_curve(signature_r);
    if (on_curve == FALSE) {
        [fp] = [fp] + 1;
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

    // Reserve 28 RC96 units for the values array.
    let values_arr = cast(range_check96_ptr, UInt384*);
    let range_check96_ptr = range_check96_ptr + 28;

    mod_curve_felt_to_uint384(w, &values_arr[0]);
    mod_curve_felt_to_uint384(signature_s, &values_arr[1]);
    assert values_arr[2] = UInt384(1, 0, 0, 0);
    mod_curve_felt_to_uint384(message, &values_arr[3]);
    mod_curve_felt_to_uint384(wz, &values_arr[4]);
    mod_curve_felt_to_uint384(signature_r, &values_arr[5]);
    mod_curve_felt_to_uint384(wr, &values_arr[6]);

    let (mul_mod_offsets_ptr) = get_label_location(mul_mod_offsets_values);
    tempvar ec_order = UInt384(ORDER0, ORDER1, ORDER2, ORDER3);
    assert mul_mod_ptr[0].p = ec_order;
    assert mul_mod_ptr[0].values_ptr = values_arr;
    assert mul_mod_ptr[0].offsets_ptr = mul_mod_offsets_ptr;
    assert mul_mod_ptr[0].n = 3;
    // Fill the `mul_mod` segment in cairo to workaround a bug in the Rust hint.
    assert mul_mod_ptr[1].p = ec_order;
    assert mul_mod_ptr[1].values_ptr = values_arr;
    assert mul_mod_ptr[1].offsets_ptr = mul_mod_offsets_ptr + 3;
    assert mul_mod_ptr[1].n = 2;
    assert mul_mod_ptr[2].p = ec_order;
    assert mul_mod_ptr[2].values_ptr = values_arr;
    assert mul_mod_ptr[2].offsets_ptr = mul_mod_offsets_ptr + 6;
    assert mul_mod_ptr[2].n = 1;
    let mul_mod_ptr = &mul_mod_ptr[3];

    // To verify ECDSA, obtain:
    //   wzG = wz * G, where G is a generator of the EC.
    //   wrQ = wr * Q, where Q.x = public_key.
    // and check that:
    //   wzG +/- wrQ = +/- R, or more efficiently that:
    //   (wzG +/- wrQ).x = R.x.
    let (wzG: EcPoint) = ec_mul(m=wz, p=EcPoint(x=StarkCurve.GEN_X, y=StarkCurve.GEN_Y));
    let (public_key_point: EcPoint) = recover_y(public_key);
    let (wrQ: EcPoint) = ec_mul(wr, public_key_point);

    let (candidate: EcPoint) = ec_add(wzG, wrQ);
    if (candidate.x == signature_r) {
        return ();
    }

    let (candidate: EcPoint) = ec_sub(wzG, wrQ);
    if (candidate.x == signature_r) {
        return ();
    }

    [fp] = [fp] + 1;

    return ();

    mul_mod_offsets_values:
    dw 0;  // w
    dw 4;  // signature_s
    dw 8;  // 1
    dw 0;  // w
    dw 12;  // message
    dw 16;  // wz
    dw 0;  // w
    dw 20;  // signature_r
    dw 24;  // wr
}

// Splits a felt into four 96-bit limbs, as required by the ModBuiltin, and verifies the
// correctness of that partition.
// Assumes that res_pointer refers to a region constrained by the 96-bit range check.
// Under this assumption, the function also ensures the partition corresponds to a value
// within [0, PRIME).
func mod_curve_felt_to_uint384{range_check96_ptr}(num: felt, res_pointer: UInt384*) {
    let res_96_felts = cast(res_pointer, felt*);
    %{
        num = ids.num
        memory[ids.res_96_felts] = num % (2**96)
        memory[ids.res_96_felts+1] = (num>>96) % (2**96)
        memory[ids.res_96_felts+2] = (num>>(2*96)) % (2**96)
    %}
    assert res_pointer.d3 = 0;
    tempvar d0 = res_pointer.d0;
    tempvar d1 = res_pointer.d1;
    tempvar d2 = res_pointer.d2;
    assert d0 + d1 * (2 ** 96) + d2 * (2 ** 192) = num;

    if (d2 == (2 ** 59 + 17)) {
        assert d0 = 0;
        assert d1 = 0;
        return ();
    }
    // Note that d2 is also range checked by RC96.
    assert [range_check96_ptr] = d2 + 2 ** 96 - (2 ** 59 + 17);
    let range_check96_ptr = range_check96_ptr + 1;
    return ();
}
