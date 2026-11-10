// Unpacker for the recursive circuit-proof tree's packed output.
//
// The recursive tree prover folds leaf circuit proofs with the circuit multiverifier and emits a
// nested `PackedNode` tree, one `Composite` per verifier node:
//   Composite { circuit_hash: C, subtasks }   // a fold node (two children, or one for the
//                                             // single-leaf tree's root self-fold), or the leaf
//                                             // circuit node
//     -> Plain { output_preimage }            // a leaf's raw revealed output
// where C is the node's circuit hash — blake2s(log_blowup_factor || component_log_sizes ||
// preprocessed_root), the identity of the verifier circuit that proved the node. The tree carries
// only the underivable data; every node's output hash is recomputed here:
//   O_leaf = H1 = blake2s(encoded preimage felts),  emitted verbatim by the leaf circuit,
//   O_parent = blake2s(C_left ++ O_left ++ C_right ++ O_right),
// where C_child is the child proof's circuit hash (the multiverifier's for internal children, the
// leaf circuit's for leaf children) and all digests are eight little-endian u32 words. The Cairo
// circuit verifier (the applicative root task) outputs blake2s(C_root ++ O_root).
//
// This module walks the tree (revealed through hints), recomputes every hash bottom-up — each
// node's circuit hash is guessed by a hint and verified to be in the trusted list matching its
// role (multiverifier hashes for fold nodes, leaf verifier hashes for leaves) — checks the top
// against the verifier task's output digest, and verifies the raw leaf task outputs in place
// against the tasks output at `tasks_output`, in the bootloader tasks-output format:
//   [n_tasks, then per task: (task_output_size, program_hash, output...)].

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_blake2s.blake2s import blake_with_opcode, encode_felt252s_to_u32s
from starkware.cairo.common.math import assert_nn_le

const BLAKE2S_DIGEST_N_WORDS = 8;

// An eight-word (little-endian u32) blake2s digest.
struct BlakeHash {
    words: (felt, felt, felt, felt, felt, felt, felt, felt),
}

// The contribution to the preimage from a single child of the multiverifier: its circuit hash
// (verified to be supported) followed by its output hash.
struct Contribution {
    circuit_hash: BlakeHash,
    output_hash: BlakeHash,
}

// The unpacker's trust anchors: the circuit hashes the tree's proofs are known to carry, split
// by role — multiverifier circuits prove internal fold nodes, leaf verifier circuits prove
// leaves.
struct CircuitUnpackerConfig {
    n_multiverifier_hashes: felt,
    multiverifier_hashes: BlakeHash*,
    n_leaf_verifier_hashes: felt,
    leaf_verifier_hashes: BlakeHash*,
}

// Returns a pointer to the trusted multiverifier circuit hash the current (fold) node's proof
// carries. The index is provided by a hint (which searches the list in Cairo memory by full
// eight-word comparison) and verified to be within the list, so any returned hash is supported.
func get_multiverifier_hash{range_check_ptr}(config: CircuitUnpackerConfig*) -> (
    circuit_hash: BlakeHash*
) {
    alloc_locals;
    local circuit_hash_index;
    // Sets `circuit_hash_index` to the index (in the config's multiverifier list) of the circuit
    // hash the current node's proof carries.
    %{ CIRCUIT_UNPACK_SET_MULTIVERIFIER_HASH_INDEX %}
    assert_nn_le(circuit_hash_index, config.n_multiverifier_hashes - 1);
    return (circuit_hash=&config.multiverifier_hashes[circuit_hash_index]);
}

// Same as get_multiverifier_hash, for the current (leaf) node in the leaf verifier list.
func get_leaf_verifier_hash{range_check_ptr}(config: CircuitUnpackerConfig*) -> (
    circuit_hash: BlakeHash*
) {
    alloc_locals;
    local circuit_hash_index;
    %{ CIRCUIT_UNPACK_SET_LEAF_VERIFIER_HASH_INDEX %}
    assert_nn_le(circuit_hash_index, config.n_leaf_verifier_hashes - 1);
    return (circuit_hash=&config.leaf_verifier_hashes[circuit_hash_index]);
}

// Reads a single leaf task from `tasks_output` and returns its hash — blake2s over the encoded
// [program_hash, output...] preimage — with the leaf verifier circuit hash its proof carries.
// Advances `tasks_output` and decrements `n_remaining_tasks`.
func process_leaf{range_check_ptr, tasks_output: felt*, n_remaining_tasks: felt}(
    config: CircuitUnpackerConfig*
) -> (output_hash: BlakeHash*, circuit_hash: BlakeHash*) {
    alloc_locals;
    // The next entry: [task_output_size, program_hash, output...].
    local preimage_len = tasks_output[0] - 1;
    let preimage = &tasks_output[1];

    let (local encoded_preimage: felt*) = alloc();
    let encoded_preimage_len = encode_felt252s_to_u32s(
        packed_values_len=preimage_len, packed_values=preimage, unpacked_u32s=encoded_preimage
    );
    let (output_hash: BlakeHash*) = alloc();
    blake_with_opcode(len=encoded_preimage_len, data=encoded_preimage, out=output_hash);

    let tasks_output = &tasks_output[preimage_len + 1];
    let n_remaining_tasks = n_remaining_tasks - 1;

    let (circuit_hash) = get_leaf_verifier_hash(config=config);
    return (output_hash=output_hash, circuit_hash=circuit_hash);
}

// Leaf and fold nodes draw their circuit hash from disjoint lists, binding each node's claimed
// type to the kind of circuit its proof carried (the parent digests, up to the verifier task's
// output digest, pin each guessed hash to the proof's actual one).

// Recursively computes a tree node's output hash bottom-up. Each leaf consumes the next task at
// `tasks_output`, advancing it and decrementing `n_remaining_tasks`.
// Returns the node's output hash and its circuit hash (verified to be supported).
func process_node{range_check_ptr, tasks_output: felt*, n_remaining_tasks: felt}(
    config: CircuitUnpackerConfig*
) -> (output_hash: BlakeHash*, circuit_hash: BlakeHash*) {
    alloc_locals;
    local is_leaf;
    %{ CIRCUIT_UNPACK_SET_IS_LEAF %}
    if (is_leaf != 0) {
        return process_leaf(config=config);
    }

    // An internal fold node: recompute O = blake2s(contribution(left) ++ contribution(right)).
    %{ CIRCUIT_UNPACK_ENTER_SUBTASK_0 %}
    let (local left_output_hash, local left_circuit_hash) = process_node(config=config);
    %{ CIRCUIT_UNPACK_EXIT_SCOPE %}

    // A self-fold node (the single-leaf tree's root pass) carries one child whose proof the
    // multiverifier verified in both slots: its contribution is duplicated, and its leaf tasks
    // are consumed once. A wrong `is_self_fold` guess is caught by the digest checks (the
    // recomputed fold digest would not match).
    local is_self_fold;
    %{ CIRCUIT_UNPACK_SET_IS_SELF_FOLD %}
    local right_output_hash: BlakeHash*;
    local right_circuit_hash: BlakeHash*;
    if (is_self_fold != 0) {
        assert right_output_hash = left_output_hash;
        assert right_circuit_hash = left_circuit_hash;
        tempvar range_check_ptr = range_check_ptr;
        tempvar tasks_output = tasks_output;
        tempvar n_remaining_tasks = n_remaining_tasks;
    } else {
        %{ CIRCUIT_UNPACK_ENTER_SUBTASK_1 %}
        let (output_hash, circuit_hash) = process_node(config=config);
        %{ CIRCUIT_UNPACK_EXIT_SCOPE %}
        assert right_output_hash = output_hash;
        assert right_circuit_hash = circuit_hash;
        tempvar range_check_ptr = range_check_ptr;
        tempvar tasks_output = tasks_output;
        tempvar n_remaining_tasks = n_remaining_tasks;
    }
    local range_check_ptr = range_check_ptr;
    local tasks_output: felt* = tasks_output;
    local n_remaining_tasks = n_remaining_tasks;

    let (preimage: Contribution*) = alloc();
    assert preimage[0].circuit_hash = [left_circuit_hash];
    assert preimage[0].output_hash = [left_output_hash];
    assert preimage[1].circuit_hash = [right_circuit_hash];
    assert preimage[1].output_hash = [right_output_hash];
    let (output_hash: BlakeHash*) = alloc();
    blake_with_opcode(len=2 * Contribution.SIZE, data=preimage, out=output_hash);
    let (circuit_hash) = get_multiverifier_hash(config=config);
    return (output_hash=output_hash, circuit_hash=circuit_hash);
}

// Unpacks the whole tree.
//
// Verifies that `verifier_output` is the root of a recursion tree whose leaves output the
// [n_tasks, tasks...] at `tasks_output`, advancing `tasks_output` past the verified output.
// Validates the circuit hashes of all the circuits in the recursion tree.
func unpack_circuit_tree{range_check_ptr, tasks_output: felt*}(
    config: CircuitUnpackerConfig*, verifier_output: felt*
) {
    alloc_locals;
    let n_remaining_tasks = tasks_output[0];
    let tasks_output = &tasks_output[1];
    with tasks_output, n_remaining_tasks {
        let (root_output_hash, root_circuit_hash) = process_node(config=config);
    }
    // Every task was consumed by exactly one leaf.
    assert n_remaining_tasks = 0;
    local tasks_output: felt* = tasks_output;

    // The verified digest must open to the recomputed root contribution.
    let (preimage: Contribution*) = alloc();
    assert preimage[0].circuit_hash = [root_circuit_hash];
    assert preimage[0].output_hash = [root_output_hash];
    // Verify that verifier_output == hash(preimage).
    blake_with_opcode(len=Contribution.SIZE, data=preimage, out=verifier_output);
    return ();
}
