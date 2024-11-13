from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.copy_indices import copy_indices
from starkware.cairo.common.dict import dict_new, dict_read, dict_squash, dict_update, dict_write
from starkware.cairo.common.dict_access import DictAccess
from starkware.cairo.common.log2_ceil import log2_ceil
from starkware.cairo.common.math import assert_in_range, unsigned_div_rem
from starkware.cairo.common.memcpy import memcpy
from starkware.cairo.common.pow import pow

const COMPRESSION_VERSION = 0;

// Holds the number of elements per unique value bucket.
struct UniqueValueBucketLengths {
    n_252_bit_elms: felt,
    n_125_bit_elms: felt,
    n_83_bit_elms: felt,
    n_62_bit_elms: felt,
    n_31_bit_elms: felt,
    n_15_bit_elms: felt,
}

// Holds decoding info such as the length of each unique values bucket.
struct Header {
    version: felt,
    // Total data length before compression.
    data_len: felt,
    unique_value_bucket_lengths: UniqueValueBucketLengths,
    // Number of elements in the special bucket that holds pointers of repeating vaules.
    n_repeating_values: felt,
}

// The number of buckets, which includes the unique value buckets and the repeating value bucket.
const TOTAL_N_BUCKETS = UniqueValueBucketLengths.SIZE + 1;

// Number of bits for each field of the header.
const HEADER_ELM_N_BITS = 20;
// Number of bits encoding each element (per bucket).
const BUCKET_125_N_BITS = 125;
const BUCKET_83_N_BITS = 83;
const BUCKET_62_N_BITS = 62;
const BUCKET_31_N_BITS = 31;
const BUCKET_15_N_BITS = 15;

// Maximum number of bits that can be packed in one felt.
const MAX_N_BITS_PER_FELT = 251;

// (Max) Number of elements packed in one felt (per bucket).
const BUCKET_125_N_ELMS_PER_FELT = 2;
const BUCKET_83_N_ELMS_PER_FELT = 3;
const BUCKET_62_N_ELMS_PER_FELT = 4;
const BUCKET_31_N_ELMS_PER_FELT = 8;
const BUCKET_15_N_ELMS_PER_FELT = 16;

// Compresses the given data into `compressed_dst`.
// Format (packed in felts - see `unpack` functions):
//   - Header: felt containing decoding info such as the total data length and the length of each
//     bucket (see Header).
//   - Buckets:
//     - Unique value buckets, concatenated by the order in the header.
//     - Repeating value pointers.
//   - Bucket indices: bucket index per element - each is the index of the bucket containing the
//     corresponding uncompressed element.
//
// The buckets preserve the insertion order.
// Thus, to decompress the data:
//   - Unpack the info (unique_values, repeating_value_pointers, bucket_index_per_elm).
//   - Build the repeating_values bucket:
//       `[unique_values[i] for i in repeating_value_pointers]`
//   - Let:
//       `all_values = unique_values + repeating_values`
//   - Calculate the initial bucket offsets.
//   - Reconstruct the data:
//       `[all_values[next(bucket_offsets[bucket_index])] for bucket_index in bucket_index_per_elm]`
//       where `next()` returns the current value and increments it by 1.
//
// Note: a malicious prover might use a non-optimal compression.
func compress{range_check_ptr, compressed_dst: felt*}(data_start: felt*, data_end: felt*) {
    // Guess the compression.
    %{
        from starkware.starknet.core.os.data_availability.compression import compress
        data = memory.get_range_as_ints(addr=ids.data_start, size=ids.data_end - ids.data_start)
        segments.write_arg(ids.compressed_dst, compress(data))
    %}
    // Verify the guess by decompressing it onto the original data array.
    let (decompressed_end) = decompress{compressed=compressed_dst}(decompressed_dst=data_start);

    // Ensure the entire data was reconstructed.
    assert decompressed_end = data_end;
    return ();
}

// Decompresses `compressed` into `decompressed_dst`.
// Returns the decompressed array end.
func decompress{range_check_ptr, compressed: felt*}(decompressed_dst: felt*) -> (
    decompressed_end: felt*
) {
    alloc_locals;
    let header = unpack_header();
    with_attr error_message("Unsupported compression version.") {
        assert header.version = COMPRESSION_VERSION;
    }
    // Unpack and build `all_values`, which is a concatenation of the unique and repeating values.
    let (all_values) = alloc();
    let (n_unique_values) = unpack_unique_values(header=header, unique_values_dst=all_values);
    unpack_repeating_values(
        n_repeating_values=header.n_repeating_values,
        n_unique_values=n_unique_values,
        unique_values=all_values,
        repeating_values_dst=&all_values[n_unique_values],
    );

    let bucket_index_per_elm = unpack_bucket_index_per_elm(header=header);

    // Reconstruct the data into `decompressed_dst`.
    let data_dst = decompressed_dst;
    with data_dst {
        reconstruct_data(
            header=header, all_values=all_values, bucket_index_per_elm=bucket_index_per_elm
        );
    }
    return (decompressed_end=data_dst);
}

// Unpacks the first felt of `compressed` into a `Header` struct.
func unpack_header{range_check_ptr, compressed: felt*}() -> Header* {
    alloc_locals;
    let (local header: Header*) = alloc();
    static_assert Header.SIZE * HEADER_ELM_N_BITS == 180;  // <= 251 bits.
    unpack_felt(
        packed_felt=compressed[0],
        elm_bound=2 ** HEADER_ELM_N_BITS,
        n_elms=Header.SIZE,
        decompressed_dst=cast(header, felt*),
    );
    let compressed = &compressed[1];
    return header;
}

// Unpacks the unique value buckets from `compressed` into `unique_values_dst`.
func unpack_unique_values{range_check_ptr, compressed: felt*}(
    header: Header*, unique_values_dst: felt*
) -> (n_unique_values: felt) {
    alloc_locals;
    let decompressed_dst_start = unique_values_dst;
    let decompressed_dst = decompressed_dst_start;

    let bucket_lengths = header.unique_value_bucket_lengths;
    static_assert UniqueValueBucketLengths.SIZE == 6;

    // Unpack the 252-bit bucket using memcpy.
    local n_252_bit_elms = bucket_lengths.n_252_bit_elms;
    memcpy(dst=decompressed_dst, src=compressed, len=n_252_bit_elms);
    let compressed = &compressed[n_252_bit_elms];
    let decompressed_dst = &decompressed_dst[n_252_bit_elms];

    with decompressed_dst {
        static_assert BUCKET_125_N_BITS * BUCKET_125_N_ELMS_PER_FELT == 250;  // <= 251 bits.
        unpack_felts(
            n_elms=bucket_lengths.n_125_bit_elms,
            elm_bound=2 ** BUCKET_125_N_BITS,
            n_elms_per_felt=BUCKET_125_N_ELMS_PER_FELT,
        );
        static_assert BUCKET_83_N_BITS * BUCKET_83_N_ELMS_PER_FELT == 249;  // <= 251 bits.
        unpack_felts(
            n_elms=bucket_lengths.n_83_bit_elms,
            elm_bound=2 ** BUCKET_83_N_BITS,
            n_elms_per_felt=BUCKET_83_N_ELMS_PER_FELT,
        );
        static_assert BUCKET_62_N_BITS * BUCKET_62_N_ELMS_PER_FELT == 248;  // <= 251 bits.
        unpack_felts(
            n_elms=bucket_lengths.n_62_bit_elms,
            elm_bound=2 ** BUCKET_62_N_BITS,
            n_elms_per_felt=BUCKET_62_N_ELMS_PER_FELT,
        );
        static_assert BUCKET_31_N_BITS * BUCKET_31_N_ELMS_PER_FELT == 248;  // <= 251 bits.
        unpack_felts(
            n_elms=bucket_lengths.n_31_bit_elms,
            elm_bound=2 ** BUCKET_31_N_BITS,
            n_elms_per_felt=BUCKET_31_N_ELMS_PER_FELT,
        );
        static_assert BUCKET_15_N_BITS * BUCKET_15_N_ELMS_PER_FELT == 240;  // <= 251 bits.
        unpack_felts(
            n_elms=bucket_lengths.n_15_bit_elms,
            elm_bound=2 ** BUCKET_15_N_BITS,
            n_elms_per_felt=BUCKET_15_N_ELMS_PER_FELT,
        );
    }
    return (n_unique_values=decompressed_dst - decompressed_dst_start);
}

// Unpacks the repeating value pointers from `compressed`, and writes the actual
// (repeating) values to `repeating_values_dst`.
func unpack_repeating_values{range_check_ptr, compressed: felt*}(
    n_repeating_values: felt,
    n_unique_values: felt,
    unique_values: felt*,
    repeating_values_dst: felt*,
) {
    alloc_locals;
    let pointers = unpack_repeating_value_pointers(
        n_repeating_values=n_repeating_values, n_unique_values=n_unique_values
    );
    // Reconstruct the repeating values.
    // Note that `unpack_repeating_value_pointers` guarantees that each pointer is in the
    // unique_values array range.
    copy_indices(
        dst=repeating_values_dst, src=unique_values, indices=pointers, len=n_repeating_values
    );
    return ();
}

// Unpacks the repeating value pointers from `compressed`.
// Each pointer points to a value in the unique_values and corresponds to the original data element
// at the same position.
// The function guarantees that: each pointer is in range [0, n_unique_values).
func unpack_repeating_value_pointers{range_check_ptr, compressed: felt*}(
    n_repeating_values: felt, n_unique_values: felt
) -> felt* {
    alloc_locals;
    let (local pointers: felt*) = alloc();

    // The pointer bound (unlike the fixed bucket bounds) is dynamically set as the number of
    // unique values.
    let pointer_bound = n_unique_values;
    let n_elms_per_felt = get_n_elms_per_felt(elm_bound=pointer_bound);

    let decompressed_dst = pointers;
    with decompressed_dst {
        unpack_felts(
            n_elms=n_repeating_values, elm_bound=pointer_bound, n_elms_per_felt=n_elms_per_felt
        );
    }
    return pointers;
}

// Unpacks the uncompressed-data bucket indices from `compressed`.
// Each index is of the bucket containing the corresponding data element.
// The function guarantees that: each pointer is in range [0, TOTAL_N_BUCKETS).
func unpack_bucket_index_per_elm{range_check_ptr, compressed: felt*}(header: Header*) -> felt* {
    alloc_locals;
    let (local bucket_index_per_elm: felt*) = alloc();
    let n_elms_per_felt = get_n_elms_per_felt(elm_bound=TOTAL_N_BUCKETS);

    let decompressed_dst = bucket_index_per_elm;
    with decompressed_dst {
        unpack_felts(
            n_elms=header.data_len, elm_bound=TOTAL_N_BUCKETS, n_elms_per_felt=n_elms_per_felt
        );
    }
    return bucket_index_per_elm;
}

// Reconstructs the data into `data_dst`.
func reconstruct_data{range_check_ptr, data_dst: felt*}(
    header: Header*, all_values: felt*, bucket_index_per_elm: felt*
) {
    alloc_locals;
    // Calculate the initial offset (in `all_values`) of each bucket.
    // Unique value buckets.
    let bucket0_offset = 0;
    local bucket1_offset = bucket0_offset + header.unique_value_bucket_lengths.n_252_bit_elms;
    local bucket2_offset = bucket1_offset + header.unique_value_bucket_lengths.n_125_bit_elms;
    local bucket3_offset = bucket2_offset + header.unique_value_bucket_lengths.n_83_bit_elms;
    local bucket4_offset = bucket3_offset + header.unique_value_bucket_lengths.n_62_bit_elms;
    local bucket5_offset = bucket4_offset + header.unique_value_bucket_lengths.n_31_bit_elms;
    // Repeating values bucket.
    local bucket6_offset = bucket5_offset + header.unique_value_bucket_lengths.n_15_bit_elms;

    // Create a dictionary from bucket index (0, 1, ..., 6) to the current offset in `all_values`.
    %{ initial_dict = {bucket_index: 0 for bucket_index in range(ids.TOTAL_N_BUCKETS)} %}
    let (local dict_ptr_start) = dict_new();
    let dict_ptr = dict_ptr_start;
    with dict_ptr {
        // Initialize the bucket offsets.
        static_assert TOTAL_N_BUCKETS == 7;
        dict_write(key=0, new_value=bucket0_offset);
        dict_write(key=1, new_value=bucket1_offset);
        dict_write(key=2, new_value=bucket2_offset);
        dict_write(key=3, new_value=bucket3_offset);
        dict_write(key=4, new_value=bucket4_offset);
        dict_write(key=5, new_value=bucket5_offset);
        dict_write(key=6, new_value=bucket6_offset);

        // Reconstruct the data.
        reconstruct_data_inner(
            data_len=header.data_len,
            all_values=all_values,
            bucket_index_per_elm=bucket_index_per_elm,
        );

        // Verify there was no out-of-bound access to `all_values` array by checking the bucket
        // offset final values.
        dict_update(key=0, prev_value=bucket1_offset, new_value=bucket1_offset);
        dict_update(key=1, prev_value=bucket2_offset, new_value=bucket2_offset);
        dict_update(key=2, prev_value=bucket3_offset, new_value=bucket3_offset);
        dict_update(key=3, prev_value=bucket4_offset, new_value=bucket4_offset);
        dict_update(key=4, prev_value=bucket5_offset, new_value=bucket5_offset);
        dict_update(key=5, prev_value=bucket6_offset, new_value=bucket6_offset);
        tempvar all_values_len = bucket6_offset + header.n_repeating_values;
        dict_update(key=6, prev_value=all_values_len, new_value=all_values_len);
    }
    // Verify the dict reads by squashing the updates.
    // Note that there is no need to verify the initial values:
    // the dict keys are contained in [0, 1, ... TOTAL_N_BUCKETS - 1] since `unpack_pointers`
    // guarantees that each pointer is in this range, and they were all set explicitly above.
    dict_squash(dict_accesses_start=dict_ptr_start, dict_accesses_end=dict_ptr);
    return ();
}

// A helper for `reconstruct_data`.
// The given dict_ptr holds the bucket offsets.
func reconstruct_data_inner{dict_ptr: DictAccess*, data_dst: felt*}(
    data_len: felt, all_values: felt*, bucket_index_per_elm: felt*
) {
    if (data_len == 0) {
        return ();
    }

    let bucket_index = bucket_index_per_elm[0];
    // Guess the offset to the all_values array - it is validated by the `dict_update` below.
    tempvar prev_offset;
    %{
        dict_tracker = __dict_manager.get_tracker(ids.dict_ptr)
        ids.prev_offset = dict_tracker.data[ids.bucket_index]
    %}

    // Advance the bucket offset.
    dict_update(key=bucket_index, prev_value=prev_offset, new_value=prev_offset + 1);

    assert data_dst[0] = all_values[prev_offset];
    let data_dst = &data_dst[1];

    return reconstruct_data_inner(
        data_len=data_len - 1, all_values=all_values, bucket_index_per_elm=&bucket_index_per_elm[1]
    );
}

// Returns the number of elements (smaller than `elm_bound`) that can be packed in one felt.
// The result will satisfy: max(log2(elm_bound), 1) * n_elms_per_felt <= 251.
//
// Note: this calculation may return a sub-optimal result when `elm_bound` is not a power of two:
// it returns: 251 // max(log2_ceil(elm_bound), 1).
func get_n_elms_per_felt{range_check_ptr}(elm_bound: felt) -> felt {
    alloc_locals;
    // If elm_bound is 0 or 1, return MAX_N_BITS_PER_FELT.
    if (elm_bound * (elm_bound - 1) == 0) {
        return MAX_N_BITS_PER_FELT;
    }
    let n_bits_per_elm = log2_ceil(value=elm_bound);
    let (n_elms_per_felt, _) = unsigned_div_rem(value=MAX_N_BITS_PER_FELT, div=n_bits_per_elm);
    return n_elms_per_felt;
}

// Unpacks an array of `n_elms` from `compressed`,
// packed in `ceil(n_elms/n_elms_per_felt)` felts, into `decompressed_dst`.
//
// Assumptions:
//   - elm_bound is in range [0, 2**128).
//   - elm_bound ** n_elms_per_felt <= 2**251.
func unpack_felts{range_check_ptr, compressed: felt*, decompressed_dst: felt*}(
    n_elms: felt, elm_bound: felt, n_elms_per_felt: felt
) {
    alloc_locals;
    let (n_full_felts, local n_remaining_elms) = unsigned_div_rem(
        value=n_elms, div=n_elms_per_felt
    );
    unpack_felts_given_n_packed_felts(
        n_packed_felts=n_full_felts, elm_bound=elm_bound, n_elms_per_felt=n_elms_per_felt
    );
    if (n_remaining_elms != 0) {
        unpack_felts_given_n_packed_felts(
            n_packed_felts=1, elm_bound=elm_bound, n_elms_per_felt=n_remaining_elms
        );
        return ();
    }
    return ();
}

// Unpacks `n_packed_felts` from `compressed` into `decompressed_dst`,
// where each packed felt contains `n_elms_per_felt` elements.
// Assumptions: see `unpack_felts`.
func unpack_felts_given_n_packed_felts{range_check_ptr, compressed: felt*, decompressed_dst: felt*}(
    n_packed_felts: felt, elm_bound: felt, n_elms_per_felt: felt
) {
    if (n_packed_felts == 0) {
        return ();
    }

    unpack_felt(
        packed_felt=compressed[0],
        elm_bound=elm_bound,
        n_elms=n_elms_per_felt,
        decompressed_dst=decompressed_dst,
    );
    let compressed = &compressed[1];
    let decompressed_dst = &decompressed_dst[n_elms_per_felt];
    return unpack_felts_given_n_packed_felts(
        n_packed_felts=n_packed_felts - 1, elm_bound=elm_bound, n_elms_per_felt=n_elms_per_felt
    );
}

// Unpacks `n_elms` from the given felt into `decompressed_dst`.
// The first element is at the least significant bits.
// The function guarantees that: packed_felt < elm_bound ** n_elms.
// Assumptions: see `unpack_felts`.
func unpack_felt{range_check_ptr}(
    packed_felt: felt, elm_bound: felt, n_elms: felt, decompressed_dst: felt*
) {
    if (n_elms == 0) {
        // Verify that there are no more elements to unpack.
        // This check also ensures that the initial `packed_felt` is equal to
        // current0 + current1 * bound + current2 * bound**2 + ... + current(n-1) * bound**(n-1).
        assert packed_felt = 0;
        return ();
    }

    %{ memory[ids.decompressed_dst] = ids.packed_felt % ids.elm_bound %}
    tempvar current = decompressed_dst[0];

    // Verify element is in range [0, elm_bound).
    assert [range_check_ptr] = current;
    assert [range_check_ptr + 1] = elm_bound - current - 1;
    let range_check_ptr = range_check_ptr + 2;

    let packed_suffix = (packed_felt - current) / elm_bound;
    return unpack_felt(
        packed_felt=packed_suffix,
        elm_bound=elm_bound,
        n_elms=n_elms - 1,
        decompressed_dst=&decompressed_dst[1],
    );
}
