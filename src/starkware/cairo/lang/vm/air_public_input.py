import re
from dataclasses import field
from typing import ClassVar, Dict, List, Tuple, Type

import marshmallow
import marshmallow_dataclass

from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.vm.utils import IntAsHex, MemorySegmentAddresses


@marshmallow_dataclass.dataclass
class PublicMemoryEntry:
    address: int
    value: int = field(metadata=dict(marshmallow_field=IntAsHex(required=True)))
    # The public memory may be divided into several chunks, called "pages".
    page: int


@marshmallow_dataclass.dataclass
class PublicInput:
    # The name of the layout (e.g., 'small'), see the LAYOUTS dict in
    # starkware/cairo/lang/instances.py.
    layout: str
    rc_min: int
    rc_max: int
    n_steps: int
    # A map from segment name (e.g., 'execution') to its memory addresses.
    memory_segments: Dict[str, MemorySegmentAddresses]
    public_memory: List[PublicMemoryEntry]
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema


def extract_public_memory(public_input: PublicInput) -> Dict[int, int]:
    """
    Returns a dict from address to value representing the public memory.
    """
    memory = {}
    for entry in public_input.public_memory:
        addr = entry.address
        value = entry.value
        assert (
            addr not in memory
        ), f"Duplicate public memory entries found with the same address: {addr}"
        memory[addr] = value
    return memory


def extract_program_output(public_input: PublicInput, memory: Dict[int, int]) -> List[int]:
    """
    Returns a list of field elements represeting the program output.
    This function fails if the program doesn't have an output segment.
    """
    assert "output" in public_input.memory_segments, "Missing output segment."
    output_addresses = public_input.memory_segments["output"]
    assert output_addresses.stop_ptr is not None, "Missing stop_ptr for the output segment."
    return [memory[addr] for addr in range(output_addresses.begin_addr, output_addresses.stop_ptr)]


def get_pages_and_products(
    public_memory: List[PublicMemoryEntry], z: int, alpha: int
) -> Tuple[Dict[int, List[int]], Dict[int, int]]:
    """
    Rearranges memory entries of the public memory by pages.
    Returns a tuple: (page, page_prods).
    * pages: a dictionary from page id to a list of interleaved addresses and values.
    * page_prods: a dictionary from page_id to the product of the page:
    *   \prod_i (z - (address_i + alpha * value_i))
    """
    pages: Dict[int, List[int]] = {}
    page_prods: Dict[int, int] = {}
    for cell in public_memory:
        page_id, addr, val = cell.page, cell.address, cell.value
        page = pages.setdefault(page_id, [])
        page.append(addr)
        page.append(val)
        page_prods[page_id] = (
            page_prods.get(page_id, 1) * (z - (addr + alpha * val))
        ) % DEFAULT_PRIME
    return pages, page_prods


def extract_z_and_alpha(annotations: List[str]) -> Tuple[int, int]:
    """
    Extracts the interaction elements z and alpha from the proof annotations.
    Returns (z, alpha)
    """
    interaction_elements = [
        int(x, 16)
        for x in re.findall(
            r"V->P: /cpu air/STARK/Interaction: Interaction element #\d+: "
            r"Field Element\(0x([0-9a-f]+)\)",
            "\n".join(annotations),
        )
    ]
    # Make sure the number of interaction_elements is as expected - z, alpha for the memory and
    # z' for the permutation range-check and possibly 3 additional elements for the diluted logic.
    assert len(interaction_elements) in [3, 6]
    z, alpha = interaction_elements[:2]
    return z, alpha
