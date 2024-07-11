// Represents 256 bits of a SHA256 state (8 felts each containing 32 bits).
struct Sha256State {
    s0: felt,
    s1: felt,
    s2: felt,
    s3: felt,
    s4: felt,
    s5: felt,
    s6: felt,
    s7: felt,
}

// Represents 512 bits of a SHA256 input (16 felts each containing 32 bits).
struct Sha256Input {
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

struct Sha256ProcessBlock {
    input: Sha256Input,
    in_state: Sha256State,
    out_state: Sha256State,
}
