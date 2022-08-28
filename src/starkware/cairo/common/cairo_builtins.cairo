from starkware.cairo.common.ec_point import EcPoint
from starkware.cairo.common.keccak_state import KeccakBuiltinState

// Specifies the hash builtin memory structure.
struct HashBuiltin {
    x: felt,
    y: felt,
    result: felt,
}

// Specifies the signature builtin memory structure.
struct SignatureBuiltin {
    pub_key: felt,
    message: felt,
}

// Specifies the bitwise builtin memory structure.
struct BitwiseBuiltin {
    x: felt,
    y: felt,
    x_and_y: felt,
    x_xor_y: felt,
    x_or_y: felt,
}

// Specifies the EC operation builtin memory structure.
struct EcOpBuiltin {
    p: EcPoint,
    q: EcPoint,
    m: felt,
    r: EcPoint,
}

// Specifies the Keccak builtin memory structure.
struct KeccakBuiltin {
    input: KeccakBuiltinState,
    output: KeccakBuiltinState,
}
