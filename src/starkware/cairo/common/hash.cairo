from starkware.cairo.common.cairo_builtins import HashBuiltin

# Computes the hash of two given field elements.
# The hash function is defined by the hash_ptr used.
# For example, pass the pedersen builtin pointer to compute Pedersen hash.
#
# Arguments:
#   hash_ptr - the hash builtin pointer.
#   x, y - the two field elements to be hashed, in this order.
#
# Returns:
#   result - the field element result of the hash.
func hash2{hash_ptr : HashBuiltin*}(x, y) -> (result):
    hash_ptr.x = x
    hash_ptr.y = y
    let result = hash_ptr.result
    let hash_ptr = hash_ptr + HashBuiltin.SIZE
    return (result=result)
end
