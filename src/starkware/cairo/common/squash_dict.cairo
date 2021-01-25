from starkware.cairo.common.dict_access import DictAccess

# Inner tail-recursive function for squash_dict.
#
# Arguments:
# range_check_ptr - range check builtin pointer.
# dict_accesses - a pointer to the beginning of an array of DictAccess instances.
# dict_accesses_end_minus1 - a pointer to the end of said array, minus 1.
# min_key - minimum allowed key. Used to enforce monotonicity of keys.
# remaining_accesses - remaining number of accesses that need to be accounted for. Starts with
#   the total number of entries in dict_accesses array, and slowly decreases until it reaches 0.
# squashed_dict - a pointer to an output array, which will be filled with
# DictAccess instances sorted by key with the first and last value for each key.
#
# Hints:
# keys - a descending list of the keys for which we have accesses. Destroyed in the process.
# access_indices - A map from key to a descending list of indices in the dict_accesses array that
#   access this key. Destroyed in the process.
#
# Returns:
# range_check_ptr - updated range check builtin pointer.
# squashed_dict - end pointer to squashed_dict.
func squash_dict_inner(
        range_check_ptr, dict_accesses : DictAccess*, dict_accesses_end_minus1 : felt*, min_key,
        remaining_accesses, squashed_dict : DictAccess*) -> (
        range_check_ptr, squashed_dict : DictAccess*):
    # Exit recursion when done.
    if remaining_accesses == 0:
        %{ assert len(keys) == 0 %}
        return (range_check_ptr=range_check_ptr, squashed_dict=squashed_dict)
    end

    # Locals.
    struct Locals:
        member key = 0
        member should_skip_loop = 1
        member first_value = 2
        const SIZE = 3
    end
    let locals = cast(fp, Locals*)
    let key = locals.key
    let dict_diff : DictAccess* = squashed_dict
    ap += Locals.SIZE

    # Guess key and check that key >= min_key.
    %{ ids.locals.key = key = keys.pop() %}
    [ap] = key - min_key
    [ap] = [range_check_ptr]; ap++

    # Loop to verify chronological accesses to the key.
    # These values are not needed from previous iteration.
    struct LoopTemps:
        member index_delta_minus1 = 0
        member index_delta = 1
        member ptr_delta = 2
        member should_continue = 3
        const SIZE = 4
    end
    # These values are needed from previous iteration.
    struct LoopLocals:
        member value = 0
        member access_ptr : DictAccess* = 1
        member range_check_ptr = 2
        const SIZE = 3
    end

    # Prepare first iteration.
    %{
        current_access_indices = sorted(access_indices[key])[::-1]
        current_access_index = current_access_indices.pop()
        memory[ids.range_check_ptr + 1] = current_access_index
    %}
    # Check that first access_index >= 0.
    tempvar current_access_index = [range_check_ptr + 1]
    tempvar ptr_delta = current_access_index * DictAccess.SIZE

    let first_loop_locals = cast(ap, LoopLocals*)
    first_loop_locals.access_ptr = dict_accesses + ptr_delta; ap++
    let first_access : DictAccess* = first_loop_locals.access_ptr
    first_loop_locals.value = first_access.new_value; ap++
    first_loop_locals.range_check_ptr = range_check_ptr + 2; ap++

    # Verify first key.
    key = first_access.key

    # Write key and first value to dict_diff.
    key = dict_diff.key
    # Use a local variable, instead of a tempvar, to avoid increasing ap.
    locals.first_value = first_access.prev_value
    locals.first_value = dict_diff.prev_value

    # Skip loop non-deterministically if necessary.
    %{ memory[fp + ids.Locals.should_skip_loop] = 0 if current_access_indices else 1 %}
    jmp skip_loop if [fp + Locals.should_skip_loop] != 0

    loop:
    let prev_loop_locals = cast(ap - LoopLocals.SIZE, LoopLocals*)
    let loop_temps = cast(ap, LoopTemps*)
    let loop_locals = cast(ap + LoopTemps.SIZE, LoopLocals*)

    # Check access_index.
    %{
        new_access_index = current_access_indices.pop()
        ids.loop_temps.index_delta_minus1 = new_access_index - current_access_index - 1
        current_access_index = new_access_index
    %}
    # Check that new access_index > prev access_index.
    loop_temps.index_delta_minus1 = [prev_loop_locals.range_check_ptr]; ap++
    loop_temps.index_delta = loop_temps.index_delta_minus1 + 1; ap++
    loop_temps.ptr_delta = loop_temps.index_delta * DictAccess.SIZE; ap++
    loop_locals.access_ptr = prev_loop_locals.access_ptr + loop_temps.ptr_delta; ap++

    # Check valid transition.
    let access : DictAccess* = loop_locals.access_ptr
    prev_loop_locals.value = access.prev_value
    loop_locals.value = access.new_value; ap++

    # Verify key.
    key = access.key

    # Next range_check_ptr.
    loop_locals.range_check_ptr = prev_loop_locals.range_check_ptr + 1; ap++

    %{ ids.loop_temps.should_continue = 1 if current_access_indices else 0 %}
    jmp loop if loop_temps.should_continue != 0; ap++

    skip_loop:
    let last_loop_locals = cast(ap - LoopLocals.SIZE, LoopLocals*)

    # Check if address is out of bounds.
    %{ assert len(current_access_indices) == 0 %}
    [ap] = dict_accesses_end_minus1 - cast(last_loop_locals.access_ptr, felt)
    [ap] = [last_loop_locals.range_check_ptr]; ap++
    tempvar range_check_diff = last_loop_locals.range_check_ptr - range_check_ptr
    tempvar n_used_accesses = range_check_diff - 1
    %{ assert ids.n_used_accesses == len(access_indices[key]) %}

    # Write last value to dict_diff.
    last_loop_locals.value = dict_diff.new_value

    # Call squashed_dict_inner recursively.
    squash_dict_inner(
        range_check_ptr=last_loop_locals.range_check_ptr + 1,
        dict_accesses=dict_accesses,
        dict_accesses_end_minus1=dict_accesses_end_minus1,
        min_key=key + 1,
        remaining_accesses=remaining_accesses - n_used_accesses,
        squashed_dict=squashed_dict + DictAccess.SIZE)
    return (...)
end

# Verifies that dict_accesses lists valid chronological accesses (and updates)
# to a mutable dictionary and outputs a squashed dict with one DictAccess instance per key
# (value before and value after) which summarizes all the changes to that key.
#
# All keys are assumed to be in the range of the range check builtin (usually 2**128).
#
# Example:
#   Input: {(key1, 0, 2), (key1, 2, 7), (key2, 4, 1), (key1, 7, 5), (key2, 1, 2)}
#   Output: {(key1, 0, 5), (key2, 4, 2)}
#
# Arguments:
# range_check_ptr - range check builtin pointer.
# dict_accesses - a pointer to the beginning of an array of DictAccess instances. The format of each
#   entry is a triplet (key, prev_value, new_value).
# dict_accesses_end - a pointer to the end of said array.
# squashed_dict - a pointer to an output array, which will be filled with
#   DictAccess instances sorted by key with the first and last value for each key.
#
# Returns:
# range_check_ptr - updated range check builtin pointer.
# squashed_dict - end pointer to squashed_dict.
func squash_dict(
        range_check_ptr, dict_accesses : DictAccess*, dict_accesses_end : DictAccess*,
        squashed_dict : DictAccess*) -> (range_check_ptr, squashed_dict : DictAccess*):
    let ptr_diff = [fp]
    %{ vm_enter_scope() %}
    ptr_diff = dict_accesses_end - dict_accesses; ap++

    if ptr_diff == 0:
        # Access array is empty, nothing to check.
        %{ vm_exit_scope() %}
        return (range_check_ptr=range_check_ptr, squashed_dict=squashed_dict)
    end

    tempvar n_accesses = ptr_diff / DictAccess.SIZE
    %{
        assert ids.ptr_diff % ids.DictAccess.SIZE == 0, \
            'Accesses array size must be divisible by DictAccess.SIZE'
        # A map from key to the list of indices accessing it.
        access_indices = {}
        for i in range(ids.n_accesses):
            key = memory[ids.dict_accesses.address_ + ids.DictAccess.SIZE * i]
            access_indices.setdefault(key, []).append(i)
        # Descending list of keys.
        keys = sorted(access_indices.keys())[::-1]
    %}

    # Call inner.
    squash_dict_inner(
        range_check_ptr=range_check_ptr,
        dict_accesses=dict_accesses,
        dict_accesses_end_minus1=dict_accesses_end - 1,
        min_key=0,
        remaining_accesses=n_accesses,
        squashed_dict=squashed_dict)
    %{ vm_exit_scope() %}
    return (...)
end
