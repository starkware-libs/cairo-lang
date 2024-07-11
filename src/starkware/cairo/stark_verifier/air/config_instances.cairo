from starkware.cairo.stark_verifier.core.table_commitment import TableCommitmentConfig

const MAX_N_COLUMNS = 128;

// Configuration for the Traces component.
struct TracesConfig {
    original: TableCommitmentConfig*,
    interaction: TableCommitmentConfig*,
}
