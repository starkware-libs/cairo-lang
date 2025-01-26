import itertools
from itertools import count
from typing import Dict, Iterator, List, Tuple

from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.python.math_utils import log2_ceil
from starkware.python.utils import div_ceil, iter_blockify, safe_zip

COMPRESSION_VERSION = 0

# Max number of bits that can be packed in a single felt.
MAX_N_BITS = 251

# Number of bits encoding each element (per bucket).
N_BITS_PER_BUCKET = [252, 125, 83, 62, 31, 15]
N_UNIQUE_VALUE_BUCKETS = len(N_BITS_PER_BUCKET)
# Number of buckets, including the repeating values bucket.
TOTAL_N_BUCKETS = N_UNIQUE_VALUE_BUCKETS + 1

# Version, data length, bucket lengths.
HEADER_LEN = 1 + 1 + TOTAL_N_BUCKETS

HEADER_ELM_N_BITS = 20
HEADER_ELM_BOUND = 2**HEADER_ELM_N_BITS


class UniqueValueBucket:
    """
    A set-like data structure that preserves the insertion order.
    Holds values of `n_bits` bit length or less.
    """

    def __init__(self, n_bits: int):
        self.n_bits = n_bits
        # A mapping from value to its insertion order.
        self._value_to_index: Dict[int, int] = {}

    def __contains__(self, value: int) -> bool:
        return value in self._value_to_index

    def __len__(self) -> int:
        return len(self._value_to_index)

    def add(self, value: int):
        if value in self:
            return
        next_index = len(self._value_to_index)
        self._value_to_index[value] = next_index

    def get_index(self, value: int) -> int:
        return self._value_to_index[value]

    def pack_in_felts(self) -> List[int]:
        # The values should be sorted by the insertion order, but this is given for free since
        # Python dict preserves order.
        values = list(self._value_to_index.keys())
        return pack_in_felts(elms=values, elm_bound=2**self.n_bits)


class CompressionSet:
    """
    A utility class for compression.
    Used to manage and store the unique values in seperate buckets according to their bit length.
    """

    def __init__(self, n_bits_per_bucket: List[int]):
        self._buckets = [UniqueValueBucket(n_bits=n_bits) for n_bits in n_bits_per_bucket]
        # Index by the given order.
        indexed_buckets = list(enumerate(self._buckets))
        # Sort by the number of bits (cached for the `update` function).
        self._sorted_buckets = sorted(
            indexed_buckets, key=lambda indexed_bucket: indexed_bucket[1].n_bits
        )

        # A special bucket that holds locations of the unique values in the buckets, in the
        # following form: (bucket_index, index_in_bucket).
        # Each corresponds to a repeating value and is the location of the first (unique) copy.
        self._repeating_value_locations: List[Tuple[int, int]] = []

        # Maps each item to the bucket it was assigned, including the repeating values bucket.
        self._bucket_index_per_elm: List[int] = []

        self.finalized = False

    @property
    def repeating_values_bucket_index(self) -> int:
        return len(self._buckets)

    def update(self, values: List[int]):
        assert not self.finalized, "Cannot add values after finalizing."
        for value in values:
            for bucket_index, bucket in self._sorted_buckets:
                if value.bit_length() <= bucket.n_bits:
                    if value in bucket:
                        # Repeated value; add the location of the first added copy.
                        self._repeating_value_locations.append(
                            (bucket_index, bucket.get_index(value))
                        )
                        self._bucket_index_per_elm.append(self.repeating_values_bucket_index)
                    else:
                        # First appearance of this value.
                        bucket.add(value)
                        self._bucket_index_per_elm.append(bucket_index)
                    break
            else:
                raise ValueError(f"{value} is too large.")

    def get_unique_value_bucket_lengths(self) -> List[int]:
        return [len(bucket) for bucket in self._buckets]

    def get_repeating_value_bucket_length(self) -> int:
        return len(self._repeating_value_locations)

    def get_repeating_value_pointers(self) -> List[int]:
        """
        Returns a list of pointers corresponding to the repeating values.
        The pointers point to the chained unique value buckets.
        """
        assert self.finalized, "Cannot get pointers before finalizing."
        unique_value_bucket_lengths = self.get_unique_value_bucket_lengths()
        bucket_offsets = get_bucket_offsets(bucket_lengths=unique_value_bucket_lengths)
        return [
            bucket_offsets[bucket_index] + index_in_bucket
            for bucket_index, index_in_bucket in self._repeating_value_locations
        ]

    def get_bucket_index_per_elm(self) -> List[int]:
        """
        Returns the bucket indices of the added values.
        """
        assert self.finalized, "Cannot get bucket_index_per_elm before finalizing."
        return self._bucket_index_per_elm

    def pack_unique_values(self) -> List[int]:
        """
        Packs the unique value buckets and chains them.
        """
        assert self.finalized, "Cannot pack before finalizing."
        return list(itertools.chain(*(bucket.pack_in_felts() for bucket in self._buckets)))

    def finalize(self):
        self.finalized = True


def compress(data: List[int]) -> List[int]:
    """
    Compresses the given data.
    The result is a list of felts.
    """
    assert len(data) < HEADER_ELM_BOUND, "Data is too long."
    compression_set = CompressionSet(n_bits_per_bucket=N_BITS_PER_BUCKET)
    compression_set.update(data)
    compression_set.finalize()

    bucket_index_per_elm = compression_set.get_bucket_index_per_elm()

    unique_value_bucket_lengths = compression_set.get_unique_value_bucket_lengths()
    n_unique_values = sum(unique_value_bucket_lengths)
    header = [
        COMPRESSION_VERSION,
        len(data),
        *unique_value_bucket_lengths,
        compression_set.get_repeating_value_bucket_length(),
    ]
    packed_header = pack_in_felt(elms=header, elm_bound=HEADER_ELM_BOUND)
    packed_repeating_value_pointers = pack_in_felts(
        elms=compression_set.get_repeating_value_pointers(), elm_bound=n_unique_values
    )
    packed_bucket_index_per_elm = pack_in_felts(
        elms=bucket_index_per_elm, elm_bound=TOTAL_N_BUCKETS
    )

    return [
        packed_header,
        *compression_set.pack_unique_values(),
        *packed_repeating_value_pointers,
        *packed_bucket_index_per_elm,
    ]


def decompress(compressed: Iterator[int]) -> List[int]:
    """
    Decompresses the given compressed data.
    """
    assert isinstance(compressed, Iterator), f"Expected iterator, got: {type(compressed).__name__}."

    def unpack_chunk(n_elms: int, elm_bound: int) -> List[int]:
        n_packed_felts = div_ceil(n_elms, get_n_elms_per_felt(elm_bound))
        compressed_chunk = list(itertools.islice(compressed, n_packed_felts))
        return unpack_felts(compressed=compressed_chunk, elm_bound=elm_bound, n_elms=n_elms)

    header = unpack_chunk(n_elms=HEADER_LEN, elm_bound=HEADER_ELM_BOUND)
    # Unpack header.
    version = header[0]
    assert version == COMPRESSION_VERSION, f"Unsupported compression version {version}."
    data_len = header[1]
    unique_value_bucket_lengths = header[2 : 2 + N_UNIQUE_VALUE_BUCKETS]
    (n_repeating_values,) = header[2 + N_UNIQUE_VALUE_BUCKETS :]

    # Unpack buckets: unique values and repeating values.
    unique_values = list(
        itertools.chain(
            *(
                unpack_chunk(n_elms=bucket_length, elm_bound=2**n_bits)
                for bucket_length, n_bits in safe_zip(
                    unique_value_bucket_lengths, N_BITS_PER_BUCKET
                )
            )
        )
    )
    repeating_value_pointers = unpack_chunk(n_elms=n_repeating_values, elm_bound=len(unique_values))
    repeating_values = [unique_values[i] for i in repeating_value_pointers]
    all_values = unique_values + repeating_values

    # Unpack the bucket indices.
    bucket_index_per_elm = unpack_chunk(n_elms=data_len, elm_bound=TOTAL_N_BUCKETS)

    # Get the starting position of each bucket.
    all_bucket_lengths = [*unique_value_bucket_lengths, n_repeating_values]
    bucket_offsets = get_bucket_offsets(bucket_lengths=all_bucket_lengths)

    # Reconstruct the data.
    bucket_offset_iterators = [count(start=offset) for offset in bucket_offsets]
    return [
        all_values[next(bucket_offset_iterators[bucket_index])]
        for bucket_index in bucket_index_per_elm
    ]


def pack_in_felts(elms: List[int], elm_bound: int) -> List[int]:
    """
    Packs the given elements in multiple felts.
    """
    assert all(elm < elm_bound for elm in elms), "Element out of bound."
    return [
        pack_in_felt(elms=chunk, elm_bound=elm_bound)
        for chunk in iter_blockify(elms, chunk_size=get_n_elms_per_felt(elm_bound))
    ]


def unpack_felts(compressed: List[int], elm_bound: int, n_elms: int) -> List[int]:
    """
    Unpacks the given packed felts into an array of `n_elms` elements.
    """
    n_elms_per_felt = get_n_elms_per_felt(elm_bound)
    res = itertools.chain(
        *(
            unpack_felt(packed_felt=packed_felt, elm_bound=elm_bound, n_elms=n_elms_per_felt)
            for packed_felt in compressed
        )
    )
    # Remove trailing zeros.
    return list(res)[:n_elms]


def pack_in_felt(elms: List[int], elm_bound: int) -> int:
    """
    Packs the given elements in a single felt.
    The first element is at the least significant bits.
    """
    res = sum(elm * (elm_bound**i) for i, elm in enumerate(elms))
    assert res < DEFAULT_PRIME, "Out of bound packing."
    return res


def unpack_felt(packed_felt: int, elm_bound: int, n_elms: int) -> List[int]:
    res = []
    for _ in range(n_elms):
        packed_felt, current = divmod(packed_felt, elm_bound)
        res.append(current)

    assert packed_felt == 0
    return res


def get_n_elms_per_felt(elm_bound: int) -> int:
    if elm_bound <= 1:
        return MAX_N_BITS
    if elm_bound > 2**MAX_N_BITS:
        return 1

    return MAX_N_BITS // log2_ceil(elm_bound)


def get_bucket_offsets(bucket_lengths: List[int]) -> List[int]:
    """
    Returns the starting position of each bucket given their lengths.
    """
    return [sum(bucket_lengths[:i]) for i in range(len(bucket_lengths))]
