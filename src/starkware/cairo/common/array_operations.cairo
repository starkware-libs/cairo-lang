# Library to implement array operations.

from starkware.cairo.common.alloc import alloc

# Compute the sum of the element in an array.
# Args:
#   n - length of the felt array.
#   vs - felt array.
# Returns:
#   s - felt with the sum of each element of the array.
func sum(n: felt, vs : felt*) -> (s : felt):
    if n == 0:
        return(s=0)
    end
    let (s) = sum(n = n-1, vs = vs + 1) 
    return(s + [vs])
end

# Compute the arithmetic mean along the array.
# Args:
#   n - length of the felt array.
#   vs - felt array.
# Returns:
#   m - arithmetic mean.
func mean(n : felt, vs : felt*) -> (m : felt):
    let (s) = sum(n = n, vs = vs)
    return(s / n)
end

# Compute the scalar multiplication of an array.
# Args:
#   n - length of the felt array.
#   scalar - felt that multiplies the array.
#   vs - felt array.
# Returns:
#   d - scalar product felt.
func scalar_product(n : felt, scalar : felt, vs : felt*) -> (d : felt):    
    if n == 0:
        return(d=0)
    end
    let (d) = scalar_product(n-1, scalar, vs + 1)
    return (scalar * [vs] + d) 
end

# Compute the median along the array.
# Args:
#   n - length of the felt array.
#   vs - felt array.
# Returns:
#   m - median.
func median(n : felt, vs : felt*) -> (med : felt):
    tempvar is_even : felt
    %{
        ids.is_even = 1 if (ids.n % 2 == 0) else 0
    %}
    if is_even == 1:
        return(vs[n/2])
    else:
        tempvar a = vs[((n-1)/2)-1]
        tempvar b = vs[((n+1)/2)-1]
        return((a+b)/2)
    end
end

# Compute the dot product of two arrays.
# Args:
#   n - length of the felt arrays. If they do not have the same length an error will appear.
#   vs1 - first felt array.
#   vs2 - second felt array.
# Returns:
#   d - dot product felt.
func dot(n : felt, vs1 : felt*, vs2 : felt*) -> (d : felt):    
    if n == 1:
        return(d=0)
    end
    let (d) = dot(n-1, vs1 + 1, vs2 + 1)
    return ([vs1] * [vs2] + d) 
end

# Obtain the minimum value in an array.
# Args:
#   n - length of the felt array.
#   vs - felt array.
# Returns:
#   m - minimum value.
func min(n : felt, vs : felt*) -> (m : felt):
    if n == 0:
        return (vs[0])
    end
    let (n_prev) = min(n-1, vs)
    let min_prev = vs[n-1]
    tempvar m : felt
    %{
        ids.m = min(ids.n_prev, ids.min_prev)
    %}
    return(m)
end

# Obtain the maximum value in an array.
# Args:
#   n - length of the felt array.
#   vs - felt array.
# Returns:
#   m - maximum value.
func max(n : felt, vs : felt*) -> (m : felt):
    if n == 0:
        return (vs[0])
    end
    let (n_prev) = max(n-1, vs)
    let max_prev = vs[n-1]
    tempvar m : felt
    %{
        ids.m = max(ids.n_prev, ids.max_prev)
    %}
    return(m)
end
