%builtins output pedersen range_check ecdsa bitwise ec_op keccak poseidon range_check96 add_mod mul_mod

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.cairo_builtins import (
    BitwiseBuiltin,
    HashBuiltin,
    KeccakBuiltin,
    ModBuiltin,
    PoseidonBuiltin,
)
from starkware.cairo.common.dict import dict_new, dict_update
from starkware.cairo.common.dict_access import DictAccess
from starkware.cairo.common.math import assert_not_equal
from starkware.cairo.common.math_cmp import is_nn
from starkware.cairo.common.registers import get_label_location
from starkware.cairo.common.segments import relocate_segment
from starkware.starknet.core.aggregator.combine_blocks import combine_blocks
from starkware.starknet.core.os.block_context import BlockContext, get_block_context
from starkware.starknet.core.os.constants import (
    BLOCK_HASH_CONTRACT_ADDRESS,
    STORED_BLOCK_HASH_BUFFER,
)
from starkware.starknet.core.os.contract_class.compiled_class import (
    CompiledClassFact,
    guess_compiled_class_facts,
    validate_compiled_class_facts_post_execution,
)
from starkware.starknet.core.os.contract_class.deprecated_compiled_class import (
    DeprecatedCompiledClassFact,
    deprecated_load_compiled_class_facts,
)
from starkware.starknet.core.os.execution.deprecated_execute_syscalls import (
    execute_deprecated_syscalls,
)
from starkware.starknet.core.os.execution.execute_syscalls import execute_syscalls
from starkware.starknet.core.os.execution.execute_transactions import execute_transactions
from starkware.starknet.core.os.os_config.os_config import get_starknet_os_config_hash
from starkware.starknet.core.os.output import (
    MessageToL1Header,
    MessageToL2Header,
    OsCarriedOutputs,
    OsOutput,
    OsOutputHeader,
    serialize_os_output,
)
from starkware.starknet.core.os.state.commitment import StateEntry
from starkware.starknet.core.os.state.state import OsStateUpdate, state_update

// Executes transactions on Starknet.
func main{
    output_ptr: felt*,
    pedersen_ptr: HashBuiltin*,
    range_check_ptr,
    ecdsa_ptr,
    bitwise_ptr: BitwiseBuiltin*,
    ec_op_ptr,
    keccak_ptr: KeccakBuiltin*,
    poseidon_ptr: PoseidonBuiltin*,
    range_check96_ptr: felt*,
    add_mod_ptr: ModBuiltin*,
    mul_mod_ptr: ModBuiltin*,
}() {
    alloc_locals;
    %{
        from starkware.starknet.core.os.os_hints import OsHintsConfig
        from starkware.starknet.core.os.os_input import StarknetOsInput

        os_input = StarknetOsInput.load(data=program_input)
        os_hints_config = OsHintsConfig.load(data=os_hints_config)
        block_input_iterator = iter(os_input.block_inputs)
    %}

    // Reserve the initial range check for self validation.
    // Note that this must point to the first range check used by the OS.
    let initial_range_check_ptr = range_check_ptr;
    let range_check_ptr = range_check_ptr + 1;

    local n_blocks = nondet %{ len(os_input.block_inputs) %};

    let (
        local n_compiled_class_facts, local compiled_class_facts, local builtin_costs
    ) = guess_compiled_class_facts();

    let (
        local n_deprecated_compiled_class_facts, deprecated_compiled_class_facts
    ) = deprecated_load_compiled_class_facts();

    let (local os_outputs: OsOutput*) = alloc();
    local initial_txs_range_check_ptr = nondet %{ segments.add_temp_segment() %};
    let txs_range_check_ptr = initial_txs_range_check_ptr;
    %{
        from starkware.starknet.core.os.execution_helper import StateUpdatePointers
        state_update_pointers = StateUpdatePointers(segments=segments)
    %}
    with txs_range_check_ptr {
        execute_blocks(
            n_blocks=n_blocks,
            os_output_per_block_dst=os_outputs,
            n_compiled_class_facts=n_compiled_class_facts,
            compiled_class_facts=compiled_class_facts,
            n_deprecated_compiled_class_facts=n_deprecated_compiled_class_facts,
            deprecated_compiled_class_facts=deprecated_compiled_class_facts,
        );
    }

    // Validate the guessed compile class facts.
    validate_compiled_class_facts_post_execution(
        n_compiled_class_facts=n_compiled_class_facts,
        compiled_class_facts=compiled_class_facts,
        builtin_costs=builtin_costs,
    );

    // Guess whether to use KZG commitment scheme and whether to output the full state.
    local use_kzg_da = nondet %{
        os_hints_config.use_kzg_da and (
            not os_hints_config.full_output
        )
    %};
    local full_output = nondet %{ os_hints_config.full_output %};

    // Verify that the guessed values are 0 or 1.
    assert use_kzg_da * use_kzg_da = use_kzg_da;
    assert full_output * full_output = full_output;

    let final_os_output = combine_blocks(
        n=n_blocks,
        os_outputs=os_outputs,
        os_program_hash=0,
        use_kzg_da=use_kzg_da,
        full_output=full_output,
    );

    // Serialize OS output.
    %{
        __serialize_data_availability_create_pages__ = True
        kzg_manager = global_hints.kzg_manager
    %}

    // Currently, the block hash is not enforced by the OS.
    serialize_os_output(os_output=final_os_output, replace_keys_with_aliases=TRUE);

    // The following code deals with the problem that untrusted code (contract code) could
    // potentially move builtin pointers backward, compromising the soundness of those builtins.
    //
    // The check that the pointers can only move forward is done in `validate_builtins`,
    // but `validate_builtins` itself relies on range checks.
    //
    // To guarantee the validity of this mechanism, we split range checks into:
    //   * OS range checks (used internally by the OS, and in particular by `validate_builtins`).
    //   * Transaction range checks (used by contracts).
    //
    // The OS range checks are located at `[initial_range_check_ptr, reserved_range_checks_end)` and
    // the transaction range checks are located at `[reserved_range_checks_end, range_check_ptr)`.
    //
    // The following `assert_not_equal` guarantees that at least one value
    // (`[initial_range_check_ptr]`) is range-checked by ensuring
    //   `range_check_ptr != initial_range_check_ptr`,
    // which implies
    //   `range_check_ptr >= initial_range_check_ptr + 1`.
    // Combined with the next assertion, we establish that
    //   `range_check_ptr >= reserved_range_checks_end`,
    // which confirms that all OS range checks are sound.
    //
    // Since `validate_builtins` relies on OS range checks, proving their validity ensures that all
    // calls to `validate_builtins` remain sound, thereby maintaining the integrity of all the
    // builtins.
    let reserved_range_checks_end = range_check_ptr;
    // Relocate the range checks used by the transactions after the range checks used by the OS.
    relocate_segment(
        src_ptr=cast(initial_txs_range_check_ptr, felt*),
        dest_ptr=cast(reserved_range_checks_end, felt*),
    );
    let range_check_ptr = txs_range_check_ptr;

    assert_not_equal(initial_range_check_ptr, range_check_ptr);
    assert [initial_range_check_ptr] = range_check_ptr - reserved_range_checks_end;

    return ();
}

// Executes `n_blocks` blocks. For each block,
//   * Runs the transactions,
//   * Updates the state,
//   * Produces the OS output and writes it to `os_output_per_block_dst`.
//
// Hint arguments:
// state_update_pointers - A class that manages the pointers of the squashed state changes.
// block_input_iterator - an iterator for Block-related input, such as the transaction to execute.
// global_hints - hints that are used to create the execution helper.
func execute_blocks{
    output_ptr: felt*,
    pedersen_ptr: HashBuiltin*,
    range_check_ptr,
    ecdsa_ptr,
    bitwise_ptr: BitwiseBuiltin*,
    ec_op_ptr,
    keccak_ptr: KeccakBuiltin*,
    poseidon_ptr: PoseidonBuiltin*,
    range_check96_ptr: felt*,
    add_mod_ptr: ModBuiltin*,
    mul_mod_ptr: ModBuiltin*,
    txs_range_check_ptr,
}(
    n_blocks: felt,
    os_output_per_block_dst: OsOutput*,
    n_compiled_class_facts: felt,
    compiled_class_facts: CompiledClassFact*,
    n_deprecated_compiled_class_facts: felt,
    deprecated_compiled_class_facts: DeprecatedCompiledClassFact*,
) {
    %{ print(f"execute_blocks: {ids.n_blocks} blocks remaining.") %}
    if (n_blocks == 0) {
        return ();
    }
    alloc_locals;

    %{
        from starkware.starknet.core.os.os_hints import get_execution_helper_and_syscall_handlers
        block_input = next(block_input_iterator)
        (
            execution_helper,
            syscall_handler,
            deprecated_syscall_handler
        ) = get_execution_helper_and_syscall_handlers(
            block_input=block_input, global_hints=global_hints, os_hints_config=os_hints_config
        )
    %}

    // Allocate segments for the messages.
    let (messages_to_l1: MessageToL1Header*) = alloc();
    let (messages_to_l2: MessageToL2Header*) = alloc();
    tempvar initial_carried_outputs = new OsCarriedOutputs(
        messages_to_l1=messages_to_l1, messages_to_l2=messages_to_l2
    );

    let (
        contract_state_changes: DictAccess*, contract_class_changes: DictAccess*
    ) = initialize_state_changes();
    // Keep a reference to the start of contract_state_changes and contract_class_changes.
    let contract_state_changes_start = contract_state_changes;
    let contract_class_changes_start = contract_class_changes;

    // Build block context.
    let (execute_syscalls_ptr) = get_label_location(label_value=execute_syscalls);
    let (execute_deprecated_syscalls_ptr) = get_label_location(
        label_value=execute_deprecated_syscalls
    );

    let (block_context: BlockContext*) = get_block_context(
        execute_syscalls_ptr=execute_syscalls_ptr,
        execute_deprecated_syscalls_ptr=execute_deprecated_syscalls_ptr,
        n_compiled_class_facts=n_compiled_class_facts,
        compiled_class_facts=compiled_class_facts,
        n_deprecated_compiled_class_facts=n_deprecated_compiled_class_facts,
        deprecated_compiled_class_facts=deprecated_compiled_class_facts,
    );

    // Pre-process block.
    with contract_state_changes {
        write_block_number_to_block_hash_mapping(block_context=block_context);
    }

    // Execute transactions.
    let outputs = initial_carried_outputs;
    with contract_state_changes, contract_class_changes, outputs {
        execute_transactions(block_context=block_context);
    }
    let final_carried_outputs = outputs;

    %{
        from starkware.starknet.definitions.constants import ALIAS_CONTRACT_ADDRESS

        # This hint shouldn't be whitelisted.
        vm_enter_scope(dict(
            state_update_pointers=state_update_pointers,
            aliases=execution_helper.storage_by_address[ALIAS_CONTRACT_ADDRESS],
            execution_helper=execution_helper,
            __dict_manager=__dict_manager,
            block_input=block_input,
        ))
    %}

    let (squashed_os_state_update, state_update_output) = state_update{hash_ptr=pedersen_ptr}(
        os_state_update=OsStateUpdate(
            contract_state_changes_start=contract_state_changes_start,
            contract_state_changes_end=contract_state_changes,
            contract_class_changes_start=contract_class_changes_start,
            contract_class_changes_end=contract_class_changes,
        ),
    );

    %{ vm_exit_scope() %}

    // Compute the general config hash.
    // This is done here to avoid passing pedersen_ptr to serialize_output_header.
    let hash_ptr = pedersen_ptr;
    with hash_ptr {
        let (starknet_os_config_hash) = get_starknet_os_config_hash(
            starknet_os_config=&block_context.starknet_os_config
        );
    }
    let pedersen_ptr = hash_ptr;

    // All blocks inside of a multi block should be off-chain and therefore
    // should not be compressed.
    let use_kzg_da = 0;
    let full_output = 1;

    assert os_output_per_block_dst[0] = OsOutput(
        header=new OsOutputHeader(
            state_update_output=state_update_output,
            prev_block_number=block_context.block_info_for_execute.block_number - 1,
            new_block_number=block_context.block_info_for_execute.block_number,
            prev_block_hash=nondet %{ block_input.prev_block_hash %},
            new_block_hash=nondet %{ block_input.new_block_hash %},
            os_program_hash=0,
            starknet_os_config_hash=starknet_os_config_hash,
            use_kzg_da=use_kzg_da,
            full_output=full_output,
        ),
        squashed_os_state_update=squashed_os_state_update,
        initial_carried_outputs=initial_carried_outputs,
        final_carried_outputs=final_carried_outputs,
    );

    return execute_blocks(
        n_blocks=n_blocks - 1,
        os_output_per_block_dst=&os_output_per_block_dst[1],
        n_compiled_class_facts=n_compiled_class_facts,
        compiled_class_facts=compiled_class_facts,
        n_deprecated_compiled_class_facts=n_deprecated_compiled_class_facts,
        deprecated_compiled_class_facts=deprecated_compiled_class_facts,
    );
}

// Initializes state changes dictionaries.
func initialize_state_changes() -> (
    contract_state_changes: DictAccess*, contract_class_changes: DictAccess*
) {
    %{
        from starkware.python.utils import from_bytes

        initial_dict = {
            address: segments.gen_arg(
                (from_bytes(contract.contract_hash), segments.add(), contract.nonce))
            for address, contract in block_input.contracts.items()
        }
    %}
    // A dictionary from contract address to a dict of storage changes of type StateEntry.
    let (contract_state_changes: DictAccess*) = dict_new();

    %{ initial_dict = block_input.class_hash_to_compiled_class_hash %}
    // A dictionary from class hash to compiled class hash (Casm).
    let (contract_class_changes: DictAccess*) = dict_new();

    return (
        contract_state_changes=contract_state_changes, contract_class_changes=contract_class_changes
    );
}

// Writes the hash of the (current_block_number - buffer) block under its block number in the
// dedicated contract state, where buffer=STORED_BLOCK_HASH_BUFFER.
func write_block_number_to_block_hash_mapping{range_check_ptr, contract_state_changes: DictAccess*}(
    block_context: BlockContext*
) {
    alloc_locals;
    tempvar old_block_number = block_context.block_info_for_execute.block_number -
        STORED_BLOCK_HASH_BUFFER;
    let is_old_block_number_non_negative = is_nn(old_block_number);
    if (is_old_block_number_non_negative == FALSE) {
        // Not enough blocks in the system - nothing to write.
        return ();
    }

    // Fetch the (block number -> block hash) mapping contract state.
    local state_entry: StateEntry*;
    %{
        ids.state_entry = __dict_manager.get_dict(ids.contract_state_changes)[
            ids.BLOCK_HASH_CONTRACT_ADDRESS
        ]
    %}

    // Currently, the block hash mapping is not enforced by the OS.
    local old_block_hash;
    %{
        old_block_number_and_hash = block_input.old_block_number_and_hash
        assert (
            old_block_number_and_hash is not None
        ), f"Block number is probably < {ids.STORED_BLOCK_HASH_BUFFER}."
        (
            old_block_number, old_block_hash
        ) = old_block_number_and_hash
        assert old_block_number == ids.old_block_number,(
            "Inconsistent block number. "
            "The constant STORED_BLOCK_HASH_BUFFER is probably out of sync."
        )
        ids.old_block_hash = old_block_hash
    %}

    // Update mapping.
    assert state_entry.class_hash = 0;
    assert state_entry.nonce = 0;
    tempvar storage_ptr = state_entry.storage_ptr;
    assert [storage_ptr] = DictAccess(key=old_block_number, prev_value=0, new_value=old_block_hash);
    let storage_ptr = storage_ptr + DictAccess.SIZE;
    %{
        storage = execution_helper.storage_by_address[ids.BLOCK_HASH_CONTRACT_ADDRESS]
        storage.write(key=ids.old_block_number, value=ids.old_block_hash)
    %}

    // Update contract state.
    tempvar new_state_entry = new StateEntry(class_hash=0, storage_ptr=storage_ptr, nonce=0);
    dict_update{dict_ptr=contract_state_changes}(
        key=BLOCK_HASH_CONTRACT_ADDRESS,
        prev_value=cast(state_entry, felt),
        new_value=cast(new_state_entry, felt),
    );
    return ();
}
