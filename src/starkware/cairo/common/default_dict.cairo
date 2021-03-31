from starkware.cairo.common.dict import dict_squash
from starkware.cairo.common.dict_access import DictAccess

# Creates a new dictionary, with a default value.
#
# NOTE: you MUST call default_dict_finalize() (with the same default_value) to properly destruct
# the dictionary. Otherwise, the initial values of the dictionary are not guaranteed to be 'value'.
func default_dict_new(default_value : felt) -> (res : DictAccess*):
    %{
        if '__dict_manager' not in globals():
            from starkware.cairo.common.dict import DictManager
            __dict_manager = DictManager()

        memory[ap] = __dict_manager.new_default_dict(segments, ids.default_value)
    %}
    ap += 1
    return (res=cast([ap - 1], DictAccess*))
end

# Finalizes the given default dictionary, and makes sure the initial values of the dictionary
# were indeed 'default_value'.
# Returns the squashed dictionary.
func default_dict_finalize{range_check_ptr}(
        dict_accesses_start : DictAccess*, dict_accesses_end : DictAccess*,
        default_value : felt) -> (
        squashed_dict_start : DictAccess*, squashed_dict_end : DictAccess*):
    alloc_locals
    let (local squashed_dict_start, local squashed_dict_end) = dict_squash(
        dict_accesses_start, dict_accesses_end)
    local range_check_ptr = range_check_ptr

    default_dict_finalize_inner(
        dict_accesses_start=squashed_dict_start,
        n_accesses=(squashed_dict_end - squashed_dict_start) / DictAccess.SIZE,
        default_value=default_value)
    return (squashed_dict_start=squashed_dict_start, squashed_dict_end=squashed_dict_end)
end

func default_dict_finalize_inner(
        dict_accesses_start : DictAccess*, n_accesses : felt, default_value : felt):
    if n_accesses == 0:
        return ()
    end

    assert dict_accesses_start.prev_value = default_value
    return default_dict_finalize_inner(
        dict_accesses_start + DictAccess.SIZE,
        n_accesses=n_accesses - 1,
        default_value=default_value)
end
