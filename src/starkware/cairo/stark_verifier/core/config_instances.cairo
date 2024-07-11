from starkware.cairo.stark_verifier.air.config_instances import TracesConfig
from starkware.cairo.stark_verifier.core.fri.config import FriConfig
from starkware.cairo.stark_verifier.core.proof_of_work import ProofOfWorkConfig
from starkware.cairo.stark_verifier.core.table_commitment import TableCommitmentConfig

const MAX_LOG_TRACE = 64;
const MAX_LOG_BLOWUP_FACTOR = 16;
const MAX_N_QUERIES = 48;

struct StarkConfig {
    traces: TracesConfig*,
    composition: TableCommitmentConfig*,
    fri: FriConfig*,
    proof_of_work: ProofOfWorkConfig*,

    // Log2 of the trace domain size.
    log_trace_domain_size: felt,
    // Number of queries to the last component, FRI.
    n_queries: felt,
    // Log2 of the number of cosets composing the evaluation domain, where the coset size is the
    // trace length.
    log_n_cosets: felt,
    // Number of layers that use a verifier friendly hash in each commitment.
    n_verifier_friendly_commitment_layers: felt,
}
