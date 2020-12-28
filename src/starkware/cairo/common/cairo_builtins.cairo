# A representation of a HashBuiltin struct, specifying the hash builtin memory structure.
struct HashBuiltin:
    member x = 0
    member y = 1
    member result = 2
    const SIZE = 3
end

# A representation of a SignatureBuiltin struct, specifying the signature builtin memory structure.
struct SignatureBuiltin:
    member pub_key = 0
    member message = 1
    const SIZE = 2
end

# A representation of a CheckpointsBuiltin struct, specifying the checkpoints builtin memory
# structure.
struct CheckpointsBuiltin:
    member required_pc = 0
    member required_fp = 1
    const SIZE = 2
end
