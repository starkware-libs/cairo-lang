from typing import List, Optional, Sequence, Tuple

import cachetools
import pytest

from starkware.cairo.lang.builtins.all_builtins import POSEIDON_BUILTIN, with_suffix
from starkware.cairo.lang.vm.cairo_pie import ExecutionResourcesStone
from starkware.cairo.lang.vm.vm_exceptions import VmException
from starkware.python.test_utils import maybe_raises
from starkware.starknet.core.os.contract_class.compiled_class_hash import (
    compute_compiled_class_hash,
    create_bytecode_segment_structure,
    run_compiled_class_hash,
)
from starkware.starknet.core.os.contract_class.compiled_class_hash_objects import (
    BytecodeLeaf,
    BytecodeSegment,
    BytecodeSegmentedNode,
)
from starkware.starknet.core.os.contract_class.utils import set_class_hash_cache
from starkware.starknet.core.test_contract.test_utils import get_test_compiled_class
from starkware.starknet.services.api.contract_class.contract_class import CompiledClass


def compute_compiled_class_hash_using_cairo(
    compiled_class: CompiledClass, visited_pcs: Optional[Sequence[int]]
) -> Tuple[int, ExecutionResourcesStone]:
    """
    Returns the compiled class hash and the Cairo execution resources.
    """
    runner = run_compiled_class_hash(compiled_class=compiled_class, visited_pcs=visited_pcs)
    _, class_hash = runner.get_return_values(2)
    assert isinstance(class_hash, int)
    return class_hash, runner.get_execution_resources()


CLASS_HASH_WITH_SEGMENTATION = 0x5517AD8471C9AA4D1ADD31837240DEAD9DC6653854169E489A813DB4376BE9C
CLASS_HASH_WITHOUT_SEGMENTATION = 0xB268995DD0EE80DEBFB8718852750B5FD22082D0C729121C48A0487A4D2F64


@pytest.mark.parametrize(
    "compiled_class, expected_hash, expected_n_poseidons",
    [
        (
            get_test_compiled_class(contract_segmentation=False),
            CLASS_HASH_WITHOUT_SEGMENTATION,
            16,
        ),
        (
            get_test_compiled_class(contract_segmentation=True),
            CLASS_HASH_WITH_SEGMENTATION,
            28,
        ),
    ],
)
def test_compiled_class_hash_basic(
    compiled_class: CompiledClass, expected_hash: int, expected_n_poseidons: int
):
    """
    Tests that the hash of a constant contract does not change.
    """
    # Assert that our test Python hash computation is equivalent to static value.
    (
        cairo_computed_compiled_class_hash,
        execution_resources,
    ) = compute_compiled_class_hash_using_cairo(
        compiled_class=compiled_class,
        visited_pcs=None,
    )
    assert expected_hash == cairo_computed_compiled_class_hash, (
        f"Computed compiled class hash: {hex(cairo_computed_compiled_class_hash)} "
        f"does not match the expected value: {hex(expected_hash)}."
    )
    assert (
        execution_resources.builtin_instance_counter[with_suffix(POSEIDON_BUILTIN)]
        == expected_n_poseidons
    )
    cache: cachetools.LRUCache = cachetools.LRUCache(maxsize=10)
    with set_class_hash_cache(cache=cache):
        assert len(cache) == 0

        python_computed_compiled_class_hash: int = compute_compiled_class_hash(
            compiled_class=compiled_class
        )
        assert len(cache) == 1

        assert python_computed_compiled_class_hash == expected_hash, (
            f"Computed compiled class hash: {hex(python_computed_compiled_class_hash)} "
            f"does not match the expected value: {hex(expected_hash)}."
        )


@pytest.mark.parametrize(
    "visited_pcs, expected_n_poseidons, error_message",
    [
        ([], 14, None),
        ([0], 16, None),
        ([0, 2, 3, 6, 9], 24, None),
        ([3], 19, None),
        ([6], 17, None),
        ([3, 5], 22, None),
        ([7], None, "PC 7 was visited, but the beginning of the segment (6) was not"),
        ([5], None, "PC 5 was visited, but the beginning of the segment (3) was not"),
    ],
)
def test_compiled_class_hash_visited_pcs(
    visited_pcs: List[int], expected_n_poseidons: Optional[int], error_message: Optional[str]
):
    compiled_class = get_test_compiled_class(contract_segmentation=True)
    with maybe_raises(expected_exception=VmException, error_message=error_message):
        compiled_class_hash, execution_resources = compute_compiled_class_hash_using_cairo(
            compiled_class=compiled_class, visited_pcs=visited_pcs
        )
        assert compiled_class_hash == CLASS_HASH_WITH_SEGMENTATION
        assert (
            execution_resources.builtin_instance_counter[with_suffix(POSEIDON_BUILTIN)]
            == expected_n_poseidons
        )


def test_create_bytecode_segment_structure():
    segment_structure = create_bytecode_segment_structure(
        bytecode=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10], bytecode_segment_lengths=[3, [1, 1, [1]], 4]
    )
    assert segment_structure == BytecodeSegmentedNode(
        segments=[
            BytecodeSegment(segment_length=3, inner_structure=BytecodeLeaf(data=[1, 2, 3])),
            BytecodeSegment(
                segment_length=3,
                inner_structure=BytecodeSegmentedNode(
                    segments=[
                        BytecodeSegment(segment_length=1, inner_structure=BytecodeLeaf(data=[4])),
                        BytecodeSegment(segment_length=1, inner_structure=BytecodeLeaf(data=[5])),
                        BytecodeSegment(
                            segment_length=1,
                            inner_structure=BytecodeSegmentedNode(
                                segments=[
                                    BytecodeSegment(
                                        segment_length=1, inner_structure=BytecodeLeaf(data=[6])
                                    )
                                ]
                            ),
                        ),
                    ]
                ),
            ),
            BytecodeSegment(segment_length=4, inner_structure=BytecodeLeaf(data=[7, 8, 9, 10])),
        ]
    )

    empty_structure = create_bytecode_segment_structure(bytecode=[], bytecode_segment_lengths=0)
    assert empty_structure == BytecodeLeaf(data=[])

    flat_structure = create_bytecode_segment_structure(bytecode=[1, 2], bytecode_segment_lengths=2)
    assert flat_structure == BytecodeLeaf(data=[1, 2])

    with pytest.raises(AssertionError, match="Invalid length bytecode segment structure"):
        create_bytecode_segment_structure(bytecode=[1, 2], bytecode_segment_lengths=[2, 1])
