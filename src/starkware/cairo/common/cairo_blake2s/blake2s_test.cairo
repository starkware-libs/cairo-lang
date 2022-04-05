%builtins range_check bitwise

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_blake2s.blake2s import INSTANCE_SIZE, blake2s, finalize_blake2s
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin

func run_blake2s{range_check_ptr, blake2s_ptr : felt*}(inputs : felt**, lengths : felt*, n : felt):
    if n == 0:
        return ()
    end

    blake2s(inputs[0], lengths[0])
    return run_blake2s(inputs + 1, lengths + 1, n - 1)
end

func run_blake2s_and_finalize{range_check_ptr, bitwise_ptr : BitwiseBuiltin*}(
    inputs : felt**, lengths : felt*, n : felt
):
    alloc_locals
    let (local blake2s_ptr_start) = alloc()
    let blake2s_ptr = blake2s_ptr_start

    run_blake2s{blake2s_ptr=blake2s_ptr}(inputs, lengths, n)
    finalize_blake2s(blake2s_ptr_start=blake2s_ptr_start, blake2s_ptr_end=blake2s_ptr)
    return ()
end
