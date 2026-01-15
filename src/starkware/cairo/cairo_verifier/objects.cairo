// This structure represents the header of the Cairo verifier output for the case where the
// output is hashed.
struct CairoVerifierHashedOutput {
    program_hash: felt,
    output_hash: felt,
}
