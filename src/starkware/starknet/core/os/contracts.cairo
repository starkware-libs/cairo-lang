from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.hash_state import (
    HashState,
    hash_finalize,
    hash_init,
    hash_update,
    hash_update_single,
)
from starkware.cairo.common.math import assert_lt_felt
from starkware.cairo.common.registers import get_fp_and_pc

const API_VERSION = 0

struct ContractEntryPoint:
    # A field element that encodes the signature of the called function.
    member selector : felt
    # The offset of the instruction that should be called within the contract bytecode.
    member offset : felt
end

struct ContractDefinition:
    member api_version : felt

    # The length and pointer to the external entry point table of the contract.
    member n_external_functions : felt
    member external_functions : ContractEntryPoint*

    # The length and pointer to the L1 handler entry point table of the contract.
    member n_l1_handlers : felt
    member l1_handlers : ContractEntryPoint*

    # The length and pointer to the constructor entry point table of the contract.
    member n_constructors : felt
    member constructors : ContractEntryPoint*

    member n_builtins : felt
    # 'builtin_list' is a continuous memory segment containing the ASCII encoding of the (ordered)
    # builtins used by the program.
    member builtin_list : felt*

    # The hinted_contract_definition_hash field should be set to the starknet_keccak of the
    # contract program, including its hints. However the OS does not validate that.
    # This field may be used by the operator to differentiate between contract definitions that
    # differ only in the hints.
    # This field is included in the hash of the ContractDefinition to simplify the implementation.
    member hinted_contract_definition_hash : felt

    # The length and pointer of the bytecode.
    member bytecode_length : felt
    member bytecode_ptr : felt*
end

# Checks that the list of selectors is sorted.
func validate_entry_points{range_check_ptr}(
    n_entry_points : felt, entry_points : ContractEntryPoint*
):
    if n_entry_points == 0:
        return ()
    end

    return validate_entry_points_inner(
        n_entry_points=n_entry_points - 1,
        entry_points=&entry_points[1],
        prev_selector=entry_points[0].selector,
    )
end

# Inner function for validate_entry_points.
func validate_entry_points_inner{range_check_ptr}(
    n_entry_points : felt, entry_points : ContractEntryPoint*, prev_selector
):
    if n_entry_points == 0:
        return ()
    end

    assert_lt_felt(prev_selector, entry_points.selector)

    return validate_entry_points_inner(
        n_entry_points=n_entry_points - 1,
        entry_points=&entry_points[1],
        prev_selector=entry_points[0].selector,
    )
end

func contract_hash{hash_ptr : HashBuiltin*}(contract_definition : ContractDefinition*) -> (
    hash : felt
):
    let (hash_state : HashState*) = hash_init()
    let (hash_state) = hash_update_single(
        hash_state_ptr=hash_state, item=contract_definition.api_version
    )

    # Hash external entry points.
    let (hash_state) = hash_update_with_hashchain(
        hash_state=hash_state,
        data_ptr=contract_definition.external_functions,
        data_length=contract_definition.n_external_functions * ContractEntryPoint.SIZE,
    )

    # Hash L1 handler entry points.
    let (hash_state) = hash_update_with_hashchain(
        hash_state=hash_state,
        data_ptr=contract_definition.l1_handlers,
        data_length=contract_definition.n_l1_handlers * ContractEntryPoint.SIZE,
    )

    # Hash constructor entry points.
    let (hash_state) = hash_update_with_hashchain(
        hash_state=hash_state,
        data_ptr=contract_definition.constructors,
        data_length=contract_definition.n_constructors * ContractEntryPoint.SIZE,
    )

    # Hash builtins.
    let (hash_state) = hash_update_with_hashchain(
        hash_state=hash_state,
        data_ptr=contract_definition.builtin_list,
        data_length=contract_definition.n_builtins,
    )

    # Hash hinted_contract_definition_hash.
    let (hash_state) = hash_update_single(
        hash_state_ptr=hash_state, item=contract_definition.hinted_contract_definition_hash
    )

    # Hash bytecode.
    let (hash_state) = hash_update_with_hashchain(
        hash_state=hash_state,
        data_ptr=contract_definition.bytecode_ptr,
        data_length=contract_definition.bytecode_length,
    )

    let (hash : felt) = hash_finalize(hash_state_ptr=hash_state)
    return (hash=hash)
end

func hash_update_with_hashchain{hash_ptr : HashBuiltin*}(
    hash_state : HashState*, data_ptr : felt*, data_length : felt
) -> (hash_state : HashState*):
    # Hash data.
    let (list_hash_state : HashState*) = hash_init()
    let (list_hash_state) = hash_update(
        hash_state_ptr=list_hash_state, data_ptr=data_ptr, data_length=data_length
    )
    let (hash : felt) = hash_finalize(hash_state_ptr=list_hash_state)

    # Update contract hash state with the resulting hash of the data.
    let (hash_state) = hash_update_single(hash_state_ptr=hash_state, item=hash)
    return (hash_state=hash_state)
end

# A list entry that maps a hash to the corresponding contract definition.
struct ContractDefinitionFact:
    # The hash of the contract. This member should be first, so that we can lookup items
    # with the hash as key, using find_element().
    member hash : felt
    member contract_definition : ContractDefinition*
end

# Loads the contract definitions from the 'os_input' hint variable.
# Returns ContractDefinitionFact list that maps a hash to a ContractDefinition.
func load_contract_definition_facts{pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
    n_contract_definition_facts, contract_definition_facts : ContractDefinitionFact*
):
    alloc_locals
    local n_contract_definition_facts
    local contract_definition_facts : ContractDefinitionFact*
    %{
        ids.contract_definition_facts = segments.add()
        ids.n_contract_definition_facts = len(os_input.contract_definitions)
        vm_enter_scope({
            'contract_definitions_facts' : iter(os_input.contract_definitions.items()),
        })
    %}

    load_contract_definition_facts_inner(
        n_contract_definition_facts=n_contract_definition_facts,
        contract_definition_facts=contract_definition_facts,
    )
    %{ vm_exit_scope() %}

    return (
        n_contract_definition_facts=n_contract_definition_facts,
        contract_definition_facts=contract_definition_facts,
    )
end

# Loads 'n_contract_definition_facts' from the hint 'contract_definitions_facts' and appends the
# corresponding ContractDefinitionFact to contract_definition_facts.
func load_contract_definition_facts_inner{pedersen_ptr : HashBuiltin*, range_check_ptr}(
    n_contract_definition_facts, contract_definition_facts : ContractDefinitionFact*
):
    if n_contract_definition_facts == 0:
        return ()
    end
    alloc_locals

    let contract_definition_fact = contract_definition_facts
    let contract_definition = contract_definition_fact.contract_definition

    # Fetch contract data form hints.
    %{
        from starkware.starknet.core.os.contract_hash import get_contract_definition_struct

        contract_hash, contract_definition = next(contract_definitions_facts)

        cairo_contract = get_contract_definition_struct(
            identifiers=ids._context.identifiers, contract_definition=contract_definition)
        ids.contract_definition = segments.gen_arg(cairo_contract)
    %}

    assert contract_definition.api_version = API_VERSION

    validate_entry_points(
        n_entry_points=contract_definition.n_external_functions,
        entry_points=contract_definition.external_functions,
    )

    validate_entry_points(
        n_entry_points=contract_definition.n_l1_handlers,
        entry_points=contract_definition.l1_handlers,
    )

    let (hash) = contract_hash{hash_ptr=pedersen_ptr}(contract_definition)
    contract_definition_fact.hash = hash

    %{
        from starkware.python.utils import from_bytes

        computed_hash = ids.contract_definition_fact.hash
        expected_hash = from_bytes(contract_hash)
        assert computed_hash == expected_hash, (
            "Computed contract_hash is inconsistent with the hash in the os_input"
            f"Computed hash = {computed_hash}, Expected hash = {expected_hash}.")

        vm_load_program(contract_definition.program, ids.contract_definition.bytecode_ptr)
    %}

    return load_contract_definition_facts_inner(
        n_contract_definition_facts=n_contract_definition_facts - 1,
        contract_definition_facts=contract_definition_facts + ContractDefinitionFact.SIZE,
    )
end
