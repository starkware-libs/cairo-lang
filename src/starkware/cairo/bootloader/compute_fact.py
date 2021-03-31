import binascii
import dataclasses
from typing import List

from eth_hash.auto import keccak

from starkware.cairo.bootloader.fact_topology import FactTopology


def keccak_ints(values: List[int]) -> str:
    """
    Computes the keccak of a list of ints.
    This function is compatible with
      Web3.solidityKeccak(['uint256[]'], [values]).hex()
    """
    return '0x' + binascii.hexlify(
        keccak(b''.join(value.to_bytes(32, 'big') for value in values))).decode('ascii')


def generate_program_fact(
        program_hash: int, program_output: List[int], fact_topology: FactTopology) -> str:
    """
    Generates the program fact of the Cairo program with program_hash and program_output.
    See GpsOutputParser.sol for more information on the way the fact is computed.
    """
    return keccak_ints([
        program_hash,
        generate_output_root(program_output=program_output, fact_topology=fact_topology).node_hash
    ])


@dataclasses.dataclass
class FactNode:
    node_hash: int
    end_offset: int
    size: int
    children: List['FactNode']


def generate_output_root(
        program_output: List[int], fact_topology: FactTopology) -> FactNode:
    """
    Generates the root of the output Merkle tree for the program fact computation.
    See GpsOutputParser.sol for more information on the way the fact is computed.
    """
    # Create a copy of page_sizes.
    page_sizes = list(fact_topology.page_sizes)
    tree_structure = fact_topology.tree_structure
    offset = 0
    node_stack: List[FactNode] = []
    for n_pages, n_nodes in zip(tree_structure[::2], tree_structure[1::2]):
        # Push n_pages to the stack.
        assert 0 <= n_pages <= len(page_sizes), 'Invalid tree structure: n_pages is out of range.'
        for _ in range(n_pages):
            page_size = page_sizes.pop(0)
            page_hash = int(keccak_ints(program_output[offset:offset + page_size]), 16)

            offset += page_size

            node_stack.append(FactNode(
                node_hash=page_hash, end_offset=offset, size=page_size, children=[]))

        assert 0 <= n_nodes <= len(node_stack), 'Invalid tree structure: n_nodes is out of range.'
        if n_nodes > 0:
            # Create a parent node to the last n_nodes in the head of the stack.
            node_stack, child_nodes = node_stack[:-n_nodes], node_stack[-n_nodes:]
            # Create an alternating list of hashes and end offsets.
            node_data = [val for node in child_nodes for val in [node.node_hash, node.end_offset]]
            node_stack.append(FactNode(
                node_hash=1 + int(keccak_ints(node_data), 16),
                end_offset=child_nodes[-1].end_offset,
                size=sum(node.size for node in child_nodes),
                children=child_nodes))

    # Make sure there is one node in the stack (hash and end).
    assert len(node_stack) == 1, 'Invalid tree structure: stack contains more than one node.'
    # Make sure all pages were processed.
    assert len(page_sizes) == 0, 'Invalid tree structure: not all pages were processed.'
    assert offset == node_stack[0].end_offset == len(program_output)

    return node_stack[0]
