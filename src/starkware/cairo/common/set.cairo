from starkware.cairo.common.math import assert_nn_le
from starkware.cairo.common.memcpy import memcpy

const SET_ADD_RANGE_CHECK_USAGE_ON_DUPLICATE = 2
const SET_ADD_RANGE_CHECK_USAGE_ON_NO_DUPLICATE = 0

# Given an array of elements and an element, does one of two things:
# 1. Adds the element to the array.
# 2. Verifies that the element is in the array (all of the fields of the element are equal to all of
#    the fields of one of the array's elements).
#
# Note that this function does not ensure that the elements of the resulted array are distinct
# (from soundness perspective). In other words, from the verifier's perspective, an element may be
# added even if it already existed. (On the other hand, from the prover perspective an element won't
# be added if it already exists).
# This function is usually used in order to avoid long arrays where it doesn't matter if an element
# exists more than once in the array.
#
# Arguments:
# set_ptr - pointer to an array.
# elm_size - size of an element in the array.
# elm_ptr - pointer to an element (of size elm_size) to add to the set.
#
# Implicit arguments:
# range_check_ptr - range check builtin pointer.
# set_end_ptr - pointer to the end of the array.
#
# Assumptions:
# elm_size != 0.
func set_add{range_check_ptr, set_end_ptr : felt*}(set_ptr : felt*, elm_size, elm_ptr : felt*):
    alloc_locals
    local is_elm_in_set
    local index
    %{
        assert ids.elm_size > 0
        assert ids.set_ptr <= ids.set_end_ptr
        elm_list = memory.get_range(ids.elm_ptr, ids.elm_size)
        for i in range(0, ids.set_end_ptr - ids.set_ptr, ids.elm_size):
            if memory.get_range(ids.set_ptr + i, ids.elm_size) == elm_list:
                ids.index = i // ids.elm_size
                ids.is_elm_in_set = 1
                break
        else:
            ids.is_elm_in_set = 0
    %}
    if is_elm_in_set != 0:
        local located_elm_ptr : felt* = set_ptr + elm_size * index
        # Using memcpy for equality assertion.
        memcpy(dst=located_elm_ptr, src=elm_ptr, len=elm_size)
        tempvar n_elms = (cast(set_end_ptr, felt) - cast(set_ptr, felt)) / elm_size
        assert_nn_le(index, n_elms - 1)
        return ()
    else:
        memcpy(dst=set_end_ptr, src=elm_ptr, len=elm_size)
        let set_end_ptr : felt* = set_end_ptr + elm_size
        return ()
    end
end
