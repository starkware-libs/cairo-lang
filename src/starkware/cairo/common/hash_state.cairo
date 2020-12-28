from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.hash import pedersen_hash
from starkware.cairo.common.registers import get_fp_and_pc

# Stores the hash of a sequence of items. New items can be added to the hash state using hash_update
# and hash_update_single. The final hash of the entire sequence, including the sequence length, can
# be extracted using hash_finalize.
# For example, the hash of the sequence (x, y, z) is h(h(h(h(0, x), y), z), 3).
# In particular, the hash of zero items is h(0, 0).
struct HashState:
    member current_hash = 0
    member n_words = 1
    const SIZE = 2
end

# Initializes a new HashState with no items.
func hash_init() -> (hash_state_ptr : HashState*):
    alloc_locals
    let (__fp__, _) = get_fp_and_pc()
    local hash_state : HashState
    hash_state.current_hash = 0
    hash_state.n_words = 0
    return (hash_state_ptr=&hash_state)
end

# A helper function for 'hash_update', see its documentaion.
# Computes the hash of an array of items, not including its length.
func hash_update_inner(pedersen_ptr : HashBuiltin*, curr_ptr : felt*, data_length, hash) -> (
        pedersen_ptr : HashBuiltin*, hash):
    if data_length == 0:
        return (pedersen_ptr=pedersen_ptr, hash=hash)
    end

    let (pedersen_ptr, hash) = pedersen_hash(pedersen_ptr=pedersen_ptr, x=hash, y=[curr_ptr])
    let (pedersen_ptr, hash) = hash_update_inner(
        pedersen_ptr=pedersen_ptr, curr_ptr=curr_ptr + 1, data_length=data_length - 1, hash=hash)
    return (...)
end

# Adds each item in an array of items to the HashState.
# The array is represented by a pointer and a length.
func hash_update(
        pedersen_ptr : HashBuiltin*, hash_state_ptr : HashState*, data_ptr : felt*,
        data_length) -> (pedersen_ptr : HashBuiltin*, new_hash_state_ptr : HashState*):
    alloc_locals
    let (pedersen_ptr, hash) = hash_update_inner(
        pedersen_ptr=pedersen_ptr,
        curr_ptr=data_ptr,
        data_length=data_length,
        hash=hash_state_ptr.current_hash)
    let (__fp__, _) = get_fp_and_pc()
    local new_hash_state : HashState
    new_hash_state.current_hash = hash
    assert new_hash_state.n_words = hash_state_ptr.n_words + data_length
    return (pedersen_ptr=pedersen_ptr, new_hash_state_ptr=&new_hash_state)
end

# Adds a single item to the HashState.
func hash_update_single(pedersen_ptr : HashBuiltin*, hash_state_ptr : HashState*, item) -> (
        pedersen_ptr : HashBuiltin*, new_hash_state_ptr : HashState*):
    alloc_locals
    let (pedersen_ptr, hash) = pedersen_hash(
        pedersen_ptr=pedersen_ptr, x=hash_state_ptr.current_hash, y=item)
    let (__fp__, _) = get_fp_and_pc()
    local new_hash_state : HashState
    new_hash_state.current_hash = hash
    assert new_hash_state.n_words = hash_state_ptr.n_words + 1
    return (pedersen_ptr=pedersen_ptr, new_hash_state_ptr=&new_hash_state)
end

# Returns the hash result of the HashState.
func hash_finalize(pedersen_ptr : HashBuiltin*, hash_state_ptr : HashState*) -> (
        pedersen_ptr : HashBuiltin*, hash):
    pedersen_hash(
        pedersen_ptr=pedersen_ptr, x=hash_state_ptr.current_hash, y=hash_state_ptr.n_words)
    return (...)
end
