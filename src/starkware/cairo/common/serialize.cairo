# Appends a single word to the output pointer, and returns the pointer to the next output cell.
func serialize_word(output_ptr : felt*, word) -> (output_ptr : felt*):
    assert [output_ptr] = word
    return (output_ptr + 1)
end

# Array right fold: computes the following:
#   callback(callback(... callback(value, a[n-1]) ..., a[1]), a[0])
# Arguments:
# value - the initial value.
# array - a pointer to an array.
# elm_size - the size of an element in the array.
# n_elms - the number of elements in the array.
# callback - a function pointer to the callback. Expected signature: (felt, T*) -> felt.
func array_rfold(value, array : felt*, n_elms, elm_size, callback) -> (res):
    if n_elms == 0:
        return (value)
    end

    [ap] = value; ap++
    [ap] = array; ap++
    call abs callback
    # We use ..., since we use the result of callback as the value for the next iteration.
    array_rfold(
        ..., array=array + elm_size, n_elms=n_elms - 1, elm_size=elm_size, callback=callback)
    return (...)
end

# Serializes an array of objects to output_ptr, and returns the pointer to the next output cell.
# The format is: len(array) || callback(a[0]) || ... || callback(a[n-1]) .
# Arguments:
# output_ptr - the pointer to serialize to.
# array - a pointer to an array.
# elm_size - the size of an element in the array.
# n_elms - the number of elements in the array.
# callback - a function pointer to the serialize function of a single element.
#   Expected signature: (felt, T*) -> felt.
func serialize_array(output_ptr : felt*, array : felt*, n_elms, elm_size, callback) -> (
        output_ptr : felt*):
    let (output_ptr) = serialize_word(output_ptr, n_elms)
    let (output_ptr : felt*) = array_rfold(
        value=cast(output_ptr, felt),
        array=array,
        n_elms=n_elms,
        elm_size=elm_size,
        callback=callback)
    return (output_ptr)
end
