from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import EcOpBuiltin, SignatureBuiltin
from starkware.cairo.common.ec import StarkCurve, ec_add, ec_mul, ec_sub, is_x_on_curve, recover_y
from starkware.cairo.common.ec_point import EcPoint

// Verifies that the prover knows a signature of the given public_key on the given message.
//
// Prover assumption: (signature_r, signature_s) is a valid signature for the given public_key
// on the given message.
func verify_ecdsa_signature{ecdsa_ptr: SignatureBuiltin*}(
    message, public_key, signature_r, signature_s
) {
    %{ ecdsa_builtin.add_signature(ids.ecdsa_ptr.address_, (ids.signature_r, ids.signature_s)) %}
    assert ecdsa_ptr.message = message;
    assert ecdsa_ptr.pub_key = public_key;

    let ecdsa_ptr = ecdsa_ptr + SignatureBuiltin.SIZE;
    return ();
}

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
func check_ecdsa_signature{ec_op_ptr: EcOpBuiltin*}(
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

    // To verify ECDSA, obtain:
    //   zG = z * G, where z is the message and G is a generator of the EC.
    //   rQ = r * Q, where Q.x = public_key.
    //   sR = s * R, where R.x = r.
    // and check that:
    //   zG +/- rQ = +/- sR, or more efficiently that:
    //   (zG +/- rQ).x = sR.x.
    let (zG: EcPoint) = ec_mul(m=message, p=EcPoint(x=StarkCurve.GEN_X, y=StarkCurve.GEN_Y));
    let (public_key_point: EcPoint) = recover_y(public_key);
    let (rQ: EcPoint) = ec_mul(signature_r, public_key_point);
    let (signature_r_point: EcPoint) = recover_y(signature_r);
    let (sR: EcPoint) = ec_mul(signature_s, signature_r_point);

    let (candidate: EcPoint) = ec_add(zG, rQ);
    if (candidate.x == sR.x) {
        return (res=TRUE);
    }

    let (candidate: EcPoint) = ec_sub(zG, rQ);
    if (candidate.x == sR.x) {
        return (res=TRUE);
    }

    return (res=FALSE);
}
