from starkware.cairo.common.cairo_builtins import HashBuiltin

# Computes a hash chain of a sequence whose length is given at [data_ptr] and the data starts at
# data_ptr + 1. The hash is calculated backwards (from the highest memory address to the lowest).
# For example, for the 3-element sequence [x, y, z] the hash is:
#   h(3, h(x, h(y, z)))
# If data_length = 0, the function does not return (takes more than field prime steps).
func hash_chain{hash_ptr : HashBuiltin*}(data_ptr : felt*) -> (hash : felt):
    struct LoopLocals:
        member data_ptr : felt*
        member hash_ptr : HashBuiltin*
        member cur_hash : felt
    end

    tempvar data_length = [data_ptr]
    tempvar data_ptr_end = data_ptr + data_length
    # Prepare the loop_frame for the first iteration of the hash_loop.
    tempvar loop_frame = LoopLocals(
        data_ptr=data_ptr_end,
        hash_ptr=hash_ptr,
        cur_hash=[data_ptr_end])

    hash_loop:
    let curr_frame = cast(ap - LoopLocals.SIZE, LoopLocals*)
    let current_hash : HashBuiltin* = curr_frame.hash_ptr

    tempvar new_data = [curr_frame.data_ptr - 1]

    let n_elements_to_hash = [ap]
    # Assign current_hash inputs and allocate space for n_elements_to_hash.
    current_hash.x = new_data; ap++
    current_hash.y = curr_frame.cur_hash

    # Set the frame for the next loop iteration (going backwards).
    tempvar next_frame = LoopLocals(
        data_ptr=curr_frame.data_ptr - 1,
        hash_ptr=curr_frame.hash_ptr + HashBuiltin.SIZE,
        cur_hash=current_hash.result)

    # Update n_elements_to_hash and loop accordingly. Note that the hash is calculated backwards.
    n_elements_to_hash = next_frame.data_ptr - data_ptr
    jmp hash_loop if n_elements_to_hash != 0

    # Set the hash_ptr implicit argument and return the result.
    let hash_ptr = next_frame.hash_ptr
    return (hash=next_frame.cur_hash)
end
