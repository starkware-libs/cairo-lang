%builtins output pedersen

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.hash import hash2
from starkware.cairo.common.serialize import serialize_word

func main{output_ptr : felt*, pedersen_ptr : HashBuiltin*}():
    let (hash) = hash2{hash_ptr=pedersen_ptr}(1, 2)
    serialize_word(hash)
    return ()
end
