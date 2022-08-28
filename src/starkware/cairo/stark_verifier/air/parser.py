import itertools
import re
from typing import List, Sequence

from starkware.cairo.common.structs import CairoStructFactory
from starkware.cairo.lang.compiler.identifier_definition import ConstDefinition
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.instances import recursive_instance as INSTANCE
from starkware.cairo.lang.vm.air_public_input import PublicInput, extract_z_and_alpha
from starkware.cairo.stark_verifier.air.utils import public_input_to_cairo
from starkware.python.math_utils import safe_log2
from starkware.python.utils import safe_zip

COMPONENT_HEIGHT = 16
SUPPORTED_LAYOUTS = ["bitwise", "dex", "perpetual_with_bitwise", "recursive"]
ADDITIONAL_IMPORTS = [
    "starkware.cairo.stark_verifier.air.config.TracesConfig",
    "starkware.cairo.stark_verifier.air.public_input.PublicInput",
    "starkware.cairo.stark_verifier.air.public_input.SegmentInfo",
    "starkware.cairo.stark_verifier.air.public_memory.ContinuousPageHeader",
    "starkware.cairo.stark_verifier.air.traces.TracesDecommitment",
    "starkware.cairo.stark_verifier.air.traces.TracesUnsentCommitment",
    "starkware.cairo.stark_verifier.air.traces.TracesWitness",
    "starkware.cairo.stark_verifier.core.config.StarkConfig",
    "starkware.cairo.stark_verifier.core.fri.config.FriConfig",
    "starkware.cairo.stark_verifier.core.fri.fri.FriLayerWitness",
    "starkware.cairo.stark_verifier.core.fri.fri.FriUnsentCommitment",
    "starkware.cairo.stark_verifier.core.fri.fri.FriWitness",
    "starkware.cairo.stark_verifier.core.proof_of_work.ProofOfWorkConfig",
    "starkware.cairo.stark_verifier.core.proof_of_work.ProofOfWorkUnsentCommitment",
    "starkware.cairo.stark_verifier.core.stark.StarkProof",
    "starkware.cairo.stark_verifier.core.stark.StarkUnsentCommitment",
    "starkware.cairo.stark_verifier.core.stark.StarkWitness",
    "starkware.cairo.stark_verifier.core.table_commitment.TableCommitmentConfig",
    "starkware.cairo.stark_verifier.core.table_commitment.TableCommitmentWitness",
    "starkware.cairo.stark_verifier.core.table_commitment.TableDecommitment",
    "starkware.cairo.stark_verifier.core.vector_commitment.VectorCommitmentConfig",
    "starkware.cairo.stark_verifier.core.vector_commitment.VectorCommitmentWitness",
]


def extract_annotations(annotations: Sequence[str], prefix: str, kind: str) -> List[int]:
    """
    Extracts annotations from a proof JSON with a specific prefix, of a specific kind.
    Examples for prefix: "STARK/Original/Commit on Trace".
    Examples for kind: "Data", "Hash", "FieldElement", "Field Elements".
    """
    res: List[int] = []
    pattern = f"P->V\\[(\\d+):(\\d+)\\]: /cpu air/{prefix}: .*{kind}\\((.+)\\)"
    for line in annotations:
        match = re.match(pattern=pattern, string=line)
        if match is None:
            continue
        _from_pos, _to_pos, str_value = match.groups()
        if kind == "Field Elements":
            res += [int(x, 16) for x in str_value.split(",")]
            continue
        value = int(str_value, 16)
        if kind == "Hash":
            # Make sure hash is truncated.
            assert value % 2**96 == 0
        res.append(value)
    return res


def to_uint256(x):
    return (x % (2**128), x >> 128)


def parse_proof(identifiers: IdentifierManager, proof_json: dict):
    """
    Generates a Cairo StarkProof struct from a proof JSON.
    """

    structs = CairoStructFactory(
        identifiers=identifiers, additional_imports=ADDITIONAL_IMPORTS
    ).structs

    def annotations(prefix: str, kind: str):
        return extract_annotations(proof_json["annotations"], prefix, kind)

    # Parse JSON.
    public_input: PublicInput = PublicInput.Schema().load(proof_json["public_input"])
    z, alpha = extract_z_and_alpha(proof_json["annotations"])
    cairo_public_input = public_input_to_cairo(structs, public_input=public_input, z=z, alpha=alpha)

    # Extract elements from annotations.
    (original_commitment_hash,) = annotations("STARK/Original/Commit on Trace", "Hash")
    (interaction_commitment_hash,) = annotations("STARK/Interaction/Commit on Trace", "Hash")
    (composition_commitment_hash,) = annotations(
        "STARK/Out Of Domain Sampling/Commit on Trace", "Hash"
    )
    oods_values = annotations("STARK/Out Of Domain Sampling/OODS values", "Field Element")
    fri_layers_commitments = [
        x >> 96 for x in annotations("STARK/FRI/Commitment/Layer [0-9]+", "Hash")
    ]
    fri_last_layer_coefficients = annotations("STARK/FRI/Commitment/Last Layer", "Field Elements")
    (proof_of_work_nonce,) = annotations("STARK/FRI/Proof of Work", "Data")

    def get_authentications(prefix: str):
        # Collect authentication (siblings) values.
        # In the case of 1 column, the first authentication values come as Data.
        return annotations(prefix, "Data") + annotations(prefix, "Hash")

    original_witness_leaves = annotations(
        "STARK/FRI/Decommitment/Layer 0/Virtual Oracle/Trace 0", "Field Element"
    )
    original_witness_authentications = get_authentications(
        "STARK/FRI/Decommitment/Layer 0/Virtual Oracle/Trace 0"
    )
    interaction_witness_leaves = annotations(
        "STARK/FRI/Decommitment/Layer 0/Virtual Oracle/Trace 1", "Field Element"
    )
    interaction_witness_authentications = get_authentications(
        "STARK/FRI/Decommitment/Layer 0/Virtual Oracle/Trace 1"
    )
    composition_witness_leaves = annotations(
        "STARK/FRI/Decommitment/Layer 0/Virtual Oracle/Trace 2", "Field Element"
    )
    composition_witness_authentications = get_authentications(
        "STARK/FRI/Decommitment/Layer 0/Virtual Oracle/Trace 2"
    )

    fri_step_list = proof_json["proof_parameters"]["stark"]["fri"]["fri_step_list"]
    n_fri_layers = len(fri_step_list)
    fri_witnesses = []
    for i in range(1, n_fri_layers):
        leaves = annotations(f"STARK/FRI/Decommitment/Layer {i}", "Field Element")
        authentications = annotations(f"STARK/FRI/Decommitment/Layer {i}", "Hash")
        fri_witnesses.append(
            structs.FriLayerWitness(
                n_leaves=len(leaves),
                leaves=leaves,
                table_witness=structs.TableCommitmentWitness(
                    vector=structs.VectorCommitmentWitness(
                        n_authentications=len(authentications),
                        authentications=list(itertools.chain(*map(to_uint256, authentications))),
                    ),
                ),
            )
        )

    # Extract details for config.
    effective_component_height = COMPONENT_HEIGHT * INSTANCE.cpu_component_step
    log_trace_domain_size = safe_log2(effective_component_height * public_input.n_steps)
    log_n_cosets = proof_json["proof_parameters"]["stark"]["log_n_cosets"]
    log_last_layer_degree_bound = safe_log2(
        proof_json["proof_parameters"]["stark"]["fri"]["last_layer_degree_bound"]
    )

    # FRI layers.
    assert len(fri_layers_commitments) == n_fri_layers - 1  # Inner layers.

    log_eval_domain_size = log_trace_domain_size + log_n_cosets
    layer_log_sizes = [log_eval_domain_size]
    for layer_step in fri_step_list:
        layer_log_sizes.append(layer_log_sizes[-1] - layer_step)
    assert len(layer_log_sizes) == n_fri_layers + 1  # Inner layers, input and last layer.
    assert layer_log_sizes[-1] == log_last_layer_degree_bound + log_n_cosets
    assert len(fri_last_layer_coefficients) == 2**log_last_layer_degree_bound

    def get_const_value(name: str):
        res = identifiers.root.get(ScopedName.from_string(name)).identifier_definition
        assert isinstance(res, ConstDefinition)
        return res.value

    layout_name = public_input.layout
    module_name = f"starkware.cairo.stark_verifier.air.layouts.{layout_name}.autogenerated"
    N_ORIGINAL_COLUMNS = get_const_value(f"{module_name}.N_ORIGINAL_COLUMNS")
    N_INTERACTION_COLUMNS = get_const_value(f"{module_name}.N_INTERACTION_COLUMNS")
    CONSTRAINT_DEGREE = get_const_value(f"{module_name}.CONSTRAINT_DEGREE")
    # Build the Cairo structs.
    stark_config = structs.StarkConfig(
        traces=structs.TracesConfig(
            original=structs.TableCommitmentConfig(
                n_columns=N_ORIGINAL_COLUMNS,
                vector=structs.VectorCommitmentConfig(
                    height=log_eval_domain_size,
                ),
            ),
            interaction=structs.TableCommitmentConfig(
                n_columns=N_INTERACTION_COLUMNS,
                vector=structs.VectorCommitmentConfig(
                    height=log_eval_domain_size,
                ),
            ),
        ),
        composition=structs.TableCommitmentConfig(
            n_columns=CONSTRAINT_DEGREE,
            vector=structs.VectorCommitmentConfig(
                height=log_eval_domain_size,
            ),
        ),
        fri=structs.FriConfig(
            log_input_size=layer_log_sizes[0],
            n_layers=n_fri_layers,
            inner_layers=list(
                itertools.chain(
                    *(
                        structs.TableCommitmentConfig(
                            n_columns=2**layer_steps,
                            vector=structs.VectorCommitmentConfig(
                                height=layer_log_rows,
                            ),
                        )
                        for layer_steps, layer_log_rows in safe_zip(
                            fri_step_list[1:], layer_log_sizes[2:]
                        )
                    )
                )
            ),
            fri_step_sizes=fri_step_list,
            log_last_layer_degree_bound=log_last_layer_degree_bound,
        ),
        proof_of_work=structs.ProofOfWorkConfig(
            n_bits=proof_json["proof_parameters"]["stark"]["fri"]["proof_of_work_bits"],
        ),
        log_trace_domain_size=log_trace_domain_size,
        n_queries=proof_json["proof_parameters"]["stark"]["fri"]["n_queries"],
        log_n_cosets=log_n_cosets,
    )
    stark_unsent_commitment = structs.StarkUnsentCommitment(
        traces=structs.TracesUnsentCommitment(
            original=original_commitment_hash >> 96,
            interaction=interaction_commitment_hash >> 96,
        ),
        composition=composition_commitment_hash >> 96,
        oods_values=oods_values,
        fri=structs.FriUnsentCommitment(
            inner_layers=fri_layers_commitments, last_layer_coefficients=fri_last_layer_coefficients
        ),
        proof_of_work=structs.ProofOfWorkUnsentCommitment(
            nonce=proof_of_work_nonce,
        ),
    )
    stark_witness = structs.StarkWitness(
        traces_decommitment=structs.TracesDecommitment(
            original=structs.TableDecommitment(
                n_values=len(original_witness_leaves),
                values=original_witness_leaves,
            ),
            interaction=structs.TableDecommitment(
                n_values=len(interaction_witness_leaves),
                values=interaction_witness_leaves,
            ),
        ),
        traces_witness=structs.TracesWitness(
            original=structs.TableCommitmentWitness(
                vector=structs.VectorCommitmentWitness(
                    n_authentications=len(original_witness_authentications),
                    authentications=list(
                        itertools.chain(*map(to_uint256, original_witness_authentications))
                    ),
                ),
            ),
            interaction=structs.TableCommitmentWitness(
                vector=structs.VectorCommitmentWitness(
                    n_authentications=len(interaction_witness_authentications),
                    authentications=list(
                        itertools.chain(*map(to_uint256, interaction_witness_authentications))
                    ),
                ),
            ),
        ),
        composition_decommitment=structs.TableDecommitment(
            n_values=len(composition_witness_leaves),
            values=composition_witness_leaves,
        ),
        composition_witness=structs.TableCommitmentWitness(
            vector=structs.VectorCommitmentWitness(
                n_authentications=len(composition_witness_authentications),
                authentications=list(
                    itertools.chain(*map(to_uint256, composition_witness_authentications))
                ),
            ),
        ),
        fri_witness=structs.FriWitness(
            layers=list(itertools.chain(*fri_witnesses)),
        ),
    )
    proof = structs.StarkProof(
        config=stark_config,
        public_input=cairo_public_input,
        unsent_commitment=stark_unsent_commitment,
        witness=stark_witness,
    )

    return proof
