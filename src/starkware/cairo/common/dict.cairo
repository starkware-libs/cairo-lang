from starkware.cairo.common.dict_access import DictAccess
from starkware.cairo.common.squash_dict import squash_dict

# Creates a new dict.
func dict_new() -> (res : DictAccess*):
    %{
        if '__dict_manager' not in globals():
            from starkware.cairo.common.dict import DictManager
            __dict_manager = DictManager()

        memory[ap] = __dict_manager.new_dict(segments, initial_dict)
        del initial_dict
    %}
    ap += 1
    return (res=cast([ap - 1], DictAccess*))
end

# Reads a value from the dictionary and returns the result.
func dict_read{dict_ptr : DictAccess*}(key : felt) -> (value : felt):
    alloc_locals
    local value
    %{
        dict_tracker = __dict_manager.get_tracker(ids.dict_ptr)
        dict_tracker.current_ptr += ids.DictAccess.SIZE
        ids.value = dict_tracker.data[ids.key]
    %}
    assert dict_ptr.key = key
    assert dict_ptr.prev_value = value
    assert dict_ptr.new_value = value
    let dict_ptr = dict_ptr + DictAccess.SIZE
    return (value=value)
end

# Writes a value to the dictionary, overriding the existing value.
func dict_write{dict_ptr : DictAccess*}(key : felt, new_value : felt):
    %{
        dict_tracker = __dict_manager.get_tracker(ids.dict_ptr)
        dict_tracker.current_ptr += ids.DictAccess.SIZE
        ids.dict_ptr.prev_value = dict_tracker.data[ids.key]
        dict_tracker.data[ids.key] = ids.new_value
    %}
    assert dict_ptr.key = key
    assert dict_ptr.new_value = new_value
    let dict_ptr = dict_ptr + DictAccess.SIZE
    return ()
end

# Updates a value in a dict. prev_value must be specified. A standalone read with no write should be
# performed by writing the same value.
# It is possible to get prev_value from __dict_manager using the hint:
#   %{ ids.val = __dict_manager.get_dict(ids.dict_ptr)[ids.key] %}
func dict_update{dict_ptr : DictAccess*}(key : felt, prev_value : felt, new_value : felt):
    %{
        # Verify dict pointer and prev value.
        dict_tracker = __dict_manager.get_tracker(ids.dict_ptr)
        current_value = dict_tracker.data[ids.key]
        assert current_value == ids.prev_value, \
            f'Wrong previous value in dict. Got {ids.prev_value}, expected {current_value}.'

        # Update value.
        dict_tracker.data[ids.key] = ids.new_value
        dict_tracker.current_ptr += ids.DictAccess.SIZE
    %}
    dict_ptr.key = key
    dict_ptr.prev_value = prev_value
    dict_ptr.new_value = new_value
    let dict_ptr = dict_ptr + DictAccess.SIZE
    return ()
end

# Returns a new dictionary with one DictAccess instance per key
# (value before and value after) which summarizes all the changes to that key.
#
# Example:
#   Input: {(key1, 0, 2), (key1, 2, 7), (key2, 4, 1), (key1, 7, 5), (key2, 1, 2)}
#   Output: {(key1, 0, 5), (key2, 4, 2)}
#
# This is a wrapper of squash_dict for dictionaries created by dict_new().
func dict_squash{range_check_ptr}(
        dict_accesses_start : DictAccess*, dict_accesses_end : DictAccess*) -> (
        squashed_dict_start : DictAccess*, squashed_dict_end : DictAccess*):
    alloc_locals

    %{
        # Prepare arguments for dict_new. In particular, the same dictionary values should be copied
        # to the new (squashed) dictionary.
        vm_enter_scope({
            # Make __dict_manager accessible.
            '__dict_manager': __dict_manager,
            # Create a copy of the dict, in case it changes in the future.
            'initial_dict': dict(__dict_manager.get_dict(ids.dict_accesses_end)),
        })
    %}
    let (local squashed_dict_start) = dict_new()
    %{ vm_exit_scope() %}

    let (squashed_dict_end) = squash_dict(
        dict_accesses=dict_accesses_start,
        dict_accesses_end=dict_accesses_end,
        squashed_dict=squashed_dict_start)

    %{
        # Update the DictTracker's current_ptr to point to the end of the squashed dict.
        __dict_manager.get_tracker(ids.squashed_dict_start).current_ptr = \
            ids.squashed_dict_end.address_
    %}
    return (squashed_dict_start=squashed_dict_start, squashed_dict_end=squashed_dict_end)
end
