# Allocates a new memory segment.
func alloc() -> (ptr : felt*):
    %{ memory[ap] = segments.add() %}
    ap += 1
    return (ptr=cast([ap - 1], felt*))
end
