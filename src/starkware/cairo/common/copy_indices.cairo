// Copies len field elements from src to dst at the given indices.
// I.e., dst = [src[i] for i in indices].
func copy_indices(dst: felt*, src: felt*, indices: felt*, len: felt) {
    struct LoopFrame {
        dst: felt*,
        indices: felt*,
    }

    if (len == 0) {
        return ();
    }

    %{ vm_enter_scope({'n': ids.len}) %}
    tempvar frame = LoopFrame(dst=dst, indices=indices);

    loop:
    let frame = [cast(ap - LoopFrame.SIZE, LoopFrame*)];
    assert [frame.dst] = src[[frame.indices]];

    let continue_copying = [ap];
    // Reserve space for continue_copying.
    let next_frame = cast(ap + 1, LoopFrame*);
    next_frame.dst = frame.dst + 1, ap++;
    next_frame.indices = frame.indices + 1, ap++;
    %{
        n -= 1
        ids.continue_copying = 1 if n > 0 else 0
    %}
    static_assert next_frame + LoopFrame.SIZE == ap + 1;
    jmp loop if continue_copying != 0, ap++;
    // Assert that the loop executed len times.
    len = cast(next_frame.indices, felt) - cast(indices, felt);

    %{ vm_exit_scope() %}
    return ();
}
