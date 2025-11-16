# Library to implement array operations.

from starkware.cairo.common.alloc import alloc

# Compute the sum of the element in an array.
# Args:
#   input_len - length of the felt array.
#   input - felt array.
# Returns:
#   output - felt with the sum of each element of the array.
func sum(input_len : felt, input : felt*) -> (output : felt):
    if input_len == 0:
        return(0)
    end
    let (output) = sum(input_len - 1, input + 1) 
    return(output + [input])
end

# Compute the arithmetic mean along the array.
# Args:
#   input_len - length of the felt array.
#   input - felt array.
# Returns:
#   output - arithmetic mean.
func mean(input_len : felt, input : felt*) -> (output : felt):
    let (s) = sum(input_len, input)
    return(s / input_len)
end

# Compute the scalar multiplication of an array.
# Args:
#   input_len - length of the felt array.
#   scalar - felt that multiplies the array.
#   input - felt array.
# Returns:
#   output - scalar product felt.
func scalar_product(input_len : felt, scalar : felt, input : felt*) -> (output : felt):    
    if input_len == 0:
        return(0)
    end
    let (d) = scalar_product(input_len - 1, scalar, input + 1)
    return (scalar * [input] + d) 
end

# Compute the median along the array.
# Args:
#   input_len - length of the felt array.
#   vs - felt array.
# Returns:
#   output - median.
func median(input_len : felt, input : felt*) -> (med : felt):
    tempvar is_even : felt
    %{
        ids.is_even = 1 if (ids.input_len % 2 == 0) else 0
    %}
    if is_even == 1:
        return(input[input_len / 2])
    else:
        tempvar a = input[((input_len - 1) / 2) - 1]
        tempvar b = input[((input_len + 1) / 2) - 1]
        return((a + b) / 2)
    end
end

# Compute the dot product of two arrays.
# Args:
#   input_len - length of the felt arrays. If they do not have the same length an error will appear.
#   input1 - first felt array.
#   input2 - second felt array.
# Returns:
#   output - dot product felt.
func dot(input_len : felt, input1 : felt*, input2 : felt*) -> (output : felt):    
    if input_len == 1:
        return(0)
    end
    let (d) = dot(input_len - 1, input1 + 1, input2 + 1)
    return ([input1] * [input2] + d) 
end

# Obtain the minimum value in an array.
# Args:
#   input_len - length of the felt array.
#   input - felt array.
# Returns:
#   output - minimum value.
func min(input_len : felt, input : felt*) -> (output : felt):
    if input_len == 0:
        return (input[0])
    end
    let (input_len_prev) = min(input_len - 1, input)
    let min_prev = input[input_len - 1]
    tempvar output : felt
    %{
        ids.output = min(ids.input_len_prev, ids.min_prev)
    %}
    return(output)
end

# Obtain the maximum value in an array.
# Args:
#   input_len - length of the felt array.
#   input - felt array.
# Returns:
#   output - maximum value.
func max(input_len : felt, input : felt*) -> (output : felt):
    if input_len == 0:
        return (input[0])
    end
    let (input_len_prev) = max(input_len - 1, input)
    let max_prev = input[input_len - 1]
    tempvar output : felt
    %{
        ids.output = max(ids.input_len_prev, ids.max_prev)
    %}
    return(output)
end
