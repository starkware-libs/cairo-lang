import pytest

from starkware.cairo.lang.compiler.cairo_compile import compile_cairo
from starkware.cairo.lang.vm.cairo_runner import CairoRunner
from starkware.cairo.lang.vm.output_builtin_runner import OutputBuiltinRunner
from starkware.cairo.lang.vm.relocatable import RelocatableValue


@pytest.fixture
def runner_and_output_runner():
    PRIME = 2 ** 251 + 17 * 2 ** 192 + 1
    code = """
func main():
  ret
end
"""
    program = compile_cairo(code=[(code, '')], prime=PRIME, add_start=True)
    runner = CairoRunner(program=program, layout='plain', proof_mode=True)
    runner.initialize_segments()
    output_builtin_runner = runner.builtin_runners['output'] = OutputBuiltinRunner(included=True)
    output_builtin_runner.initialize_segments(runner=runner)
    runner.initialize_main_entrypoint()
    runner.initialize_vm(hint_locals={})
    return runner, output_builtin_runner, output_builtin_runner.base


def test_pages(runner_and_output_runner):
    """
    Tests the add_page() functionality.
    """
    runner, output_builtin_runner, base = runner_and_output_runner
    for i in range(15):
        runner.vm_memory[base + i] = i
    # Add two pages, with page_id 1 and 3.
    output_builtin_runner.add_page(page_id=1, page_start=base + 3, page_size=4)
    output_builtin_runner.add_page(page_id=3, page_start=base + 9, page_size=3)

    # page_start must be in the output segment (base).
    with pytest.raises(AssertionError, match='page_start must be in the output segment'):
        output_builtin_runner.add_page(
            page_id=4, page_start=RelocatableValue(999, 999), page_size=3)

    runner.finalize_segments()

    # A list of output cells and their page id.
    offset_page_pairs = [
        (0, 0), (1, 0), (2, 0),
        (3, 1), (4, 1), (5, 1), (6, 1),
        (7, 0), (8, 0),
        (9, 3), (10, 3), (11, 3),
        (12, 0), (13, 0), (14, 0),
    ]

    assert runner.segments.public_memory_offsets[base.segment_index] == \
        offset_page_pairs

    # Check that get_public_memory_addresses() returns the correct page_id for each value.
    # The program and execution segments are always in page 0.
    segment_offsets = {0: 0, 1: 10, 2: 100}
    assert runner.segments.get_public_memory_addresses(segment_offsets=segment_offsets) == (
        [(i, 0) for i in range(len(runner.program.data))] +  # Program segment.
        [(10, 0)] +  # Execution segment.
        [(100 + offset, page_id) for offset, page_id in offset_page_pairs])  # Output segment.


def test_pages_collision(runner_and_output_runner):
    runner, output_builtin_runner, base = runner_and_output_runner

    for i in range(20):
        runner.vm_memory[base + i] = i
    output_builtin_runner.add_page(page_id=1, page_start=base + 10, page_size=4)
    output_builtin_runner.add_page(page_id=2, page_start=base + 12, page_size=4)
    with pytest.raises(AssertionError, match='Offset 12 was already assigned a page.'):
        output_builtin_runner.finalize_segments(runner=runner)


def test_pages_out_of_bounds(runner_and_output_runner):
    runner, output_builtin_runner, base = runner_and_output_runner

    for i in range(10):
        runner.vm_memory[base + i] = i
    output_builtin_runner.add_page(page_id=1, page_start=base + 3, page_size=5)
    output_builtin_runner.add_page(page_id=2, page_start=base + 7, page_size=4)
    output_builtin_runner.add_page(page_id=3, page_start=base + 11, page_size=2)
    with pytest.raises(AssertionError, match='Page 2 is out of bounds.'):
        output_builtin_runner.finalize_segments(runner=runner)
