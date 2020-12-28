# Copies len field elements from src to dst.
func memcpy(dst : felt*, src : felt*, len):
    struct LoopFrame:
        member dst : felt* = 0
        member src : felt* = 1
        const SIZE = 2
    end

    if len == 0:
        return ()
    end

    let frame = cast(ap, LoopFrame*)
    %{ vm_enter_scope({'n': ids.len}) %}
    frame.dst = dst; ap++
    frame.src = src; ap++

    loop:
    let frame = cast(ap - LoopFrame.SIZE, LoopFrame*)
    assert [frame.dst] = [frame.src]

    let continue_copying = [ap]
    # Reserve space for continue_copying.
    let next_frame = cast(ap + 1, LoopFrame*)
    next_frame.dst = frame.dst + 1; ap++
    next_frame.src = frame.src + 1; ap++
    %{
        n -= 1
        ids.continue_copying = 1 if n > 0 else 0
    %}
    static_assert next_frame + LoopFrame.SIZE == ap + 1
    jmp loop if continue_copying != 0; ap++
    # Assert that the loop executed len times.
    len = cast(next_frame.src, felt) - cast(src, felt)

    %{ vm_exit_scope() %}
    return ()
end
