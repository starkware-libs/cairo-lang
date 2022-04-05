from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.math import split_felt, unsigned_div_rem
from starkware.cairo.common.uint256 import Uint256

# Computes the keccak hash.
# This function is unsafe (not sound): there is no validity enforcement that the result is indeed
# keccak, but an honest prover will compute the keccak.
# Args:
# data - an array of words representing the input data. Each word in the array is 16 bytes of the
# input data, except the last word, which may be less.
# length - the number of bytes in the input.
func unsafe_keccak(data : felt*, length : felt) -> (low, high):
    alloc_locals
    local low
    local high
    %{
        from eth_hash.auto import keccak

        data, length = ids.data, ids.length

        if '__keccak_max_size' in globals():
            assert length <= __keccak_max_size, \
                f'unsafe_keccak() can only be used with length<={__keccak_max_size}. ' \
                f'Got: length={length}.'

        keccak_input = bytearray()
        for word_i, byte_i in enumerate(range(0, length, 16)):
            word = memory[data + word_i]
            n_bytes = min(16, length - byte_i)
            assert 0 <= word < 2 ** (8 * n_bytes)
            keccak_input += word.to_bytes(n_bytes, 'big')

        hashed = keccak(keccak_input)
        ids.high = int.from_bytes(hashed[:16], 'big')
        ids.low = int.from_bytes(hashed[16:32], 'big')
    %}
    return (low=low, high=high)
end

struct KeccakState:
    member start_ptr : felt*
    member end_ptr : felt*
end

func unsafe_keccak_init() -> (res : KeccakState):
    let (ptr) = alloc()
    return (res=KeccakState(ptr, ptr))
end

func unsafe_keccak_add_felt{keccak_state : KeccakState, range_check_ptr}(num : felt) -> ():
    let (high, low) = split_felt(num)
    keccak_state.end_ptr[0] = high
    keccak_state.end_ptr[1] = low
    let keccak_state = KeccakState(keccak_state.start_ptr, keccak_state.end_ptr + 2)
    return ()
end

func unsafe_keccak_add_uint256{keccak_state : KeccakState, range_check_ptr}(num : Uint256) -> ():
    keccak_state.end_ptr[0] = num.high
    keccak_state.end_ptr[1] = num.low
    let keccak_state = KeccakState(keccak_state.start_ptr, keccak_state.end_ptr + 2)
    return ()
end

func unsafe_keccak_add_felts{keccak_state : KeccakState, range_check_ptr}(
    n_elements : felt, elements : felt*
) -> ():
    if n_elements == 0:
        return ()
    end
    unsafe_keccak_add_felt([elements])
    return unsafe_keccak_add_felts(n_elements=n_elements - 1, elements=elements + 1)
end

# This function is unsafe (not sound): there is no validity enforcement that the result is indeed
# keccak, but an honest prover will compute the keccak.
func unsafe_keccak_finalize(keccak_state : KeccakState) -> (res : Uint256):
    alloc_locals
    local low
    local high
    %{
        from eth_hash.auto import keccak
        keccak_input = bytearray()
        n_elms = ids.keccak_state.end_ptr - ids.keccak_state.start_ptr
        for word in memory.get_range(ids.keccak_state.start_ptr, n_elms):
            keccak_input += word.to_bytes(16, 'big')
        hashed = keccak(keccak_input)
        ids.high = int.from_bytes(hashed[:16], 'big')
        ids.low = int.from_bytes(hashed[16:32], 'big')
    %}
    return (res=Uint256(low=low, high=high))
end

func keccak_felts{range_check_ptr}(n_elements : felt, elements : felt*) -> (res : Uint256):
    let (keccak_state) = unsafe_keccak_init()
    unsafe_keccak_add_felts{keccak_state=keccak_state}(n_elements=n_elements, elements=elements)
    let (res) = unsafe_keccak_finalize(keccak_state=keccak_state)
    return (res=res)
end

# A 160 msb truncated version of keccak, where each value is assumed to also be a truncated
# hash:
#   keccak(x << 96, y << 96) >> 96
func truncated_keccak2{range_check_ptr}(x : felt, y : felt) -> (res : felt):
    let (state) = unsafe_keccak_init()

    let (xhigh, xlow) = unsigned_div_rem(x, 2 ** 32)
    let (yhigh, ylow) = unsigned_div_rem(y, 2 ** 32)
    unsafe_keccak_add_uint256{keccak_state=state}(num=Uint256(low=xlow * 2 ** 96, high=xhigh))
    unsafe_keccak_add_uint256{keccak_state=state}(num=Uint256(low=ylow * 2 ** 96, high=yhigh))
    let (hash) = unsafe_keccak_finalize(keccak_state=state)
    let (low_h, low_l) = unsigned_div_rem(hash.low, 2 ** 96)
    return (res=hash.high * 2 ** 32 + low_h)
end
