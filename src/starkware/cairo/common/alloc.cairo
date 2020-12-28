# Allocates a new memory segment.
func alloc() -> (ptr):
    %{ memory[ap] = segments.add() %}
    ap += 1
    return (...)
end
