from starkware.cairo.common.math import assert_le, assert_nn_le

const FIND_ELEMENT_RANGE_CHECK_USAGE = 2

# Finds an element in the array whose first field is key and returns a pointer
# to this element.
# Since cairo is nondeterministic this is an O(1) operation.
# Note however that if the array has multiple elements with said key the function may return any
# of those elements.
#
# Arguments:
# array_ptr - pointer to an array.
# elm_size - size of an element in the array.
# n_elms - number of element in the array.
# key - key to look for.
#
# Implicit arguments:
# range_check_ptr - range check builtin pointer.
#
# Returns:
# elm_ptr - pointer to an element in the array satisfying [ptr] = key.
#
# Optional hint variables:
# __find_element_index - the index that should be returned. If not specified, the function will
#   search for it.
func find_element{range_check_ptr}(array_ptr : felt*, elm_size, n_elms, key) -> (elm_ptr : felt*):
    alloc_locals
    local index
    %{
        array_ptr = ids.array_ptr
        elm_size = ids.elm_size
        assert isinstance(elm_size, int) and elm_size > 0, \
            f'Invalid value for elm_size. Got: {elm_size}.'
        key = ids.key

        if '__find_element_index' in globals():
            ids.index = __find_element_index
            found_key = memory[array_ptr + elm_size * __find_element_index]
            assert found_key == key, \
                f'Invalid index found in __find_element_index. index: {__find_element_index}, ' \
                f'expected key {key}, found key: {found_key}.'
            # Delete __find_element_index to make sure it's not used for the next calls.
            del __find_element_index
        else:
            n_elms = ids.n_elms
            assert isinstance(n_elms, int) and n_elms >= 0, \
                f'Invalid value for n_elms. Got: {n_elms}.'
            if '__find_element_max_size' in globals():
                assert n_elms <= __find_element_max_size, \
                    f'find_element() can only be used with n_elms<={__find_element_max_size}. ' \
                    f'Got: n_elms={n_elms}.'

            for i in range(n_elms):
                if memory[array_ptr + elm_size * i] == key:
                    ids.index = i
                    break
            else:
                raise ValueError(f'Key {key} was not found.')
    %}

    assert_nn_le(a=index, b=n_elms - 1)
    tempvar elm_ptr = array_ptr + elm_size * index
    assert [elm_ptr] = key
    return (elm_ptr=elm_ptr)
end

# Given an array sorted by its first field, returns the pointer to the first element in the array
# whose first field is at least key. If no such item exists, returns a pointer to the end of the
# array.
# Prover assumption: all the keys (the first field in each item) are in [0, RANGE_CHECK_BOUND).
func search_sorted_lower{range_check_ptr}(array_ptr : felt*, elm_size, n_elms, key) -> (
        elm_ptr : felt*):
    alloc_locals
    local index
    %{
        array_ptr = ids.array_ptr
        elm_size = ids.elm_size
        assert isinstance(elm_size, int) and elm_size > 0, \
            f'Invalid value for elm_size. Got: {elm_size}.'

        n_elms = ids.n_elms
        assert isinstance(n_elms, int) and n_elms >= 0, \
            f'Invalid value for n_elms. Got: {n_elms}.'
        if '__find_element_max_size' in globals():
            assert n_elms <= __find_element_max_size, \
                f'find_element() can only be used with n_elms<={__find_element_max_size}. ' \
                f'Got: n_elms={n_elms}.'

        for i in range(n_elms):
            if memory[array_ptr + elm_size * i] >= ids.key:
                ids.index = i
                break
        else:
            ids.index = n_elms
    %}

    assert_nn_le(a=index, b=n_elms)
    local elm_ptr : felt* = array_ptr + elm_size * index

    if index != n_elms:
        assert_le(a=key, b=[elm_ptr])
    else:
        tempvar range_check_ptr = range_check_ptr
    end

    if index != 0:
        assert_le(a=[elm_ptr - elm_size] + 1, b=key)
    end

    return (elm_ptr=elm_ptr)
end

# Given an array sorted by its first field, returns the pointer to the first element in the array
# whose first field is exactly key. If no such item exists, returns an undefined pointer,
# and success=0.
# Prover assumption: all the keys (the first field in each item) are in [0, RANGE_CHECK_BOUND).
func search_sorted{range_check_ptr}(array_ptr : felt*, elm_size, n_elms, key) -> (
        elm_ptr : felt*, success):
    let (elm_ptr) = search_sorted_lower(
        array_ptr=array_ptr, elm_size=elm_size, n_elms=n_elms, key=key)
    tempvar array_end = array_ptr + elm_size * n_elms
    if elm_ptr == array_end:
        return (elm_ptr=array_ptr, success=0)
    end
    if [elm_ptr] != key:
        return (elm_ptr=array_ptr, success=0)
    end
    return (elm_ptr=elm_ptr, success=1)
end
