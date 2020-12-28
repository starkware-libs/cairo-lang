from dataclasses import field
from typing import ClassVar, Dict, List, Type

import marshmallow
import marshmallow_dataclass

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
        assert addr not in memory, \
            f'Duplicate public memory entries found with the same address: {addr}'
        memory[addr] = value
    return memory


def extract_program_output(public_input: PublicInput, memory: Dict[int, int]) -> List[int]:
    """
    Returns a list of field elements represeting the program output.
    This function fails if the program doesn't have an output segment.
    """
    assert 'output' in public_input.memory_segments, 'Missing output segment.'
    output_addresses = public_input.memory_segments['output']
    assert output_addresses.stop_ptr is not None, 'Missing stop_ptr for the output segment.'
    return [
        memory[addr]
        for addr in range(output_addresses.begin_addr, output_addresses.stop_ptr)]
