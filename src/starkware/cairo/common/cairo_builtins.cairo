from starkware.cairo.common.ec_point import EcPoint
from starkware.cairo.common.keccak_state import KeccakBuiltinState
from starkware.cairo.common.poseidon_state import PoseidonBuiltinState

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

// Specifies the Poseidon builtin memory structure.
struct PoseidonBuiltin {
    input: PoseidonBuiltinState,
    output: PoseidonBuiltinState,
}

// Represents a 384-bit unsigned integer d0 + 2**96 * d1 + 2**192 * d2 + 2**288 * d3
// where each di is in [0, 2**96).
struct UInt384 {
    d0: felt,
    d1: felt,
    d2: felt,
    d3: felt,
}

// Specifies the Add and Mul Mod builtins memory structure.
struct ModBuiltin {
    // The modulus.
    p: UInt384,
    // A pointer to input values, the intermediate results and the output.
    values_ptr: UInt384*,
    // A pointer to offsets inside the values array, defining the circuit.
    // The offsets array should contain 3 * n elements.
    offsets_ptr: felt*,
    // The number of operations to perform.
    n: felt,
}
