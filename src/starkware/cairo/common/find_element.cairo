from starkware.cairo.common.math import assert_le, assert_nn_le

# Finds an element in the array whose first field is key and returns a pointer
# to this element.
# Since cairo is non-deterministic this is an O(1) operation.
# Note however that if the array has multiple elements with said key the function may return any
# of those elements.
#
# Arguments:
# range_check_ptr - range check builtin pointer.
# array_ptr - pointer to an array.
# elm_size - size of an element in the array.
# n_elms - number of element in the array.
# key - key to look for.
#
# Returns:
# range_check_ptr - new range check builtin pointer.
# elm_ptr - pointer to an element in the array satisfying [ptr] = key.
func find_element(range_check_ptr, array_ptr : felt*, elm_size, n_elms, key) -> (
        range_check_ptr, elm_ptr : felt*):
    alloc_locals
    local index
    %{
        for i in range(ids.n_elms):
            if memory[ids.array_ptr + ids.elm_size * i] == ids.key:
                ids.index = i
                break
        else:
            raise ValueError(f'Key {ids.key} not found.')
    %}

    let (range_check_ptr) = assert_nn_le(range_check_ptr=range_check_ptr, a=index, b=n_elms - 1)
    tempvar elm_ptr = array_ptr + elm_size * index
    assert [elm_ptr] = key
    return (range_check_ptr=range_check_ptr, elm_ptr=elm_ptr)
end

# Given an array sorted by its first field, returns the pointer to the first element in the array
# whose first field is at least key. If no such item exists, returns a pointer to the end of the
# array.
# Prover assumption: all the keys (the first field in each item) are in [0, RANGE_CHECK_BOUND).
func search_sorted_lower(range_check_ptr, array_ptr : felt*, elm_size, n_elms, key) -> (
        range_check_ptr, elm_ptr : felt*):
    alloc_locals
    local index
    %{
        for i in range(ids.n_elms):
            if memory[ids.array_ptr + ids.elm_size * i] >= ids.key:
                ids.index = i
                break
        else:
            ids.index = ids.n_elms
    %}

    let (range_check_ptr) = assert_nn_le(range_check_ptr=range_check_ptr, a=index, b=n_elms)
    local elm_ptr : felt* = array_ptr + elm_size * index

    local range_check_ptr1
    if index != n_elms:
        let (range_check_ptr) = assert_le(range_check_ptr=range_check_ptr, a=key, b=[elm_ptr])
        range_check_ptr1 = range_check_ptr
    else:
        range_check_ptr1 = range_check_ptr
    end

    local range_check_ptr2
    if index != 0:
        let (range_check_ptr) = assert_le(
            range_check_ptr=range_check_ptr1, a=[elm_ptr - elm_size] + 1, b=key)
        range_check_ptr2 = range_check_ptr
    else:
        range_check_ptr2 = range_check_ptr1
    end

    return (range_check_ptr=range_check_ptr2, elm_ptr=elm_ptr)
end

# Given an array sorted by its first field, returns the pointer to the first element in the array
# whose first field is exactly key. If no such item exists, returns an undefined pointer,
# and success=0.
# Prover assumption: all the keys (the first field in each item) are in [0, RANGE_CHECK_BOUND).
func search_sorted(range_check_ptr, array_ptr : felt*, elm_size, n_elms, key) -> (
        range_check_ptr, elm_ptr : felt*, success):
    let (range_check_ptr, elm_ptr) = search_sorted_lower(
        range_check_ptr=range_check_ptr,
        array_ptr=array_ptr,
        elm_size=elm_size,
        n_elms=n_elms,
        key=key)
    tempvar array_end = array_ptr + elm_size * n_elms
    if elm_ptr == array_end:
        return (range_check_ptr=range_check_ptr, elm_ptr=array_ptr, success=0)
    end
    if [elm_ptr] != key:
        return (range_check_ptr=range_check_ptr, elm_ptr=array_ptr, success=0)
    end
    return (range_check_ptr=range_check_ptr, elm_ptr=elm_ptr, success=1)
end
