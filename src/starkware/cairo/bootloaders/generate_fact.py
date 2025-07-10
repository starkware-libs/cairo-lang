import dataclasses
from typing import List, Optional

from starkware.cairo.bootloaders.aggregator_utils import (
    add_aggregator_prefix,
    get_aggregator_input_size,
)
from starkware.cairo.bootloaders.compute_fact import generate_program_fact
from starkware.cairo.bootloaders.fact_topology import (
    FactInfo,
    get_fact_topology_from_additional_data,
)
from starkware.cairo.bootloaders.hash_program import HashFunction, compute_program_hash_chain
from starkware.cairo.lang.vm.cairo_pie import CairoPie
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue


def get_program_output(cairo_pie: CairoPie) -> List[int]:
    """
    Returns the program output.
    """
    assert "output" in cairo_pie.metadata.builtin_segments, "The output builtin must be used."
    output = cairo_pie.metadata.builtin_segments["output"]

    def verify_int(x: MaybeRelocatable) -> int:
        assert isinstance(
            x, int
        ), f"Expected program output to contain absolute values, found: {x}."
        return x

    return [
        verify_int(cairo_pie.memory[RelocatableValue(segment_index=output.index, offset=i)])
        for i in range(output.size)
    ]


def get_cairo_pie_fact_info(
    cairo_pie: CairoPie,
    program_hash: Optional[int] = None,
    program_output: Optional[List[int]] = None,
    aggregator: bool = False,
) -> FactInfo:
    """
    Generates the fact of the Cairo program of cairo_pie. Returns the cairo-pie fact info.
    """
    if program_output is None:
        program_output = get_program_output(cairo_pie=cairo_pie)

    fact_topology = get_fact_topology_from_additional_data(
        output_size=len(program_output),
        output_builtin_additional_data=cairo_pie.additional_data["output_builtin"],
    )

    if program_hash is None:
        program_hash = get_program_hash(cairo_pie)

    if aggregator:
        # The aggregator program output is composed of the aggregator input (output of the
        # bootloader) and the actual output.
        # The fact is computed based on the actual output, where the aggregator input is ignored.
        aggregator_input_size = get_aggregator_input_size(program_output=program_output)
        program_output = program_output[aggregator_input_size:]
        assert (
            fact_topology.page_sizes[0] >= aggregator_input_size
        ), "Aggregator input must be contained in page 0."
        # Subtract the aggregator input size from the size of page 0.
        fact_topology = dataclasses.replace(
            fact_topology,
            page_sizes=[
                fact_topology.page_sizes[0] - aggregator_input_size,
                *fact_topology.page_sizes[1:],
            ],
        )
        program_hash = add_aggregator_prefix(program_hash)

    fact = generate_program_fact(program_hash, program_output, fact_topology=fact_topology)
    return FactInfo(program_output=program_output, fact_topology=fact_topology, fact=fact)


def get_program_hash(cairo_pie: CairoPie) -> int:
    return compute_program_hash_chain(
        program=cairo_pie.metadata.program, program_hash_function=HashFunction.PEDERSEN
    )
