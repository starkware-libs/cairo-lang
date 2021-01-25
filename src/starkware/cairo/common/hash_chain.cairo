from starkware.cairo.common.cairo_builtins import HashBuiltin

# Computes a hash chain of a sequence whose length is given at [data_ptr] and the data starts at
# data_ptr + 1. The hash is calculated backwards (from the highest memory address to the lowest).
# For example, for the 3-element sequence [x, y, z] the hash is:
#   h(3, h(x, h(y, z)))
# If data_length = 0, the function does not return (takes more than field prime steps).
func hash_chain(pedersen_ptr : HashBuiltin*, data_ptr : felt*) -> (
        pedersen_ptr : HashBuiltin*, hash : felt):
    struct LoopLocals:
        member data_ptr : felt* = 0
        member pedersen_ptr : HashBuiltin* = 1
        member cur_hash = 2
        const SIZE = 3
    end

    let data_length = ap
    [data_length] = [data_ptr]; ap++
    let loop_frame = cast(ap, LoopLocals*)

    # Prepare the loop_frame for the first iteration of the hash_loop.
    loop_frame.data_ptr = data_ptr + [data_length]; ap++
    loop_frame.pedersen_ptr = pedersen_ptr; ap++
    loop_frame.cur_hash = [loop_frame.data_ptr]; ap++

    hash_loop:
    let curr_frame = cast(ap - LoopLocals.SIZE, LoopLocals*)
    let current_hash : HashBuiltin* = curr_frame.pedersen_ptr

    let new_data_ptr = curr_frame.data_ptr - 1
    let new_data = ap
    [new_data] = [new_data_ptr]; ap++

    let n_elements_to_hash = ap
    # Assign current_hash inputs and allocate space for n_elements_to_hash.
    [new_data] = current_hash.x; ap++
    curr_frame.cur_hash = current_hash.y

    # Set the frame for the next loop iteration (going backwards).
    let next_frame = cast(ap, LoopLocals*)
    next_frame.data_ptr = new_data_ptr; ap++
    next_frame.pedersen_ptr = curr_frame.pedersen_ptr + HashBuiltin.SIZE; ap++
    next_frame.cur_hash = current_hash.result; ap++

    # Update n_elements_to_hash and loop accordingly. Note that the hash is calculated backwards.
    [n_elements_to_hash] = next_frame.data_ptr - data_ptr
    jmp hash_loop if [n_elements_to_hash] != 0

    # Note that the function return values (pedersen_ptr, hash) are at the end of next_frame so
    # they are already located in the correct location.
    ret
end
