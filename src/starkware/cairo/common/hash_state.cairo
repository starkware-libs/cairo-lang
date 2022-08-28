from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.hash import hash2
from starkware.cairo.common.registers import get_fp_and_pc

// Stores the hash of a sequence of items. New items can be added to the hash state using
// hash_update and hash_update_single.
// The final hash of the entire sequence, including the sequence length,
// can be extracted using hash_finalize.
// For example, the hash of the sequence (x, y, z) is h(h(h(h(0, x), y), z), 3).
// In particular, the hash of zero items is h(0, 0).
struct HashState {
    current_hash: felt,
    n_words: felt,
}

// Initializes a new HashState with no items and returns it.
func hash_init() -> (hash_state_ptr: HashState*) {
    alloc_locals;
    let (__fp__, _) = get_fp_and_pc();
    local hash_state: HashState;
    hash_state.current_hash = 0;
    hash_state.n_words = 0;
    return (hash_state_ptr=&hash_state);
}

// Adds each item in an array of items to the HashState.
// Returns a new HashState with the hash of the items of the input HashState and the array of items.
// The array is represented by a pointer and a length.
func hash_update{hash_ptr: HashBuiltin*}(
    hash_state_ptr: HashState*, data_ptr: felt*, data_length
) -> (new_hash_state_ptr: HashState*) {
    alloc_locals;
    let (hash) = hash_update_inner(
        data_ptr=data_ptr, data_length=data_length, hash=hash_state_ptr.current_hash
    );
    let (__fp__, _) = get_fp_and_pc();
    local new_hash_state: HashState;
    new_hash_state.current_hash = hash;
    assert new_hash_state.n_words = hash_state_ptr.n_words + data_length;
    return (new_hash_state_ptr=&new_hash_state);
}

// Adds a single item to the HashState.
// Returns a new HashState with the hash of the items of the input HashState and the item.
func hash_update_single{hash_ptr: HashBuiltin*}(hash_state_ptr: HashState*, item) -> (
    new_hash_state_ptr: HashState*
) {
    alloc_locals;
    let (hash) = hash2(x=hash_state_ptr.current_hash, y=item);
    let (__fp__, _) = get_fp_and_pc();
    local new_hash_state: HashState;
    new_hash_state.current_hash = hash;
    assert new_hash_state.n_words = hash_state_ptr.n_words + 1;
    return (new_hash_state_ptr=&new_hash_state);
}

// Computes the hash of the input data and then calls hash_update_single to add the hash
// of the data to 'hash_state' as a single felt. See details in the documentation of HashState.
func hash_update_with_hashchain{hash_ptr: HashBuiltin*}(
    hash_state_ptr: HashState*, data_ptr: felt*, data_length: felt
) -> (new_hash_state_ptr: HashState*) {
    // Hash data.
    let (hash: felt) = hash_felts(data=data_ptr, length=data_length);

    // Update 'hash_state' with the hash of the data.
    return hash_update_single(hash_state_ptr=hash_state_ptr, item=hash);
}

// Returns the hash result of the HashState.
func hash_finalize{hash_ptr: HashBuiltin*}(hash_state_ptr: HashState*) -> (hash: felt) {
    let (hash) = hash2(x=hash_state_ptr.current_hash, y=hash_state_ptr.n_words);
    return (hash=hash);
}

// A helper function for 'hash_update', see its documentation.
// Computes the hash of an array of items, not including its length.
// The hash is: hash(...hash(hash(data[0], data[1]), data[2])..., data[n-1]).
func hash_update_inner{hash_ptr: HashBuiltin*}(data_ptr: felt*, data_length: felt, hash: felt) -> (
    hash: felt
) {
    if (data_length == 0) {
        return (hash=hash);
    }

    // Compute 'data_last_ptr' before entering the loop.
    alloc_locals;
    local data_last_ptr: felt* = data_ptr + data_length - 1;
    struct LoopLocals {
        data_ptr: felt*,
        hash_ptr: HashBuiltin*,
        cur_hash: felt,
    }

    // Set up first iteration locals.
    let first_locals: LoopLocals* = cast(ap, LoopLocals*);
    first_locals.data_ptr = data_ptr, ap++;
    first_locals.hash_ptr = hash_ptr, ap++;
    first_locals.cur_hash = hash, ap++;

    // Do{.
    hash_loop:
    let prev_locals: LoopLocals* = cast(ap - LoopLocals.SIZE, LoopLocals*);
    tempvar n_remaining_elements = data_last_ptr - prev_locals.data_ptr;

    // Compute hash(cur_hash, [data_ptr]).
    prev_locals.hash_ptr.x = prev_locals.cur_hash;
    assert prev_locals.hash_ptr.y = [prev_locals.data_ptr];  // Allocates one memory cell.

    // Set up next iteration locals.
    let next_locals: LoopLocals* = cast(ap, LoopLocals*);
    next_locals.data_ptr = prev_locals.data_ptr + 1, ap++;
    next_locals.hash_ptr = prev_locals.hash_ptr + HashBuiltin.SIZE, ap++;
    next_locals.cur_hash = prev_locals.hash_ptr.result, ap++;

    // } while(n_remaining_elements != 0).
    jmp hash_loop if n_remaining_elements != 0;

    // Return values from final iteration.
    let final_locals: LoopLocals* = cast(ap - LoopLocals.SIZE, LoopLocals*);
    let hash_ptr = final_locals.hash_ptr;
    return (hash=final_locals.cur_hash);
}

func hash_felts{hash_ptr: HashBuiltin*}(data: felt*, length: felt) -> (hash: felt) {
    let (hash_state_ptr: HashState*) = hash_init();
    let (hash_state_ptr) = hash_update(
        hash_state_ptr=hash_state_ptr, data_ptr=data, data_length=length
    );
    return hash_finalize(hash_state_ptr=hash_state_ptr);
}
