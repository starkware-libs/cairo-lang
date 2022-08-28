from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_blake2s.blake2s import (
    blake2s_add_felt,
    blake2s_add_felts,
    blake2s_add_uint256_bigend,
    blake2s_bigend,
    blake2s_felts,
)
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.hash import HashBuiltin
from starkware.cairo.common.hash_state import hash_finalize, hash_init, hash_update
from starkware.cairo.common.math import assert_le, assert_nn, assert_nn_le
from starkware.cairo.common.pow import pow
from starkware.cairo.common.uint256 import Uint256
from starkware.cairo.stark_verifier.air.layout import AirWithLayout
from starkware.cairo.stark_verifier.air.public_memory import (
    AddrValue,
    ContinuousPageHeader,
    get_continuous_pages_product,
    get_page_product,
)

struct PublicInput {
    // Base 2 log of the number of steps.
    log_n_steps: felt,
    // Minimum value of range check component.
    rc_min: felt,
    // Maximum value of range check component.
    rc_max: felt,
    // Layout ID.
    layout: felt,
    // Memory segment infos array.
    n_segments: felt,
    segments: SegmentInfo*,

    // Public memory section.
    // Address and value of the padding memory access.
    padding_addr: felt,
    padding_value: felt,

    // Main page.
    main_page_len: felt,
    main_page: AddrValue*,

    // Page header array.
    n_continuous_pages: felt,
    continuous_page_headers: ContinuousPageHeader*,
}

struct SegmentInfo {
    // Start address of the memory segment.
    begin_addr: felt,
    // Stop pointer of the segment - not necessarily the end of the segment.
    stop_ptr: felt,
}

// Computes the hash of the public input, which is used as the initial seed for the Fiat-Shamir
// heuristic.
func public_input_hash{
    range_check_ptr, pedersen_ptr: HashBuiltin*, bitwise_ptr: BitwiseBuiltin*, blake2s_ptr: felt*
}(air: AirWithLayout*, public_input: PublicInput*) -> (res: Uint256) {
    alloc_locals;

    // Main page hash.
    let (hash_state_ptr) = hash_init();
    let (hash_state_ptr) = hash_update{hash_ptr=pedersen_ptr}(
        hash_state_ptr=hash_state_ptr,
        data_ptr=public_input.main_page,
        data_length=public_input.main_page_len * AddrValue.SIZE,
    );
    let (main_page_hash) = hash_finalize{hash_ptr=pedersen_ptr}(hash_state_ptr=hash_state_ptr);

    let (data: felt*) = alloc();
    let data_start = data;
    with data {
        blake2s_add_felt(num=public_input.log_n_steps, bigend=1);
        blake2s_add_felt(num=public_input.rc_min, bigend=1);
        blake2s_add_felt(num=public_input.rc_max, bigend=1);
        blake2s_add_felt(num=public_input.layout, bigend=1);
        // n_segments is not written, it is assumed to be fixed.
        blake2s_add_felts(
            n_elements=public_input.n_segments * SegmentInfo.SIZE,
            elements=public_input.segments,
            bigend=1,
        );
        blake2s_add_felt(num=public_input.padding_addr, bigend=1);
        blake2s_add_felt(num=public_input.padding_value, bigend=1);
        blake2s_add_felt(num=1 + public_input.n_continuous_pages, bigend=1);

        // Main page.
        blake2s_add_felt(num=public_input.main_page_len, bigend=1);
        blake2s_add_felt(num=main_page_hash, bigend=1);

        // Add the rest of the pages.
        add_continuous_page_headers(
            n_pages=public_input.n_continuous_pages, pages=public_input.continuous_page_headers
        );
    }
    // Each word in data is 4 bytes. This is specific to the blake implementation.
    let n_bytes = (data - data_start) * 4;
    let (res) = blake2s_bigend(data=data_start, n_bytes=n_bytes);
    return (res=res);
}

func add_continuous_page_headers{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, data: felt*}(
    n_pages: felt, pages: ContinuousPageHeader*
) {
    if (n_pages == 0) {
        return ();
    }

    blake2s_add_felt(num=pages.start_address, bigend=1);
    blake2s_add_felt(num=pages.size, bigend=1);
    blake2s_add_uint256_bigend(pages.hash);

    return add_continuous_page_headers(n_pages=n_pages - 1, pages=&pages[1]);
}

// Returns the product of all public memory cells.
func get_public_memory_product(public_input: PublicInput*, z: felt, alpha: felt) -> (
    res: felt, total_length: felt
) {
    alloc_locals;
    // Compute total product.
    let (main_page_prod) = get_page_product(
        z=z, alpha=alpha, data_len=public_input.main_page_len, data=public_input.main_page
    );
    let (continuous_pages_prod, continuous_pages_total_length) = get_continuous_pages_product(
        n_pages=public_input.n_continuous_pages, page_headers=public_input.continuous_page_headers
    );
    return (
        res=main_page_prod * continuous_pages_prod,
        total_length=continuous_pages_total_length + public_input.main_page_len,
    );
}

// Returns the ratio between the product of all public memory cells and z^|public_memory|.
// This is the value that needs to be at the memory__multi_column_perm__perm__public_memory_prod
// member expression.
func get_public_memory_product_ratio{range_check_ptr}(
    public_input: PublicInput*, z: felt, alpha: felt, public_memory_column_size: felt
) -> (res: felt) {
    alloc_locals;

    // Compute total product.
    let (pages_product, total_length) = get_public_memory_product(
        public_input=public_input, z=z, alpha=alpha
    );

    // Pad and divide.
    let (numerator) = pow(z, public_memory_column_size);
    tempvar padded_value = z - (public_input.padding_addr + alpha * public_input.padding_value);
    assert_le(total_length, public_memory_column_size);
    let (denominator_pad) = pow(padded_value, public_memory_column_size - total_length);

    return (res=numerator / pages_product / denominator_pad);
}
