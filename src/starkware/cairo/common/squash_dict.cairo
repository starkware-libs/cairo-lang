from starkware.cairo.common.dict_access import DictAccess
from starkware.cairo.common.math import assert_lt_felt

# Verifies that dict_accesses lists valid chronological accesses (and updates)
# to a mutable dictionary and outputs a squashed dict with one DictAccess instance per key
# (value before and value after) which summarizes all the changes to that key.
#
# Example:
#   Input: {(key1, 0, 2), (key1, 2, 7), (key2, 4, 1), (key1, 7, 5), (key2, 1, 2)}
#   Output: {(key1, 0, 5), (key2, 4, 2)}
#
# Arguments:
# dict_accesses - a pointer to the beginning of an array of DictAccess instances. The format of each
#   entry is a triplet (key, prev_value, new_value).
# dict_accesses_end - a pointer to the end of said array.
# squashed_dict - a pointer to an output array, which will be filled with
#   DictAccess instances sorted by key with the first and last value for each key.
#
# Returns:
# squashed_dict - end pointer to squashed_dict.
#
# Implicit arguments:
# range_check_ptr - range check builtin pointer.
func squash_dict{range_check_ptr}(
        dict_accesses : DictAccess*, dict_accesses_end : DictAccess*,
        squashed_dict : DictAccess*) -> (squashed_dict : DictAccess*):
    let ptr_diff = [ap]
    %{ vm_enter_scope() %}
    ptr_diff = dict_accesses_end - dict_accesses; ap++

    if ptr_diff == 0:
        # Access array is empty, nothing to check.
        %{ vm_exit_scope() %}
        return (squashed_dict=squashed_dict)
    end
    let first_key = [fp + 1]
    let big_keys = [fp + 2]
    ap += 2
    tempvar n_accesses = ptr_diff / DictAccess.SIZE
    %{
        dict_access_size = ids.DictAccess.SIZE
        address = ids.dict_accesses.address_
        assert ids.ptr_diff % dict_access_size == 0, \
            'Accesses array size must be divisible by DictAccess.SIZE'
        n_accesses = ids.n_accesses
        if '__squash_dict_max_size' in globals():
            assert n_accesses <= __squash_dict_max_size, \
                f'squash_dict() can only be used with n_accesses<={__squash_dict_max_size}. ' \
                f'Got: n_accesses={n_accesses}.'
        # A map from key to the list of indices accessing it.
        access_indices = {}
        for i in range(n_accesses):
            key = memory[address + dict_access_size * i]
            access_indices.setdefault(key, []).append(i)
        # Descending list of keys.
        keys = sorted(access_indices.keys(), reverse=True)
        # Are the keys used bigger than range_check bound.
        ids.big_keys = 1 if keys[0] >= range_check_builtin.bound else 0
        ids.first_key = key = keys.pop()
    %}

    # Call inner.
    if big_keys != 0:
        tempvar range_check_ptr = range_check_ptr
    else:
        assert first_key = [range_check_ptr]
        tempvar range_check_ptr = range_check_ptr + 1
    end
    let (range_check_ptr, squashed_dict) = squash_dict_inner(
        range_check_ptr=range_check_ptr,
        dict_accesses=dict_accesses,
        dict_accesses_end_minus1=dict_accesses_end - 1,
        key=first_key,
        remaining_accesses=n_accesses,
        squashed_dict=squashed_dict,
        big_keys=big_keys)
    %{ vm_exit_scope() %}
    return (squashed_dict=squashed_dict)
end

# Inner tail-recursive function for squash_dict.
#
# Arguments:
# range_check_ptr - range check builtin pointer.
# dict_accesses - a pointer to the beginning of an array of DictAccess instances.
# dict_accesses_end_minus1 - a pointer to the end of said array, minus 1.
# key - current DictAccess key to check.
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
        range_check_ptr, dict_accesses : DictAccess*, dict_accesses_end_minus1 : felt*, key,
        remaining_accesses, squashed_dict : DictAccess*, big_keys) -> (
        range_check_ptr, squashed_dict : DictAccess*):
    alloc_locals

    let dict_diff : DictAccess* = squashed_dict

    # Loop to verify chronological accesses to the key.
    # These values are not needed from previous iteration.
    struct LoopTemps:
        member index_delta_minus1 : felt
        member index_delta : felt
        member ptr_delta : felt
        member should_continue : felt
    end
    # These values are needed from previous iteration.
    struct LoopLocals:
        member value : felt
        member access_ptr : DictAccess*
        member range_check_ptr : felt
    end

    # Prepare first iteration.
    %{
        current_access_indices = sorted(access_indices[key])[::-1]
        current_access_index = current_access_indices.pop()
        memory[ids.range_check_ptr] = current_access_index
    %}
    # Check that first access_index >= 0.
    tempvar current_access_index = [range_check_ptr]
    tempvar ptr_delta = current_access_index * DictAccess.SIZE

    let first_loop_locals = cast(ap, LoopLocals*)
    first_loop_locals.access_ptr = dict_accesses + ptr_delta; ap++
    let first_access : DictAccess* = first_loop_locals.access_ptr
    first_loop_locals.value = first_access.new_value; ap++
    first_loop_locals.range_check_ptr = range_check_ptr + 1; ap++

    # Verify first key.
    key = first_access.key

    # Write key and first value to dict_diff.
    key = dict_diff.key
    # Use a local variable, instead of a tempvar, to avoid increasing ap.
    local first_value = first_access.prev_value
    assert first_value = dict_diff.prev_value

    # Skip loop nondeterministically if necessary.
    local should_skip_loop
    %{ ids.should_skip_loop = 0 if current_access_indices else 1 %}
    jmp skip_loop if should_skip_loop != 0

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
    tempvar n_used_accesses = last_loop_locals.range_check_ptr - range_check_ptr
    %{ assert ids.n_used_accesses == len(access_indices[key]) %}

    # Write last value to dict_diff.
    last_loop_locals.value = dict_diff.new_value

    let range_check_ptr = last_loop_locals.range_check_ptr + 1
    tempvar remaining_accesses = remaining_accesses - n_used_accesses

    # Exit recursion when done.
    if remaining_accesses == 0:
        %{ assert len(keys) == 0 %}
        return (range_check_ptr=range_check_ptr, squashed_dict=squashed_dict + DictAccess.SIZE)
    end

    let next_key = [ap]
    ap += 1
    # Guess next_key and check that next_key > key.
    %{
        assert len(keys) > 0, 'No keys left but remaining_accesses > 0.'
        ids.next_key = key = keys.pop()
    %}

    if big_keys != 0:
        assert_lt_felt{range_check_ptr=range_check_ptr}(a=key, b=next_key)
        tempvar dict_accesses = dict_accesses
        tempvar dict_accesses_end_minus1 = dict_accesses_end_minus1
        tempvar next_key = next_key
        tempvar remaining_accesses = remaining_accesses
    else:
        assert [range_check_ptr] = next_key - (key + 1)
        tempvar range_check_ptr = range_check_ptr + 1
        tempvar dict_accesses = dict_accesses
        tempvar dict_accesses_end_minus1 = dict_accesses_end_minus1
        tempvar next_key = next_key
        tempvar remaining_accesses = remaining_accesses
    end

    return squash_dict_inner(
        range_check_ptr=range_check_ptr,
        dict_accesses=dict_accesses,
        dict_accesses_end_minus1=dict_accesses_end_minus1,
        key=next_key,
        remaining_accesses=remaining_accesses,
        squashed_dict=squashed_dict + DictAccess.SIZE,
        big_keys=big_keys)
end
