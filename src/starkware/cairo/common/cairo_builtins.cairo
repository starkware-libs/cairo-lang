from starkware.cairo.common.ec_point import EcPoint

# Specifies the hash builtin memory structure.
struct HashBuiltin:
    member x : felt
    member y : felt
    member result : felt
end

# Specifies the signature builtin memory structure.
struct SignatureBuiltin:
    member pub_key : felt
    member message : felt
end

# Specifies the bitwise builtin memory structure.
struct BitwiseBuiltin:
    member x : felt
    member y : felt
    member x_and_y : felt
    member x_xor_y : felt
    member x_or_y : felt
end

# Specifies the EC operation builtin memory structure.
struct EcOpBuiltin:
    member p : EcPoint
    member q : EcPoint
    member m : felt
    member r : EcPoint
end
