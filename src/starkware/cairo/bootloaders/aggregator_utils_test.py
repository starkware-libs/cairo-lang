from starkware.cairo.bootloaders.aggregator_utils import get_aggregator_input_size


def test_get_aggregator_input_size():
    # Create an aggregator input (bootloader output) with 2 tasks with output sizes 4 and 3.
    aggregator_input = [2] + [4, 100, 100, 100] + [3, 100, 100]
    aggregator_output = [100, 100, 100, 100]
    assert get_aggregator_input_size(program_output=aggregator_input + aggregator_output) == len(
        aggregator_input
    )
