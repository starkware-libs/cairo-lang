from starkware.cairo.common.cairo_builtins import HashBuiltin

# Computes the Pedersen hash of two given field elements.
#
# Arguments:
# pedersen_ptr - the Pedersen hash builtin pointer.
# x, y - the two field elements to be hashed, in this order.
#
# Returns:
# pedersen_ptr - the new Pedersen builtin pointer.
# result - the field element result of the hash.
func pedersen_hash(pedersen_ptr : HashBuiltin*, x, y) -> (pedersen_ptr : HashBuiltin*, result):
    pedersen_ptr.x = x
    pedersen_ptr.y = y
    return (pedersen_ptr=pedersen_ptr + HashBuiltin.SIZE, result=pedersen_ptr.result)
end
