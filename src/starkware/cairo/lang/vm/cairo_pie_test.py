import io

from starkware.cairo.lang.compiler.cairo_compile import compile_cairo
from starkware.cairo.lang.vm.cairo_pie import (
    CairoPie, CairoPieMetadata, ExecutionResources, SegmentInfo)
from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.relocatable import RelocatableValue

PRIME = 2 ** 251 + 17 * 2 ** 192 + 1


def test_cairo_pie_serialize_deserialize():
    program = compile_cairo(
        code=[('%builtins output pedersen range_check ecdsa\nmain:\n[ap] = [ap]\n', '')],
        prime=PRIME)
    metadata = CairoPieMetadata(
        program=program.stripped(),
        program_segment=SegmentInfo(0, 10),
        execution_segment=SegmentInfo(1, 20),
        ret_fp_segment=SegmentInfo(6, 12),
        ret_pc_segment=SegmentInfo(7, 21),
        builtin_segments={
            'a': SegmentInfo(4, 15),
        },
        extra_segments=[],
    )
    memory = MemoryDict({
        1: 2,
        RelocatableValue(3, 4): RelocatableValue(6, 7),
    })
    additional_data = {'c': ['d', 3]}
    execution_resources = ExecutionResources(
        n_steps=10,
        builtin_instance_counter={
            'output': 6,
            'pedersen': 3,
        }
    )
    cairo_pie = CairoPie(
        metadata=metadata,
        memory=memory,
        additional_data=additional_data,
        execution_resources=execution_resources
    )

    file = io.BytesIO()
    cairo_pie.to_file(file)
    actual_cairo_pie = CairoPie.from_file(file)

    assert cairo_pie == actual_cairo_pie
