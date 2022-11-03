import itertools
from collections import defaultdict
from typing import Dict, List, Mapping, MutableMapping, Tuple

from starkware.cairo.common.hash_state import compute_hash_on_elements
from starkware.cairo.lang.vm.air_public_input import (
    PublicInput,
    PublicMemoryEntry,
    get_pages_and_products,
)
from starkware.cairo.lang.vm.utils import sort_segments
from starkware.python.math_utils import safe_log2


def compute_continuous_page_headers(
    public_memory: List[PublicMemoryEntry],
    z: int,
    alpha: int,
) -> List[Tuple[int, int, int, int, int]]:
    """
    Computes continuous page headers from a list of public memory entries.
    Returns a list of tuples for each page: (start_address, size, hash_low, hash_high, product).
    """
    start_address: Dict[int, int] = {}
    size: MutableMapping[int, int] = defaultdict(int)
    data: Mapping[int, List[int]] = defaultdict(list)

    _, page_prods = get_pages_and_products(public_memory=public_memory, z=z, alpha=alpha)
    for access in public_memory:
        start_address.setdefault(access.page, access.address)
        if access.page == 0:
            continue

        assert access.address == (start_address[access.page] + len(data[access.page]))
        data[access.page].append(access.value)
        size[access.page] += 1
    n_pages = 1 + len(size)
    assert len(page_prods) == n_pages

    headers = []
    for i, page in enumerate(sorted(size), start=1):
        assert i == page
        hash_value = compute_hash_on_elements(data[page])
        headers.append(
            (
                start_address[page],
                size[page],
                hash_value % 2**128,
                hash_value >> 128,
                page_prods[page],
            )
        )

    return headers


def get_main_page(
    public_memory: List[PublicMemoryEntry],
) -> List[Tuple[int, int]]:
    res = []
    for access in public_memory:
        if access.page != 0:
            continue
        res.append((access.address, access.value))
    return res


def public_input_to_cairo(structs, public_input: PublicInput, z: int, alpha: int):
    continuous_page_headers = compute_continuous_page_headers(
        public_memory=public_input.public_memory, z=z, alpha=alpha
    )
    main_page = get_main_page(public_memory=public_input.public_memory)

    memory_segments = sort_segments(public_input.memory_segments)
    cairo_public_input = structs.PublicInput(
        log_n_steps=safe_log2(public_input.n_steps),
        rc_min=public_input.rc_min,
        rc_max=public_input.rc_max,
        layout=int.from_bytes(public_input.layout.encode("ascii"), "big"),
        n_segments=len(public_input.memory_segments),
        segments=list(
            itertools.chain(
                *(
                    structs.SegmentInfo(begin_addr=elm.begin_addr, stop_ptr=elm.stop_ptr)
                    for elm in memory_segments.values()
                )
            )
        ),
        # Public memory.
        padding_addr=public_input.public_memory[0].address,
        padding_value=public_input.public_memory[0].value,
        main_page_len=len(main_page),
        main_page=list(itertools.chain(*main_page)),
        n_continuous_pages=len(continuous_page_headers),
        continuous_page_headers=list(itertools.chain(*continuous_page_headers)),
    )

    return cairo_public_input
