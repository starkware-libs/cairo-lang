# Writes value into [dst + 0], ..., [dst + n - 1].
func memset(dst : felt*, value : felt, n):
    struct LoopFrame:
        member dst : felt*
    end

    if n == 0:
        return ()
    end

    %{ vm_enter_scope({'n': ids.n}) %}
    tempvar frame = LoopFrame(dst=dst)

    loop:
    let frame = [cast(ap - LoopFrame.SIZE, LoopFrame*)]
    assert [frame.dst] = value

    let continue_loop = [ap]
    # Reserve space for continue_loop.
    let next_frame = cast(ap + 1, LoopFrame*)
    next_frame.dst = frame.dst + 1; ap++
    %{
        n -= 1
        ids.continue_loop = 1 if n > 0 else 0
    %}
    static_assert next_frame + LoopFrame.SIZE == ap + 1
    jmp loop if continue_loop != 0; ap++
    # Assert that the loop executed n times.
    n = cast(next_frame.dst, felt) - cast(dst, felt)

    %{ vm_exit_scope() %}
    return ()
end
