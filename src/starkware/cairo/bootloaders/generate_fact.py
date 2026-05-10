import dataclasses
from typing import Any, Dict, List, Optional

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


@dataclasses.dataclass
class CairoPieData:
    """
    Contains some of the data of a CairoPie used in the ambassador to create the fact info.
    """

    program_output: List[int]
    program_hash: int
    additional_data: Dict[str, Any]

    @classmethod
    def from_cairo_pie(
        cls,
        cairo_pie: CairoPie,
        program_hash_function: HashFunction,
        program_output: Optional[List[int]] = None,
        program_hash: Optional[int] = None,
    ) -> "CairoPieData":
        """
        Creates a CairoPieData instance from a CairoPie.
        """
        program_output = (
            program_output
            if program_output is not None
            else get_program_output(cairo_pie=cairo_pie)
        )
        program_hash = (
            program_hash
            if program_hash is not None
            else get_program_hash(cairo_pie=cairo_pie, program_hash_function=program_hash_function)
        )
        return CairoPieData(
            program_output=program_output,
            program_hash=program_hash,
            additional_data=cairo_pie.additional_data,
        )


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
    program_hash_function: HashFunction,
    program_hash: Optional[int] = None,
    program_output: Optional[List[int]] = None,
    aggregator: bool = False,
) -> FactInfo:
    """
    Generates the fact of the Cairo program of cairo_pie. Returns the cairo-pie fact info.
    """
    return get_fact_info_from_cairo_pie_data(
        cairo_pie_data=CairoPieData.from_cairo_pie(
            cairo_pie=cairo_pie,
            program_hash_function=program_hash_function,
            program_output=program_output,
            program_hash=program_hash,
        ),
        aggregator=aggregator,
        program_hash_function=program_hash_function,
    )


def get_fact_info_from_cairo_pie_data(
    cairo_pie_data: CairoPieData, program_hash_function: HashFunction, aggregator: bool = False
) -> FactInfo:
    """
    Generates the fact of the Cairo program of cairo_pie from the cairo_pie_data.
    Returns the cairo-pie fact info.
    """
    program_output = cairo_pie_data.program_output
    program_hash = cairo_pie_data.program_hash
    fact_topology = get_fact_topology_from_additional_data(
        output_size=len(program_output),
        output_builtin_additional_data=cairo_pie_data.additional_data["output_builtin"],
    )

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
        program_hash = add_aggregator_prefix(
            program_hash=program_hash, program_hash_function=program_hash_function
        )

    fact = generate_program_fact(program_hash, program_output, fact_topology=fact_topology)
    return FactInfo(program_output=program_output, fact_topology=fact_topology, fact=fact)


def get_program_hash(
    cairo_pie: CairoPie, program_hash_function: HashFunction = HashFunction.PEDERSEN
) -> int:
    return compute_program_hash_chain(
        program=cairo_pie.metadata.program, program_hash_function=program_hash_function
    )
