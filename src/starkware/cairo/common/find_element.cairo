from starkware.cairo.common.math import (
    assert_le,
    assert_le_felt,
    assert_lt_felt,
    assert_nn_le,
    assert_not_equal,
)

const FIND_ELEMENT_RANGE_CHECK_USAGE = 2;

// Finds an element in the array whose first field is key and returns a pointer
// to this element.
// Since cairo is nondeterministic this is an O(1) operation.
// Note however that if the array has multiple elements with said key the function may return any
// of those elements.
//
// Arguments:
// array_ptr - pointer to an array.
// elm_size - size of an element in the array.
// n_elms - number of element in the array.
// key - key to look for.
//
// Implicit arguments:
// range_check_ptr - range check builtin pointer.
//
// Returns:
// elm_ptr - pointer to an element in the array satisfying [ptr] = key.
//
// Optional hint variables:
// __find_element_index - the index that should be returned. If not specified, the function will
//   return the first index that has the key.
func find_element{range_check_ptr}(array_ptr: felt*, elm_size, n_elms, key) -> (elm_ptr: felt*) {
    alloc_locals;
    local index;
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

    assert_nn_le(a=index, b=n_elms - 1);
    tempvar elm_ptr = array_ptr + elm_size * index;
    assert [elm_ptr] = key;
    return (elm_ptr=elm_ptr);
}

// Given an array sorted by its first field, returns the pointer to the first element in the array
// whose first field is at least key. If no such item exists, returns a pointer to the end of the
// array.
// Assumption: the array is sorted as unsigned numbers.
func search_sorted_lower{range_check_ptr}(array_ptr: felt*, elm_size, n_elms, key) -> (
    elm_ptr: felt*
) {
    alloc_locals;
    local index;
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

    assert_nn_le(a=index, b=n_elms);
    local elm_ptr: felt* = array_ptr + elm_size * index;

    if (index != n_elms) {
        assert_le_felt(a=key, b=[elm_ptr]);
    } else {
        tempvar range_check_ptr = range_check_ptr;
    }

    if (index != 0) {
        assert_lt_felt(a=[elm_ptr - elm_size], b=key);
    }

    return (elm_ptr=elm_ptr);
}

// Given an array sorted by its first field, returns the pointer to the first element in the array
// whose first field is exactly key. If no such item exists, returns an undefined pointer,
// and success=0.
// Assumption: the array is sorted as unsigned numbers.
func search_sorted{range_check_ptr}(array_ptr: felt*, elm_size, n_elms, key) -> (
    elm_ptr: felt*, success: felt
) {
    let (elm_ptr) = search_sorted_lower(
        array_ptr=array_ptr, elm_size=elm_size, n_elms=n_elms, key=key
    );
    tempvar array_end = array_ptr + elm_size * n_elms;
    if (elm_ptr == array_end) {
        return (elm_ptr=array_ptr, success=0);
    }
    if ([elm_ptr] != key) {
        return (elm_ptr=array_ptr, success=0);
    }
    return (elm_ptr=elm_ptr, success=1);
}

// Similar to `search_sorted`, except that it optimizes the case where the key exists.
//
// This optimization is done in a new function for backward compatibility, since it introduces
// new hints.
func search_sorted_optimistic{range_check_ptr}(array_ptr: felt*, elm_size, n_elms, key) -> (
    elm_ptr: felt*, success: felt
) {
    alloc_locals;
    // Index of the first element whose value is at least `key`.
    local index;
    // Indicates whether the key exists.
    local exists;
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
                ids.exists = 1 if memory[array_ptr + elm_size * i] == ids.key else 0
                break
        else:
            ids.index = n_elms
            ids.exists = 0
    %}

    local elm_ptr: felt* = array_ptr + elm_size * index;

    if (exists != 0) {
        // Verify `index` in range `[0, n_elms)` (this implies `n_elms > 0`).
        assert [range_check_ptr] = index;
        assert [range_check_ptr + 1] = (n_elms - 1) - index;
        let range_check_ptr = range_check_ptr + 2;

        assert [elm_ptr] = key;

        // Verify it is the first appearance.
        if (index != 0) {
            assert_not_equal(key, [elm_ptr - elm_size]);
        }
        return (elm_ptr=elm_ptr, success=1);
    }

    // Verify `index` in range `[0, n_elms]`.
    assert [range_check_ptr] = index;
    assert [range_check_ptr + 1] = n_elms - index;
    let range_check_ptr = range_check_ptr + 2;

    // Verify array[index] > key.
    if (index != n_elms) {
        assert_lt_felt(a=key, b=[elm_ptr]);
    } else {
        tempvar range_check_ptr = range_check_ptr;
    }

    // Verify array[index - 1] < key.
    if (index != 0) {
        assert_lt_felt(a=[elm_ptr - elm_size], b=key);
    }

    return (elm_ptr=array_ptr, success=0);
}
