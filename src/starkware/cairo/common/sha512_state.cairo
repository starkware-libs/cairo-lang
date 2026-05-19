// Represents 512 bits of a SHA512 state (8 felts each containing 64 bits).
struct Sha512State {
    s0: felt,
    s1: felt,
    s2: felt,
    s3: felt,
    s4: felt,
    s5: felt,
    s6: felt,
    s7: felt,
}

// Represents 1024 bits of a SHA512 input (16 felts each containing 64 bits).
struct Sha512Input {
    s0: felt,
    s1: felt,
    s2: felt,
    s3: felt,
    s4: felt,
    s5: felt,
    s6: felt,
    s7: felt,
    s8: felt,
    s9: felt,
    s10: felt,
    s11: felt,
    s12: felt,
    s13: felt,
    s14: felt,
    s15: felt,
}

struct Sha512ProcessBlock {
    input: Sha512Input,
    in_state: Sha512State,
    out_state: Sha512State,
}
