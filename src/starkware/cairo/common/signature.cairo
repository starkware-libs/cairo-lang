from starkware.cairo.common.cairo_builtins import SignatureBuiltin

# Verifies that the prover knows a signature of the given public_key on the given message.
#
# Prover assumption: (signature_r, signature_s) is a valid signature for the given public_key
# on the given message.
func verify_ecdsa_signature{ecdsa_ptr : SignatureBuiltin*}(
        message, public_key, signature_r, signature_s):
    %{ ecdsa_builtin.add_signature(ids.ecdsa_ptr.address_, (ids.signature_r, ids.signature_s)) %}
    assert ecdsa_ptr.message = message
    assert ecdsa_ptr.pub_key = public_key

    let ecdsa_ptr = ecdsa_ptr + SignatureBuiltin.SIZE
    return ()
end
