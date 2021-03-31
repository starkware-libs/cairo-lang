from typing import Any, Dict, List, Optional

from starkware.cairo.bootloader.compute_fact import generate_program_fact
from starkware.cairo.bootloader.fact_topology import GPS_FACT_TOPOLOGY, FactInfo, FactTopology
from starkware.cairo.bootloader.hash_program import compute_program_hash_chain
from starkware.cairo.lang.vm.cairo_pie import CairoPie
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue


def get_program_output(cairo_pie: CairoPie) -> List[int]:
    """
    Returns the program output.
    """
    assert 'output' in cairo_pie.metadata.builtin_segments, 'The output builtin must be used.'
    output = cairo_pie.metadata.builtin_segments['output']

    def verify_int(x: MaybeRelocatable) -> int:
        assert isinstance(x, int), \
            f'Expected program output to contain absolute values, found: {x}.'
        return x

    return [
        verify_int(cairo_pie.memory[RelocatableValue(segment_index=output.index, offset=i)])
        for i in range(output.size)]


def get_cairo_pie_fact_info(cairo_pie: CairoPie, program_hash: Optional[int] = None) -> FactInfo:
    """
    Generates the fact of the Cairo program of cairo_pie. Returns the cairo-pie fact info.
    """
    program_output = get_program_output(cairo_pie=cairo_pie)
    fact_topology = get_fact_topology_from_additional_data(
        output_size=len(program_output),
        output_builtin_additional_data=cairo_pie.additional_data['output_builtin'])
    if program_hash is None:
        program_hash = get_program_hash(cairo_pie)
    fact = generate_program_fact(program_hash, program_output, fact_topology=fact_topology)
    return FactInfo(program_output=program_output, fact_topology=fact_topology, fact=fact)


def get_program_hash(cairo_pie: CairoPie) -> int:
    return compute_program_hash_chain(cairo_pie.metadata.program)


def get_page_sizes_from_page_dict(output_size: int, pages: dict) -> List[int]:
    """
    Returns the sizes of the program output pages, given the pages dictionary that appears
    in the additional attributes of the output builtin.
    """
    # Make sure the pages are adjacent to each other.

    # The first page id is expected to be 1.
    expected_page_id = 1
    # We don't expect anything on its start value.
    expected_page_start = None
    # The size of page 0 is output_size if there are no other pages, or the start of page 1
    # otherwise.
    page0_size = output_size

    for page_id_str, (page_start, page_size) in sorted(pages.items()):
        page_id = int(page_id_str)
        assert page_id == expected_page_id, f'Expected page id {expected_page_id}, found {page_id}.'
        if page_id == 1:
            assert isinstance(page_start, int) and 0 < page_start <= output_size, \
                f'Invalid page start {page_start}.'
            page0_size = page_start
        else:
            assert page_start == expected_page_start, \
                f'Expected page start {expected_page_start}, found {page_start}.'

        assert isinstance(page_size, int) and 0 < page_size <= output_size, \
            f'Invalid page size {page_size}.'

        expected_page_start = page_start + page_size
        expected_page_id += 1

    if len(pages) > 0:
        assert expected_page_start == output_size, 'Pages must cover the entire program output.'

    return [page0_size] + [page_size for _, (_, page_size) in sorted(pages.items())]


def get_fact_topology_from_additional_data(
        output_size: int, output_builtin_additional_data: Dict[str, Any]) -> FactTopology:
    """
    Returns the fact topology from the additional data of the output builtin.
    """
    pages = output_builtin_additional_data['pages']
    attributes = output_builtin_additional_data['attributes']

    # If the GPS_FACT_TOPOLOGY attribute is present, use it. Otherwise, the task is expected to
    # use exactly one page (page 0).
    if GPS_FACT_TOPOLOGY in attributes:
        tree_structure = attributes[GPS_FACT_TOPOLOGY]
        assert isinstance(tree_structure, list) and \
            len(tree_structure) % 2 == 0 and \
            0 < len(tree_structure) <= 10 and \
            all(isinstance(x, int) and 0 <= x < 2**30 for x in tree_structure), \
            f"Invalid tree structure specified in the '{GPS_FACT_TOPOLOGY}' attribute."
    else:
        assert len(pages) == 0, \
            f"Additional pages cannot be used since the '{GPS_FACT_TOPOLOGY}' attribute is not " \
            'specified.'
        tree_structure = [1, 0]

    return FactTopology(
        tree_structure=tree_structure,
        page_sizes=get_page_sizes_from_page_dict(output_size, pages))
