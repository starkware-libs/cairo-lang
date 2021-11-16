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
