from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import PoseidonBuiltin
from starkware.cairo.common.hash_state_poseidon import (
    HashState,
    hash_finalize,
    hash_init,
    hash_update_single,
    hash_update_with_nested_hash,
    poseidon_hash_many,
)
from starkware.cairo.common.math import assert_lt_felt
from starkware.cairo.common.poseidon_state import PoseidonBuiltinState
from starkware.cairo.common.registers import get_fp_and_pc
from starkware.starknet.core.os.constants import (
    ADD_MOD_GAS_COST,
    BITWISE_BUILTIN_GAS_COST,
    ECOP_GAS_COST,
    MUL_MOD_GAS_COST,
    PEDERSEN_GAS_COST,
    POSEIDON_GAS_COST,
)

const COMPILED_CLASS_VERSION = 'COMPILED_CLASS_V1';

struct CompiledClassEntryPoint {
    // A field element that encodes the signature of the called function.
    selector: felt,
    // The offset of the instruction that should be called within the contract bytecode.
    offset: felt,
    // The number of builtins in 'builtin_list'.
    n_builtins: felt,
    // 'builtin_list' is a continuous memory segment containing the ASCII encoding of the (ordered)
    // builtins used by the function.
    builtin_list: felt*,
}

struct CompiledClass {
    compiled_class_version: felt,

    // The length and pointer to the external entry point table of the contract.
    n_external_functions: felt,
    external_functions: CompiledClassEntryPoint*,

    // The length and pointer to the L1 handler entry point table of the contract.
    n_l1_handlers: felt,
    l1_handlers: CompiledClassEntryPoint*,

    // The length and pointer to the constructor entry point table of the contract.
    n_constructors: felt,
    constructors: CompiledClassEntryPoint*,

    // The length and pointer of the bytecode.
    bytecode_length: felt,
    bytecode_ptr: felt*,
}

// Checks that the list of selectors is sorted.
func validate_entry_points{range_check_ptr}(
    n_entry_points: felt, entry_points: CompiledClassEntryPoint*
) {
    if (n_entry_points == 0) {
        return ();
    }

    return validate_entry_points_inner(
        n_entry_points=n_entry_points - 1,
        entry_points=&entry_points[1],
        prev_selector=entry_points[0].selector,
    );
}

// Inner function for validate_entry_points.
func validate_entry_points_inner{range_check_ptr}(
    n_entry_points: felt, entry_points: CompiledClassEntryPoint*, prev_selector
) {
    if (n_entry_points == 0) {
        return ();
    }

    assert_lt_felt(prev_selector, entry_points[0].selector);

    return validate_entry_points_inner(
        n_entry_points=n_entry_points - 1,
        entry_points=&entry_points[1],
        prev_selector=entry_points[0].selector,
    );
}

func compiled_class_hash{range_check_ptr, poseidon_ptr: PoseidonBuiltin*}(
    compiled_class: CompiledClass*
) -> (hash: felt) {
    alloc_locals;
    assert compiled_class.compiled_class_version = COMPILED_CLASS_VERSION;

    let hash_state: HashState = hash_init();
    with hash_state {
        hash_update_single(item=compiled_class.compiled_class_version);

        // Hash external entry points.
        hash_entry_points(
            entry_points=compiled_class.external_functions,
            n_entry_points=compiled_class.n_external_functions,
        );

        // Hash L1 handler entry points.
        hash_entry_points(
            entry_points=compiled_class.l1_handlers, n_entry_points=compiled_class.n_l1_handlers
        );

        // Hash constructor entry points.
        hash_entry_points(
            entry_points=compiled_class.constructors, n_entry_points=compiled_class.n_constructors
        );

        // Hash bytecode.
        let bytecode_hash = bytecode_hash_node(
            data_ptr=compiled_class.bytecode_ptr, data_length=compiled_class.bytecode_length
        );
        hash_update_single(item=bytecode_hash);
    }

    let hash: felt = hash_finalize(hash_state=hash_state);
    return (hash=hash);
}

// Returns the hash of the contract class bytecode according to its segments.
//
// The hash is computed according to a segment tree. Each segment may be either a leaf or divided
// into smaller segments (internal node).
// For example, the bytecode may be divided into functions and each function can be divided
// according to its branches.
//
// The hash of a leaf is the Poseidon hash the data.
// The hash of an internal node is `1 + poseidon(len0, hash0, len1, hash1, ...)` where
// len0 is the total length of the first segment, hash0 is the hash of the first segment, and so on.
//
// For each segment, the *prover* can choose whether to load or skip the segment.
//
// * Loaded segment:
//   For leaves, the data will be fully loaded into memory.
//   For internal nodes, the prover can choose to load/skip each of the children separately.
//
// * Skipped segment:
//   The inner structure of that segment is ignored.
//   The only guarantee is that the first field element is enforced to be -1.
//   The rest of the field elements are unconstrained.
//   The fact that a skipped segment is guaranteed to begin with -1 implies that the execution of
//   the program cannot visit the start of the segment, as -1 is not a valid Cairo opcode.
//
// In the example above of division according to functions and branches, a function may be skipped
// entirely or partially.
// As long as one function does not jump into the middle of another function and as long as there
// are no jumps into the middle of a branch segment, the loading process described above will be
// sound.
func bytecode_hash_node{range_check_ptr, poseidon_ptr: PoseidonBuiltin*}(
    data_ptr: felt*, data_length: felt
) -> felt {
    alloc_locals;

    local is_leaf;

    %{
        from starkware.starknet.core.os.contract_class.compiled_class_hash_objects import (
            BytecodeLeaf,
        )
        ids.is_leaf = 1 if isinstance(bytecode_segment_structure, BytecodeLeaf) else 0
    %}

    // Guess if the bytecode is a leaf or an internal node in the tree.
    if (is_leaf != 0) {
        // If the bytecode is a leaf, it must be loaded into memory. Compute its hash.
        let (hash) = poseidon_hash_many(n=data_length, elements=data_ptr);
        return hash;
    }

    %{ bytecode_segments = iter(bytecode_segment_structure.segments) %}

    // Use the poseidon builtin directly for performance reasons.
    let poseidon_state = PoseidonBuiltinState(s0=0, s1=0, s2=0);
    bytecode_hash_internal_node{poseidon_state=poseidon_state}(
        data_ptr=data_ptr, data_length=data_length
    );

    // Pad input with [1, 0]. See implementation of poseidon_hash_many().
    assert poseidon_ptr.input = PoseidonBuiltinState(
        s0=poseidon_state.s0 + 1, s1=poseidon_state.s1, s2=poseidon_state.s2
    );
    let segmented_hash = poseidon_ptr.output.s0;
    let poseidon_ptr = &poseidon_ptr[1];

    // Add 1 to segmented_hash to avoid collisions with the hash of a leaf (domain separation).
    return segmented_hash + 1;
}

// Helper function for bytecode_hash_node.
// Computes the hash of an internal node by adding its children to the hash state.
func bytecode_hash_internal_node{
    range_check_ptr, poseidon_ptr: PoseidonBuiltin*, poseidon_state: PoseidonBuiltinState
}(data_ptr: felt*, data_length: felt) {
    if (data_length == 0) {
        %{ assert next(bytecode_segments, None) is None %}
        return ();
    }

    alloc_locals;
    local is_used_leaf;
    local is_segment_used;
    local segment_length;

    %{
        current_segment_info = next(bytecode_segments)

        is_used = current_segment_info.is_used
        ids.is_segment_used = 1 if is_used else 0

        is_used_leaf = is_used and isinstance(current_segment_info.inner_structure, BytecodeLeaf)
        ids.is_used_leaf = 1 if is_used_leaf else 0

        ids.segment_length = current_segment_info.segment_length
        vm_enter_scope(new_scope_locals={
            "bytecode_segment_structure": current_segment_info.inner_structure,
        })
    %}

    if (is_used_leaf != 0) {
        // Repeat the code of bytecode_hash_node() for performance reasons, instead of calling it.
        let (current_segment_hash) = poseidon_hash_many(n=segment_length, elements=data_ptr);
        // tempvar current_segment_hash = nondet %{ bytecode_segment_structure.hash() %};
        tempvar range_check_ptr = range_check_ptr;
        tempvar poseidon_ptr = poseidon_ptr;
        tempvar current_segment_hash = current_segment_hash;
    } else {
        if (is_segment_used != 0) {
            let current_segment_hash = bytecode_hash_node(
                data_ptr=data_ptr, data_length=segment_length
            );
        } else {
            // Set the first felt of the bytecode to -1 to make sure that the execution cannot jump
            // to this segment (-1 is an invalid opcode).
            // The hash in this case is guessed and the actual bytecode is unconstrained (except for
            // the first felt).
            %{ del memory.data[ids.data_ptr] %}
            assert data_ptr[0] = -1;

            assert [range_check_ptr] = segment_length;
            tempvar range_check_ptr = range_check_ptr + 1;
            tempvar poseidon_ptr = poseidon_ptr;
            tempvar current_segment_hash = nondet %{ bytecode_segment_structure.hash() %};
        }
    }

    // Add the segment length and hash to the hash state.
    // Use the poseidon builtin directly for performance reasons.
    assert poseidon_ptr.input = PoseidonBuiltinState(
        s0=poseidon_state.s0 + segment_length,
        s1=poseidon_state.s1 + current_segment_hash,
        s2=poseidon_state.s2,
    );
    let poseidon_state = poseidon_ptr.output;
    let poseidon_ptr = &poseidon_ptr[1];

    %{ vm_exit_scope() %}

    return bytecode_hash_internal_node(
        data_ptr=&data_ptr[segment_length], data_length=data_length - segment_length
    );
}

func hash_entry_points{poseidon_ptr: PoseidonBuiltin*, hash_state: HashState}(
    entry_points: CompiledClassEntryPoint*, n_entry_points: felt
) {
    let inner_hash_state = hash_init();
    hash_entry_points_inner{hash_state=inner_hash_state}(
        entry_points=entry_points, n_entry_points=n_entry_points
    );
    let hash: felt = hash_finalize(hash_state=inner_hash_state);
    hash_update_single(item=hash);

    return ();
}

func hash_entry_points_inner{poseidon_ptr: PoseidonBuiltin*, hash_state: HashState}(
    entry_points: CompiledClassEntryPoint*, n_entry_points: felt
) {
    if (n_entry_points == 0) {
        return ();
    }

    hash_update_single(item=entry_points.selector);
    hash_update_single(item=entry_points.offset);

    // Hash builtins.
    hash_update_with_nested_hash(
        data_ptr=entry_points.builtin_list, data_length=entry_points.n_builtins
    );

    return hash_entry_points_inner(
        entry_points=&entry_points[1], n_entry_points=n_entry_points - 1
    );
}

// A list entry that maps a hash to the corresponding contract classes.
struct CompiledClassFact {
    // The hash of the contract. This member should be first, so that we can lookup items
    // with the hash as key, using find_element().
    hash: felt,
    compiled_class: CompiledClass*,
}

// Guesses the contract classes from the 'os_input' hint variable without validating their hashes.
// Returns CompiledClassFact list that maps a hash to a CompiledClass, and the builtin costs list
// which is appended to every contract.
//
// Note: `validate_compiled_class_facts` must be called eventually to complete the validation.
func guess_compiled_class_facts{poseidon_ptr: PoseidonBuiltin*, range_check_ptr}() -> (
    n_compiled_class_facts: felt, compiled_class_facts: CompiledClassFact*, builtin_costs: felt*
) {
    alloc_locals;

    local builtin_costs: felt* = new (
        PEDERSEN_GAS_COST,
        BITWISE_BUILTIN_GAS_COST,
        ECOP_GAS_COST,
        POSEIDON_GAS_COST,
        ADD_MOD_GAS_COST,
        MUL_MOD_GAS_COST,
    );
    local n_compiled_class_facts;
    local compiled_class_facts: CompiledClassFact*;
    %{
        from starkware.starknet.core.os.contract_class.compiled_class_hash import (
            create_bytecode_segment_structure,
            get_compiled_class_struct,
        )

        ids.n_compiled_class_facts = len(os_input.compiled_classes)
        ids.compiled_class_facts = (compiled_class_facts_end := segments.add())
        for i, (compiled_class_hash, compiled_class) in enumerate(
            os_input.compiled_classes.items()
        ):
            # Load the compiled class.
            cairo_contract = get_compiled_class_struct(
                identifiers=ids._context.identifiers,
                compiled_class=compiled_class,
                # Load the entire bytecode - the unaccessed segments will be overridden and skipped
                # after the execution, in `validate_compiled_class_facts_post_execution`.
                bytecode=compiled_class.bytecode,
            )
            segments.load_data(
                ptr=ids.compiled_class_facts[i].address_,
                data=(compiled_class_hash, segments.gen_arg(cairo_contract))
            )

            bytecode_ptr = ids.compiled_class_facts[i].compiled_class.bytecode_ptr
            # Compiled classes are expected to end with a `ret` opcode followed by a pointer to
            # the builtin costs.
            segments.load_data(
                ptr=bytecode_ptr + cairo_contract.bytecode_length,
                data=[0x208b7fff7fff7ffe, ids.builtin_costs]
            )

            # Load hints and debug info.
            vm_load_program(
                compiled_class.get_runnable_program(entrypoint_builtins=[]), bytecode_ptr)
    %}

    return (
        n_compiled_class_facts=n_compiled_class_facts,
        compiled_class_facts=compiled_class_facts,
        builtin_costs=builtin_costs,
    );
}

// Validates the compiled class facts structure and hash after the execution.
// Uses the execution info to optimize hash computation.
func validate_compiled_class_facts_post_execution{poseidon_ptr: PoseidonBuiltin*, range_check_ptr}(
    n_compiled_class_facts, compiled_class_facts: CompiledClassFact*, builtin_costs: felt*
) {
    %{
        from starkware.cairo.lang.vm.relocatable import RelocatableValue

        bytecode_segment_to_length = {}
        compiled_hash_to_bytecode_segment = {}
        for i in range(ids.n_compiled_class_facts):
            fact = ids.compiled_class_facts[i]
            bytecode_segment = fact.compiled_class.bytecode_ptr.segment_index
            bytecode_segment_to_length[bytecode_segment] = fact.compiled_class.bytecode_length
            compiled_hash_to_bytecode_segment[fact.hash] = bytecode_segment

        bytecode_segment_to_visited_pcs = {
            bytecode_segment: [] for bytecode_segment in bytecode_segment_to_length
        }
        for addr in iter_accessed_addresses():
            if (
                isinstance(addr, RelocatableValue)
                and addr.segment_index in bytecode_segment_to_visited_pcs
            ):
                bytecode_segment_to_visited_pcs[addr.segment_index].append(addr.offset)

        # Sort and remove the program extra data, which is not part of the hash.
        for bytecode_segment, visited_pcs in bytecode_segment_to_visited_pcs.items():
            visited_pcs.sort()
            while (
                len(visited_pcs) > 0
                and visited_pcs[-1] >= bytecode_segment_to_length[bytecode_segment]
            ):
                visited_pcs.pop()

        # Build the bytecode segment structures based on the execution info.
        bytecode_segment_structures = {
            compiled_hash: create_bytecode_segment_structure(
                bytecode=compiled_class.bytecode,
                bytecode_segment_lengths=compiled_class.bytecode_segment_lengths,
                visited_pcs=bytecode_segment_to_visited_pcs[
                    compiled_hash_to_bytecode_segment[compiled_hash]
                ],
            ) for compiled_hash, compiled_class in os_input.compiled_classes.items()
        }
    %}
    return validate_compiled_class_facts(
        n_compiled_class_facts=n_compiled_class_facts,
        compiled_class_facts=compiled_class_facts,
        builtin_costs=builtin_costs,
    );
}

// Validates the compiled class facts structure and hash, using the hint variable
// `bytecode_segment_structures` - a mapping from compilied class hash to the structure.
func validate_compiled_class_facts{poseidon_ptr: PoseidonBuiltin*, range_check_ptr}(
    n_compiled_class_facts, compiled_class_facts: CompiledClassFact*, builtin_costs: felt*
) {
    if (n_compiled_class_facts == 0) {
        return ();
    }
    alloc_locals;

    let compiled_class_fact = compiled_class_facts[0];
    let compiled_class = compiled_class_fact.compiled_class;

    validate_entry_points(
        n_entry_points=compiled_class.n_external_functions,
        entry_points=compiled_class.external_functions,
    );

    validate_entry_points(
        n_entry_points=compiled_class.n_l1_handlers, entry_points=compiled_class.l1_handlers
    );
    // Compiled classes are expected to end with a `ret` opcode followed by a pointer to the
    // builtin costs.
    assert compiled_class.bytecode_ptr[compiled_class.bytecode_length] = 0x208b7fff7fff7ffe;
    assert compiled_class.bytecode_ptr[compiled_class.bytecode_length + 1] = cast(
        builtin_costs, felt
    );

    // Calculate the compiled class hash.
    %{
        vm_enter_scope({
            "bytecode_segment_structure": bytecode_segment_structures[ids.compiled_class_fact.hash]
        })
    %}
    let (hash) = compiled_class_hash(compiled_class);
    %{
        vm_exit_scope()

        computed_hash = ids.hash
        expected_hash = ids.compiled_class_fact.hash
        assert computed_hash == expected_hash, (
            "Computed compiled_class_hash is inconsistent with the hash in the os_input. "
            f"Computed hash = {computed_hash}, Expected hash = {expected_hash}.")
    %}

    assert compiled_class_fact.hash = hash;

    return validate_compiled_class_facts(
        n_compiled_class_facts=n_compiled_class_facts - 1,
        compiled_class_facts=&compiled_class_facts[1],
        builtin_costs=builtin_costs,
    );
}
