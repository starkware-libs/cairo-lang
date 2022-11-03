from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_blake2s.blake2s import finalize_blake2s
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.hash import HashBuiltin
from starkware.cairo.common.uint256 import Uint256
from starkware.cairo.stark_verifier.core.air_interface import (
    AirInstance,
    OodsEvaluationInfo,
    PublicInput,
    TracesCommitment,
    TracesConfig,
    TracesDecommitment,
    TracesUnsentCommitment,
    TracesWitness,
    eval_oods_boundary_poly_at_points,
    public_input_hash,
    public_input_validate,
    traces_commit,
    traces_decommit,
    traces_eval_composition_polynomial,
)
from starkware.cairo.stark_verifier.core.channel import (
    Channel,
    ChannelSentFelt,
    ChannelUnsentFelt,
    channel_new,
    random_felts_to_prover,
    read_felts_from_prover,
)
from starkware.cairo.stark_verifier.core.config import (
    StarkConfig,
    StarkDomains,
    stark_config_validate,
    stark_domains_create,
)
from starkware.cairo.stark_verifier.core.fri.fri import (
    FriCommitment,
    FriConfig,
    FriDecommitment,
    FriUnsentCommitment,
    FriWitness,
    fri_commit,
    fri_decommit,
)
from starkware.cairo.stark_verifier.core.proof_of_work import (
    ProofOfWorkUnsentCommitment,
    proof_of_work_commit,
)
from starkware.cairo.stark_verifier.core.queries import generate_queries, queries_to_points
from starkware.cairo.stark_verifier.core.table_commitment import (
    TableCommitment,
    TableCommitmentWitness,
    TableDecommitment,
    TableUnsentCommitment,
    table_commit,
    table_decommit,
)

// Protocol components:
// ======================
// The verifier is built from protocol components. Each component is responsible for commitment
// and decommitment phase. The decommitment part can be regarded as proving a statement with certain
// parameters that are known only after the commitment phase. The XDecommitment struct holds these
// parameters.
// The XWitness struct is the witness required to prove this statement.
//
// For example, VectorDecommitment holds some indices to the committed vector and the corresponding
// values.
// The VectorWitness struct has the authentication paths of the merkle tree, required to prove the
// validity of the values.
//
// The Stark protocol itself is a component, with the statement having no parameters known only
// after the commitment phase, and thus, there is no StarkDecommitment.
//
// The interface of a component named X is:
//
// Structs:
// * XConfig: Configuration for the component.
// * XUnsentCommitment: Commitment values (e.g. hashes), before sending in the channel.
//     Those values shouldn't be used directly (only by the channel).
//     Used by x_commit() to generate a commitment XCommitment.
// * XCommitment: Represents the commitment after it is read from the channel.
// * XDecommitment: Responses for queries.
// * XWitness: Auxiliary information for proving the decommitment.
//
// Functions:
// * x_commit() - The commitment phase. Takes XUnsentCommitment and returns XCommitment.
// * x_decommit() - The decommitment phase. Verifies a decommitment. Uses the commitment and the
//     witness.

// n_oods_values := air.mask_size + air.constraint_degree.
struct StarkUnsentCommitment {
    traces: TracesUnsentCommitment*,
    composition: TableUnsentCommitment,
    // n_oods_values elements. The i-th value is the evaluation of the i-th mask item polynomial at
    // the OODS point, where the mask item polynomial is the interpolation polynomial of the
    // corresponding column shifted by the corresponding row_offset.
    oods_values: ChannelUnsentFelt*,
    fri: FriUnsentCommitment*,
    proof_of_work: ProofOfWorkUnsentCommitment*,
}

struct StarkCommitment {
    traces: TracesCommitment*,
    composition: TableCommitment*,
    interaction_after_composition: InteractionValuesAfterComposition*,
    // n_oods_values elements. See StarkUnsentCommitment.
    oods_values: ChannelSentFelt*,
    interaction_after_oods: InteractionValuesAfterOods*,
    fri: FriCommitment*,
}

struct StarkWitness {
    traces_decommitment: TracesDecommitment*,
    traces_witness: TracesWitness*,
    composition_decommitment: TableDecommitment*,
    composition_witness: TableCommitmentWitness*,
    fri_witness: FriWitness*,
}

struct StarkProof {
    config: StarkConfig*,
    public_input: PublicInput*,
    unsent_commitment: StarkUnsentCommitment*,
    witness: StarkWitness*,
}

// Interaction elements after each STARK phase.
struct InteractionValuesAfterTraces {
    // n_constraints Coefficients for the AIR constraints.
    coefficients: felt*,
}

struct InteractionValuesAfterComposition {
    // Out of domain sampling point.
    oods_point: felt,
}

struct InteractionValuesAfterOods {
    // n_oods_values coefficients for the boundary polynomial validating the OODS values.
    coefficients: felt*,
}

// Verifies a STARK proof.
func verify_stark_proof{range_check_ptr, pedersen_ptr: HashBuiltin*, bitwise_ptr: BitwiseBuiltin*}(
    air: AirInstance*, proof: StarkProof*, security_bits: felt
) -> () {
    alloc_locals;

    // Validate config.
    let config = proof.config;
    stark_config_validate(air=air, config=config, security_bits=security_bits);
    let (stark_domains) = stark_domains_create(config=config);

    // Validate the public input.
    public_input_validate(air=air, public_input=proof.public_input, stark_domains=stark_domains);

    // Initialize blake2s.
    let (blake2s_ptr: felt*) = alloc();
    local blake2s_ptr_start: felt* = blake2s_ptr;

    // Compute the initial hash seed for the Fiat-Shamir channel.
    let (digest) = public_input_hash{blake2s_ptr=blake2s_ptr}(
        air=air, public_input=proof.public_input
    );

    // Construct the channel.
    let (channel: Channel) = channel_new(digest=digest);

    with blake2s_ptr, channel {
        let (stark_commitment) = stark_commit(
            air=air,
            public_input=proof.public_input,
            unsent_commitment=proof.unsent_commitment,
            config=config,
            stark_domains=stark_domains,
        );
        // Generate queries.
        let (n_queries, queries) = generate_queries(
            n_samples=config.n_queries, stark_domains=stark_domains
        );

        stark_decommit(
            air=air,
            n_queries=n_queries,
            queries=queries,
            commitment=stark_commitment,
            witness=proof.witness,
            config=config,
            stark_domains=stark_domains,
        );
    }

    finalize_blake2s(blake2s_ptr_start, blake2s_ptr);

    return ();
}

// STARK commitment phase.
func stark_commit{
    range_check_ptr, blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*, channel: Channel
}(
    air: AirInstance*,
    public_input: PublicInput*,
    unsent_commitment: StarkUnsentCommitment*,
    config: StarkConfig*,
    stark_domains: StarkDomains*,
) -> (res: StarkCommitment*) {
    alloc_locals;

    // Read the commitment of the 'traces' component.
    let (traces_commitment) = traces_commit(
        air=air,
        public_input=public_input,
        unsent_commitment=unsent_commitment.traces,
        config=config.traces,
    );

    // Generate interaction values after traces commitment.
    let (traces_coefficients: felt*) = alloc();
    random_felts_to_prover(n_elements=air.n_constraints, elements=traces_coefficients);
    let (interaction_after_traces: InteractionValuesAfterTraces*) = alloc();
    assert [interaction_after_traces] = InteractionValuesAfterTraces(
        coefficients=traces_coefficients);

    // Read composition commitment.
    let (composition_commitment: TableCommitment*) = table_commit(
        unsent_commitment=unsent_commitment.composition, config=config.composition
    );

    // Generate interaction values after composition.
    let (interaction_after_composition: InteractionValuesAfterComposition*) = alloc();
    random_felts_to_prover(
        n_elements=InteractionValuesAfterComposition.SIZE,
        elements=cast(interaction_after_composition, felt*),
    );

    // Read OODS values.
    local n_oods_values = air.mask_size + air.constraint_degree;
    let (sent_oods_values) = read_felts_from_prover(
        n_values=n_oods_values, values=unsent_commitment.oods_values
    );

    // Check that the trace and the composition agree at oods_point.
    verify_oods(
        air=air,
        oods_values=sent_oods_values,
        traces_commitment=traces_commitment,
        traces_coefficients=traces_coefficients,
        oods_point=interaction_after_composition.oods_point,
        trace_domain_size=stark_domains.trace_domain_size,
        trace_generator=stark_domains.trace_generator,
    );

    // Generate interaction values after OODS.
    let (oods_coefficients: felt*) = alloc();
    random_felts_to_prover(n_elements=n_oods_values, elements=oods_coefficients);
    tempvar interaction_after_oods = new InteractionValuesAfterOods(
        coefficients=oods_coefficients);

    // Read fri commitment.
    let (fri_commitment) = fri_commit(unsent_commitment=unsent_commitment.fri, config=config.fri);

    // Proof of work commitment phase.
    proof_of_work_commit(
        unsent_commitment=unsent_commitment.proof_of_work, config=config.proof_of_work
    );

    // Return commitment.
    return (
        res=new StarkCommitment(
        traces=traces_commitment,
        composition=composition_commitment,
        interaction_after_composition=interaction_after_composition,
        oods_values=sent_oods_values,
        interaction_after_oods=interaction_after_oods,
        fri=fri_commitment),
    );
}

// Checks that the trace and the compostion agree at oods_point, assuming the prover provided us
// with the proper evaluations.
func verify_oods{range_check_ptr}(
    air: AirInstance*,
    oods_values: ChannelSentFelt*,
    traces_commitment: TracesCommitment*,
    traces_coefficients: felt*,
    oods_point: felt,
    trace_domain_size: felt,
    trace_generator: felt,
) {
    let (composition_from_trace_values) = traces_eval_composition_polynomial(
        air=air,
        commitment=traces_commitment,
        mask_values=cast(oods_values, felt*),
        constraint_coefficients=traces_coefficients,
        point=oods_point,
        trace_domain_size=trace_domain_size,
        trace_generator=trace_generator,
    );

    // This verification is currently only implemented for constraint degree 2.
    assert air.constraint_degree = 2;
    tempvar claimed_composition = (
        oods_values[air.mask_size + 0].value + oods_values[air.mask_size + 1].value * oods_point);

    assert composition_from_trace_values = claimed_composition;

    return ();
}

// STARK decommitment phase.
func stark_decommit{range_check_ptr, blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*}(
    air: AirInstance*,
    n_queries: felt,
    queries: felt*,
    commitment: StarkCommitment*,
    witness: StarkWitness*,
    config: StarkConfig*,
    stark_domains: StarkDomains*,
) {
    alloc_locals;

    // First layer decommit.
    traces_decommit(
        air=air,
        n_queries=n_queries,
        queries=queries,
        commitment=commitment.traces,
        decommitment=witness.traces_decommitment,
        witness=witness.traces_witness,
    );
    table_decommit(
        commitment=commitment.composition,
        n_queries=n_queries,
        queries=queries,
        decommitment=witness.composition_decommitment,
        witness=witness.composition_witness,
    );

    // Compute query points.
    let (points) = queries_to_points(
        n_queries=n_queries, queries=queries, stark_domains=stark_domains
    );

    // Evaluate the FRI input layer at query points.
    tempvar eval_info = new OodsEvaluationInfo(
        oods_values=commitment.oods_values,
        oods_point=commitment.interaction_after_composition.oods_point,
        trace_generator=stark_domains.trace_generator,
        constraint_coefficients=commitment.interaction_after_oods.coefficients,
        );
    let (oods_poly_evals) = eval_oods_boundary_poly_at_points(
        air=air,
        eval_info=eval_info,
        n_points=n_queries,
        points=points,
        decommitment=witness.traces_decommitment,
        composition_decommitment=witness.composition_decommitment,
    );

    // Decommit FRI.
    tempvar fri_decommitment = new FriDecommitment(
        n_values=n_queries,
        values=oods_poly_evals,
        points=points);
    fri_decommit(
        n_queries=n_queries,
        queries=queries,
        commitment=commitment.fri,
        decommitment=fri_decommitment,
        witness=witness.fri_witness,
    );

    return ();
}
