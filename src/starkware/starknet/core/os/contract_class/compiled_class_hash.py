from typing import Callable, List, Tuple

from starkware.cairo.lang.vm.crypto import poseidon_hash_many
from starkware.cairo.lang.vm.relocatable import RelocatableValue
from starkware.python.utils import as_non_optional, from_bytes
from starkware.starknet.core.os.contract_class.compiled_class_hash_objects import (
    BytecodeLeaf,
    BytecodeSegment,
    BytecodeSegmentedNode,
    BytecodeSegmentStructure,
)
from starkware.starknet.core.os.contract_class.utils import ClassHashType, class_hash_cache_ctx_var
from starkware.starknet.definitions import constants
from starkware.starknet.public.abi import starknet_keccak
from starkware.starknet.services.api.contract_class.contract_class import (
    CompiledClass,
    CompiledClassEntryPoint,
    EntryPointType,
    NestedIntList,
)


class BytecodeAccessOracle:
    def __init__(self, is_pc_accessed_callback: Callable[[RelocatableValue], bool]):
        self.is_pc_accessed_callback = is_pc_accessed_callback

    def is_segment_used(self, start_pc: RelocatableValue, segment_length: int) -> bool:
        """
        Returns whether the bytecode segment starting at `start_pc` with length `segment_length` is
        used.
        """
        if self.is_pc_accessed_callback(start_pc):
            return True

        # Sanity check: if the first PC of the segment was not accessed, the entire segment
        # should not be accessed as well.
        for i in range(segment_length):
            pc = start_pc + i
            assert not self.is_pc_accessed_callback(pc), (
                f"PC {pc.offset} was visited, "
                f"but the beginning of the segment ({start_pc.offset}) was not"
            )

        return False


def compute_compiled_class_hash(compiled_class: CompiledClass) -> int:
    """
    Computes the compiled class hash.
    """
    cache = class_hash_cache_ctx_var.get()
    if cache is None:
        return _compute_compiled_class_hash_inner(compiled_class=compiled_class)

    compiled_class_bytes = compiled_class.dumps(sort_keys=True).encode()
    key = (ClassHashType.COMPILED_CLASS, starknet_keccak(data=compiled_class_bytes))

    if key not in cache:
        cache[key] = _compute_compiled_class_hash_inner(compiled_class=compiled_class)

    return cache[key]


def compute_hash_on_entry_points(entry_points: List[CompiledClassEntryPoint]) -> int:
    """
    Computes hash on a list of given entry points.
    """
    entry_point_hash_elements: List[int] = []
    for entry_point in entry_points:
        builtins_hash = poseidon_hash_many(
            [
                from_bytes(builtin.encode("ascii"))
                for builtin in as_non_optional(entry_point.builtins)
            ]
        )
        entry_point_hash_elements.extend([entry_point.selector, entry_point.offset, builtins_hash])

    return poseidon_hash_many(entry_point_hash_elements)


def _compute_compiled_class_hash_inner(compiled_class: CompiledClass) -> int:
    # Compute hashes on each component separately.
    external_funcs_hash = compute_hash_on_entry_points(
        entry_points=compiled_class.entry_points_by_type[EntryPointType.EXTERNAL]
    )
    l1_handlers_hash = compute_hash_on_entry_points(
        entry_points=compiled_class.entry_points_by_type[EntryPointType.L1_HANDLER]
    )
    constructors_hash = compute_hash_on_entry_points(
        entry_points=compiled_class.entry_points_by_type[EntryPointType.CONSTRUCTOR]
    )
    bytecode_hash = create_bytecode_segment_structure(
        bytecode=compiled_class.bytecode,
        bytecode_segment_lengths=compiled_class.bytecode_segment_lengths,
    ).hash()

    # Compute total hash by hashing each component on top of the previous one.
    return poseidon_hash_many(
        [
            constants.COMPILED_CLASS_VERSION,
            external_funcs_hash,
            l1_handlers_hash,
            constructors_hash,
            bytecode_hash,
        ]
    )


def create_bytecode_segment_structure(
    bytecode: List[int], bytecode_segment_lengths: NestedIntList
) -> BytecodeSegmentStructure:
    """
    Creates a BytecodeSegmentStructure instance from the given bytecode and
    bytecode_segment_lengths.
    """
    res, total_len = _create_bytecode_segment_structure_inner(
        bytecode=bytecode, bytecode_segment_lengths=bytecode_segment_lengths, bytecode_offset=0
    )
    assert total_len == len(
        bytecode
    ), f"Invalid length bytecode segment structure: {total_len}. Bytecode length: {len(bytecode)}."
    return res


def _create_bytecode_segment_structure_inner(
    bytecode: List[int],
    bytecode_segment_lengths: NestedIntList,
    bytecode_offset: int,
) -> Tuple[BytecodeSegmentStructure, int]:
    """
    Helper function for `create_bytecode_segment_structure`.
    Returns the BytecodeSegmentStructure and the total length of the processed segment.
    """
    if isinstance(bytecode_segment_lengths, int):
        segment_end = bytecode_offset + bytecode_segment_lengths
        return (BytecodeLeaf(data=bytecode[bytecode_offset:segment_end]), bytecode_segment_lengths)

    res = []
    total_len = 0
    for item in bytecode_segment_lengths:
        current_structure, item_len = _create_bytecode_segment_structure_inner(
            bytecode=bytecode, bytecode_segment_lengths=item, bytecode_offset=bytecode_offset
        )
        res.append(BytecodeSegment(segment_length=item_len, inner_structure=current_structure))
        bytecode_offset += item_len
        total_len += item_len

    return BytecodeSegmentedNode(segments=res), total_len
