// This structure represents the header of the Cairo verifier output for the case where the
// output isn't hashed. In this case the actual output follows this header.
struct CairoVerifierOutputHeader {
    program_hash: felt,
    output_len: felt,
}

// This structure represents the header of the Cairo verifier output for the case where the
// output is hashed.
struct CairoVerifierHashedOutput {
    program_hash: felt,
    output_hash: felt,
}
