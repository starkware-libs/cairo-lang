from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.math import assert_lt, assert_nn

# Sorts an array of field elements and removes duplicates.
# Returns the sorted array and an array of multiplicities.
# multiplicities[i] is the number of times that output[i] appeared in input.
# Completeness assumption: All numbers are in [0, RANGE_CHECK_BOUND).
func usort{range_check_ptr}(input_len : felt, input : felt*) -> (
    output_len : felt, output : felt*, multiplicities : felt*
):
    alloc_locals
    local output_len
    local output : felt*
    local multiplicities : felt*
    %{ vm_enter_scope(dict(__usort_max_size = globals().get('__usort_max_size'))) %}
    %{
        from collections import defaultdict

        input_ptr = ids.input
        input_len = int(ids.input_len)
        if __usort_max_size is not None:
            assert input_len <= __usort_max_size, (
                f"usort() can only be used with input_len<={__usort_max_size}. "
                f"Got: input_len={input_len}."
            )

        positions_dict = defaultdict(list)
        for i in range(input_len):
            val = memory[input_ptr + i]
            positions_dict[val].append(i)

        output = sorted(positions_dict.keys())
        ids.output_len = len(output)
        ids.output = segments.gen_arg(output)
        ids.multiplicities = segments.gen_arg([len(positions_dict[k]) for k in output])
    %}

    let output_start = output
    verify_usort{output=output}(
        input_len=input_len, input=input, total_visited=0, multiplicities=multiplicities, prev=-1
    )

    %{ vm_exit_scope() %}
    return (output_len=output - output_start, output=output_start, multiplicities=multiplicities)
end

# Verifies that usort of input is (output, multiplicities). See usort().
func verify_usort{range_check_ptr, output : felt*}(
    input_len : felt, input : felt*, total_visited : felt, multiplicities : felt*, prev : felt
):
    alloc_locals

    if total_visited == input_len:
        return ()
    end

    local value = [output]
    let output = &output[1]
    assert_lt(prev, value)

    local multiplicity = [multiplicities]
    assert_nn(multiplicity - 1)

    %{
        last_pos = 0
        positions = positions_dict[ids.value][::-1]
    %}
    verify_multiplicity(multiplicity=multiplicity, input_len=input_len, input=input, value=value)

    return verify_usort(
        input_len=input_len,
        input=input,
        total_visited=total_visited + multiplicity,
        multiplicities=&multiplicities[1],
        prev=value,
    )
end

# Verifies that value appears at least multiplicity times in input.
func verify_multiplicity{range_check_ptr}(
    multiplicity : felt, input_len : felt, input : felt*, value : felt
):
    if multiplicity == 0:
        %{ assert len(positions) == 0 %}
        assert_nn(input_len)
        return ()
    end

    alloc_locals
    # Skip to the next appearance.
    local next_item_index
    %{
        current_pos = positions.pop()
        ids.next_item_index = current_pos - last_pos
        last_pos = current_pos + 1
    %}
    assert_nn(next_item_index)
    assert input[next_item_index] = value
    return verify_multiplicity(
        multiplicity=multiplicity - 1,
        input_len=input_len - next_item_index - 1,
        input=&input[next_item_index + 1],
        value=value,
    )
end
