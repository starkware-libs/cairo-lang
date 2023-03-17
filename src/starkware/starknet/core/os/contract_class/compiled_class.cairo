from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import PoseidonBuiltin
from starkware.cairo.common.hash_state_poseidon import (
    HashState,
    hash_finalize,
    hash_init,
    hash_update_single,
    hash_update_with_nested_hash,
)
from starkware.cairo.common.math import assert_lt_felt
from starkware.cairo.common.registers import get_fp_and_pc

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

func compiled_class_hash{poseidon_ptr: PoseidonBuiltin*}(compiled_class: CompiledClass*) -> (
    hash: felt
) {
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
        hash_update_with_nested_hash(
            data_ptr=compiled_class.bytecode_ptr, data_length=compiled_class.bytecode_length
        );
    }

    let hash: felt = hash_finalize(hash_state=hash_state);
    return (hash=hash);
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

// Loads the contract classes from the 'os_input' hint variable.
// Returns CompiledClassFact list that maps a hash to a CompiledClass.
func load_compiled_class_facts{poseidon_ptr: PoseidonBuiltin*, range_check_ptr}() -> (
    n_compiled_class_facts: felt, compiled_class_facts: CompiledClassFact*
) {
    alloc_locals;
    local n_compiled_class_facts;
    local compiled_class_facts: CompiledClassFact*;
    %{
        ids.compiled_class_facts = segments.add()
        ids.n_compiled_class_facts = len(os_input.compiled_classes)
        vm_enter_scope({
            'compiled_class_facts': iter(os_input.compiled_classes.items()),
        })
    %}

    let (builtin_costs: felt*) = alloc();
    assert builtin_costs[0] = 0;
    assert builtin_costs[1] = 0;
    assert builtin_costs[2] = 0;
    assert builtin_costs[3] = 0;
    assert builtin_costs[4] = 0;

    load_compiled_class_facts_inner(
        n_compiled_class_facts=n_compiled_class_facts,
        compiled_class_facts=compiled_class_facts,
        builtin_costs=builtin_costs,
    );
    %{ vm_exit_scope() %}

    return (
        n_compiled_class_facts=n_compiled_class_facts, compiled_class_facts=compiled_class_facts
    );
}

// Loads 'n_compiled_class_facts' from the hint 'compiled_class_facts' and appends the
// corresponding CompiledClassFact to compiled_class_facts.
func load_compiled_class_facts_inner{poseidon_ptr: PoseidonBuiltin*, range_check_ptr}(
    n_compiled_class_facts, compiled_class_facts: CompiledClassFact*, builtin_costs: felt*
) {
    if (n_compiled_class_facts == 0) {
        return ();
    }
    alloc_locals;

    let compiled_class_fact = compiled_class_facts[0];
    let compiled_class = compiled_class_fact.compiled_class;

    // Fetch contract data form hints.
    %{
        from starkware.starknet.core.os.contract_class.compiled_class_hash import (
            get_compiled_class_struct,
        )

        compiled_class_hash, compiled_class = next(compiled_class_facts)

        cairo_contract = get_compiled_class_struct(
            identifiers=ids._context.identifiers, compiled_class=compiled_class)
        ids.compiled_class = segments.gen_arg(cairo_contract)
    %}

    validate_entry_points(
        n_entry_points=compiled_class.n_external_functions,
        entry_points=compiled_class.external_functions,
    );

    validate_entry_points(
        n_entry_points=compiled_class.n_l1_handlers, entry_points=compiled_class.l1_handlers
    );

    let (hash) = compiled_class_hash(compiled_class);
    compiled_class_fact.hash = hash;

    // Compiled classes are expected to end with a `ret` opcode followed by a pointer to the
    // builtin costs.
    assert compiled_class.bytecode_ptr[compiled_class.bytecode_length] = 0x208b7fff7fff7ffe;
    assert compiled_class.bytecode_ptr[compiled_class.bytecode_length + 1] = cast(
        builtin_costs, felt
    );

    %{
        computed_hash = ids.compiled_class_fact.hash
        expected_hash = compiled_class_hash
        assert computed_hash == expected_hash, (
            "Computed compiled_class_hash is inconsistent with the hash in the os_input. "
            f"Computed hash = {computed_hash}, Expected hash = {expected_hash}.")

        vm_load_program(
            compiled_class.get_runnable_program(entrypoint_builtins=[]),
            ids.compiled_class.bytecode_ptr
        )
    %}

    return load_compiled_class_facts_inner(
        n_compiled_class_facts=n_compiled_class_facts - 1,
        compiled_class_facts=compiled_class_facts + CompiledClassFact.SIZE,
        builtin_costs=builtin_costs,
    );
}
