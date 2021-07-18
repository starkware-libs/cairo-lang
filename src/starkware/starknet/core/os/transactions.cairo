from starkware.cairo.builtin_selection.select_builtins import select_builtins
from starkware.cairo.builtin_selection.validate_builtins import validate_builtin, validate_builtins
from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.dict import dict_new, dict_read, dict_update, dict_write
from starkware.cairo.common.dict_access import DictAccess
from starkware.cairo.common.find_element import find_element
from starkware.cairo.common.math import assert_not_zero
from starkware.cairo.common.memcpy import memcpy
from starkware.cairo.common.registers import get_ap, get_fp_and_pc
from starkware.cairo.common.segments import relocate_segment
from starkware.starknet.common.storage import Storage
from starkware.starknet.common.syscalls import SendMessageToL1SysCall
from starkware.starknet.core.os.contracts import (
    ContractDefinition, ContractDefinitionFact, ContractEntryPoint, load_contract_definition_facts)
from starkware.starknet.core.os.output import MessageHeader, OsCarriedOutputs
from starkware.starknet.core.os.state import StateEntry

const UNINITIALIZED_CONTRACT_HASH = 0

# The amount of range checks we need to reserve for the OS to validate an invoke transaction.
const RANGE_CHECKS_PER_INVOKE_TRANSACTION = 4 + (1 + BuiltinEncodings.SIZE)

struct Transaction:
    member contract_address : felt
    member selector : felt
    member calldata_size : felt
    member calldata : felt*
end

# A dictionary from address to StateEntry.
struct StateChanges:
    member changes_start : DictAccess*
    member changes_end : DictAccess*
end

struct BuiltinPointers:
    member pedersen : HashBuiltin*
    member range_check : felt
    member ecdsa : felt
end

# A struct containing the ASCII encoding of each builtin.
struct BuiltinEncodings:
    member pedersen : felt
    member range_check : felt
    member ecdsa : felt
end

# A struct containing the instance size of each builtin.
struct BuiltinInstanceSizes:
    member pedersen : felt
    member range_check : felt
    member ecdsa : felt
end

struct BuiltinParams:
    member builtin_encodings : BuiltinEncodings*
    member builtin_instance_sizes : BuiltinInstanceSizes*
end

struct ExecuteTransactionContext:
    member builtin_params : BuiltinParams*
    member n_contract_definition_facts : felt
    member contract_definition_facts : ContractDefinitionFact*
end

func get_builtin_params() -> (builtin_params : BuiltinParams*):
    alloc_locals
    let (local __fp__, _) = get_fp_and_pc()

    local builtin_encodings : BuiltinEncodings
    builtin_encodings.pedersen = %[int.from_bytes('pedersen'.encode('ascii'), 'big')%]
    builtin_encodings.range_check = %[int.from_bytes('range_check'.encode('ascii'), 'big')%]
    builtin_encodings.ecdsa = %[int.from_bytes('ecdsa'.encode('ascii'), 'big')%]

    local builtin_instance_sizes : BuiltinInstanceSizes
    builtin_instance_sizes.pedersen = HashBuiltin.SIZE
    builtin_instance_sizes.range_check = 1
    builtin_instance_sizes.ecdsa = SignatureBuiltin.SIZE

    local builtin_params : BuiltinParams
    assert builtin_params.builtin_encodings = &builtin_encodings
    assert builtin_params.builtin_instance_sizes = &builtin_instance_sizes
    return (builtin_params=&builtin_params)
end

# Executes the transactions in the hint variable os_input.transactions.
#
# Returns:
# reserved_range_checks_end - end pointer for the reserved range checks.
# state_changes - StateChanges struct corresponding to the changes that were done by
#   the transactions.
#
# Assumptions:
#   The caller verifies that the memory range [range_check_ptr, reserved_range_checks_end)
#   corresponds to valid range check instances.
#   Note that if the assumption above does not hold it might be the case that
#   the returned range_check_ptr is smaller then reserved_range_checks_end.
func execute_transactions{
        pedersen_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr, outputs : OsCarriedOutputs}() -> (
        reserved_range_checks_end, state_changes : StateChanges):
    alloc_locals
    local n_txs
    %{
        ids.n_txs = len(os_input.transactions)

        initial_dict = {
            address: segments.gen_arg(
                (int.from_bytes(contract.contract_hash, 'big'), segments.add()))
            for address, contract in os_input.contracts.items()
        }
    %}
    # A dict from contract address to a dict of storage changes.
    let (local global_state_changes : DictAccess*) = dict_new()

    local execute_tx_context : ExecuteTransactionContext
    let (n_contract_definition_facts, contract_definition_facts) = load_contract_definition_facts()
    assert execute_tx_context.n_contract_definition_facts = n_contract_definition_facts
    assert execute_tx_context.contract_definition_facts = contract_definition_facts

    let (local __fp__, _) = get_fp_and_pc()
    local local_builtin_ptrs : BuiltinPointers
    assert local_builtin_ptrs.pedersen = pedersen_ptr

    %{ ids.local_builtin_ptrs.range_check = segments.add_temp_segment() %}
    local_builtin_ptrs.ecdsa = ecdsa_ptr

    let (builtin_params) = get_builtin_params()
    assert execute_tx_context.builtin_params = builtin_params

    let builtin_ptrs = &local_builtin_ptrs
    %{
        vm_enter_scope({
            'storage_by_address' : storage_by_address,
            'transactions' : iter(os_input.transactions),
            '__dict_manager' : __dict_manager,
        })
    %}
    # Keep a reference to the start of global_state_changes.
    let global_state_changes_start = global_state_changes
    execute_transactions_inner{
        builtin_ptrs=builtin_ptrs, global_state_changes=global_state_changes}(
        execute_tx_context=&execute_tx_context, n_txs=n_txs)
    %{ vm_exit_scope() %}

    let reserved_range_checks_end = range_check_ptr
    # Relocate the range checks used by the transactions to reserved_range_checks_end.
    relocate_segment(
        src_ptr=cast(local_builtin_ptrs.range_check, felt*),
        dest_ptr=cast(reserved_range_checks_end, felt*))

    let pedersen_ptr = builtin_ptrs.pedersen
    let range_check_ptr = builtin_ptrs.range_check
    let ecdsa_ptr = builtin_ptrs.ecdsa
    return (
        reserved_range_checks_end=reserved_range_checks_end,
        state_changes=StateChanges(global_state_changes_start, global_state_changes))
end

# Inner function for execute_transactions.
# Arguments:
# execute_tx_context - a read-only context used for transaction execution.
# n_txs - the number of transactions to execute.
#
# Implicit arguments:
# range_check_ptr - a range check builtin, used and advanced by the OS, not the transactions.
# builtin_ptrs - a struct of builtin pointer that are going to be used by the
# executed transactions.
# The range-checks used internally by the transactions do not affect range_check_ptr.
# They are accounted for in builtin_ptrs.
func execute_transactions_inner{
        range_check_ptr, builtin_ptrs : BuiltinPointers*, global_state_changes : DictAccess*,
        outputs : OsCarriedOutputs}(execute_tx_context : ExecuteTransactionContext*, n_txs):
    if n_txs == 0:
        return ()
    end

    # Guess if the current transaction is a deploy transaction.
    %{
        from starkware.starknet.business_logic.internal_transaction import InternalDeploy

        tx = next(transactions)
        memory[ap] = 1 if isinstance(tx, InternalDeploy) else 0
    %}

    jmp deploy_transaction if [ap] != 0; ap++

    # Handle invoke_transaction.
    execute_invoke_transaction(execute_tx_context=execute_tx_context)

    return execute_transactions_inner(execute_tx_context=execute_tx_context, n_txs=n_txs - 1)

    deploy_transaction:
    # Handle deploy_transaction.
    execute_deploy_transaction()

    return execute_transactions_inner(execute_tx_context=execute_tx_context, n_txs=n_txs - 1)
end

func execute_syscalls{
        range_check_ptr, builtin_ptrs : BuiltinPointers*, global_state_changes : DictAccess*,
        outputs : OsCarriedOutputs}(
        execute_tx_context : ExecuteTransactionContext*, caller_address, syscall_size,
        syscall_ptr : felt*):
    if syscall_size == 0:
        return ()
    end

    # Currently only the 'SendMessageToL1' system call is supported.
    assert [syscall_ptr] = %[int.from_bytes(b'SendMessageToL1', 'big')%]

    let syscall = [cast(syscall_ptr, SendMessageToL1SysCall*)]

    assert [outputs.messages_to_l1] = MessageHeader(
        from_address=caller_address,
        to_address=syscall.to_address,
        payload_size=syscall.payload_size)
    memcpy(
        dst=outputs.messages_to_l1 + MessageHeader.SIZE,
        src=syscall.payload_ptr,
        len=syscall.payload_size)
    tempvar outputs = OsCarriedOutputs(
        messages_to_l1=outputs.messages_to_l1 + MessageHeader.SIZE +
            outputs.messages_to_l1.payload_size,
        messages_to_l2=outputs.messages_to_l2)
    return execute_syscalls(
        execute_tx_context=execute_tx_context,
        caller_address=caller_address,
        syscall_size=syscall_size - 4,
        syscall_ptr=syscall_ptr + 4)
end

func consume_l1_to_l2_message{outputs : OsCarriedOutputs}(tx : Transaction*):
    assert_not_zero(tx.calldata_size)
    # The raw payload is the calldata without the from_address argument (which is the first).
    tempvar raw_payload : felt* = tx.calldata + 1
    tempvar raw_payload_size = tx.calldata_size - 1

    # Write the given transaction to the output.
    assert [outputs.messages_to_l2] = MessageHeader(
        from_address=[tx.calldata],
        to_address=tx.contract_address,
        # raw_payload_size + selector.
        payload_size=raw_payload_size + 1)

    # The payload consists of the selector and the raw payload.
    let message_payload = cast(outputs.messages_to_l2 + MessageHeader.SIZE, felt*)
    assert [message_payload] = tx.selector
    memcpy(dst=message_payload + 1, src=raw_payload, len=raw_payload_size)

    tempvar outputs = OsCarriedOutputs(
        messages_to_l1=outputs.messages_to_l1,
        messages_to_l2=outputs.messages_to_l2 + MessageHeader.SIZE +
            outputs.messages_to_l2.payload_size)
    return ()
end

func execute_invoke_transaction{
        range_check_ptr, builtin_ptrs : BuiltinPointers*, global_state_changes : DictAccess*,
        outputs : OsCarriedOutputs}(execute_tx_context : ExecuteTransactionContext*):
    alloc_locals
    local tx : Transaction*
    local state_entry : StateEntry*

    %{
        from starkware.starknet.business_logic.internal_transaction import InternalInvokeFunction

        assert isinstance(tx, InternalInvokeFunction), \
            f'Expected a tx of type InternalInvokeFunction, got {tx}.'
        ids.tx = segments.gen_arg(
            arg=[tx.contract_address, tx.entry_point_selector, len(tx.calldata), tx.calldata])

        # Fetch a state_entry in this hint and validate it in the update at the end
        # of this function.
        ids.state_entry = __dict_manager.get_dict(
            ids.global_state_changes)[ids.tx.contract_address]
    %}

    # The key must be at offset 0.
    static_assert ContractDefinitionFact.hash == 0
    let (contract_definition_fact : ContractDefinitionFact*) = find_element(
        array_ptr=execute_tx_context.contract_definition_facts,
        elm_size=ContractDefinitionFact.SIZE,
        n_elms=execute_tx_context.n_contract_definition_facts,
        key=state_entry.contract_hash)

    local contract_definition : ContractDefinition* = contract_definition_fact.contract_definition

    # The key must be at offset 0.
    static_assert ContractEntryPoint.selector == 0
    local is_l1_handler : felt

    %{
        from starkware.starknet.services.api.contract_definition import EntryPointType

        if tx.entry_point_type is EntryPointType.L1_HANDLER:
            ids.is_l1_handler = 1
        elif tx.entry_point_type is EntryPointType.EXTERNAL:
            ids.is_l1_handler = 0
        else:
            raise NotImplementedError(f'Unexpected EntryPointType: {tx.entry_point_type}.')
    %}

    local range_check_ptr = range_check_ptr
    local global_state_changes : DictAccess* = global_state_changes
    if is_l1_handler != 0:
        consume_l1_to_l2_message(tx=tx)
        tempvar entry_points : ContractEntryPoint* = contract_definition.l1_handlers
        tempvar n_entry_points : felt = contract_definition.n_l1_handlers
    else:
        tempvar outputs = outputs
        tempvar entry_points : ContractEntryPoint* = contract_definition.external_functions
        tempvar n_entry_points : felt = contract_definition.n_external_functions
    end

    local outputs : OsCarriedOutputs = outputs

    let (entry_point_desc : ContractEntryPoint*) = find_element(
        array_ptr=cast(entry_points, felt*),
        elm_size=ContractEntryPoint.SIZE,
        n_elms=n_entry_points,
        key=tx.selector)
    local range_check_ptr = range_check_ptr

    # A pointer to the contract entry point within the bytecode.
    local contract_entry_point : felt* = contract_definition.bytecode_ptr + entry_point_desc.offset

    local os_context : felt*
    local syscall_ptr : felt*

    %{
        ids.os_context = segments.add()
        ids.syscall_ptr = segments.add()
    %}
    assert [os_context] = cast(syscall_ptr, felt)
    assert [os_context + 1] = cast(state_entry.storage_ptr, felt)

    let n_builtins = BuiltinEncodings.SIZE
    local builtin_params : BuiltinParams* = execute_tx_context.builtin_params
    select_builtins(
        n_builtins=n_builtins,
        all_encodings=builtin_params.builtin_encodings,
        all_ptrs=builtin_ptrs,
        n_selected_builtins=contract_definition.n_builtins,
        selected_encodings=contract_definition.builtin_list,
        selected_ptrs=os_context + 2)

    # Use tempvar to pass arguments to contract_entry_point().
    tempvar context = os_context
    tempvar calldata_size = tx.calldata_size
    tempvar calldata = tx.calldata
    %{ vm_enter_scope({'__storage' : storage_by_address[ids.tx.contract_address]}) %}
    call abs contract_entry_point
    %{ vm_exit_scope() %}
    # Retrieve returned_builtin_ptrs_subset.
    # Note that returned_builtin_ptrs_subset cannot be set in a hint because doing so will allow a
    # malicious prover to lie about the storage changes of a valid contract.
    let (ap_val) = get_ap()
    local returned_builtin_ptrs_subset : felt* = cast(
        ap_val - contract_definition.n_builtins - 2, felt*)
    local retdata_size : felt = [ap_val - 2]
    local retdata_ptr : felt* = cast([ap_val - 1], felt*)

    local return_builtin_ptrs : BuiltinPointers*
    %{
        from starkware.starknet.core.os.os_utils import update_builtin_pointers

        # Fill the values of all builtin pointers after the current transaction.
        ids.return_builtin_ptrs = segments.gen_arg(
            update_builtin_pointers(
                memory=memory,
                n_builtins=ids.n_builtins,
                builtins_encoding_addr=ids.builtin_params.builtin_encodings.address_,
                n_selected_builtins=ids.contract_definition.n_builtins,
                selected_builtins_encoding_addr=ids.contract_definition.builtin_list,
                orig_builtins_ptrs_addr=ids.builtin_ptrs.address_,
                selected_builtins_ptrs_addr=ids.returned_builtin_ptrs_subset,
                ),
            )
    %}
    select_builtins(
        n_builtins=n_builtins,
        all_encodings=builtin_params.builtin_encodings,
        all_ptrs=return_builtin_ptrs,
        n_selected_builtins=contract_definition.n_builtins,
        selected_encodings=contract_definition.builtin_list,
        selected_ptrs=returned_builtin_ptrs_subset)

    # Call validate_builtins to validate that the builtin pointers have advanced correctly.
    validate_builtins(
        prev_builtin_ptrs=builtin_ptrs,
        new_builtin_ptrs=return_builtin_ptrs,
        builtin_instance_sizes=builtin_params.builtin_instance_sizes,
        n_builtins=n_builtins)

    let syscall_end = cast([returned_builtin_ptrs_subset - 2], felt*)
    execute_syscalls(
        execute_tx_context=execute_tx_context,
        caller_address=tx.contract_address,
        syscall_size=syscall_end - syscall_ptr,
        syscall_ptr=syscall_ptr)

    local new_state_entry : StateEntry*
    %{ ids.new_state_entry = segments.add() %}
    assert new_state_entry.contract_hash = state_entry.contract_hash
    assert new_state_entry.storage_ptr = cast([returned_builtin_ptrs_subset - 1], DictAccess*)

    validate_builtin(
        prev_builtin_ptr=cast(state_entry.storage_ptr, felt*),
        new_builtin_ptr=cast(new_state_entry.storage_ptr, felt*),
        builtin_instance_size=DictAccess.SIZE)

    dict_update{dict_ptr=global_state_changes}(
        key=tx.contract_address,
        prev_value=cast(state_entry, felt),
        new_value=cast(new_state_entry, felt))

    let builtin_ptrs = return_builtin_ptrs
    return ()
end

func execute_deploy_transaction{global_state_changes : DictAccess*}():
    alloc_locals
    local contract_address
    local state_entry : StateEntry*
    local new_state_entry : StateEntry*
    %{
        ids.contract_address = tx.contract_address

        # Fetch a state_entry in this hint and validate it in the update at the end
        # of this function.
        ids.state_entry = __dict_manager.get_dict(
            ids.global_state_changes)[ids.contract_address]

        ids.new_state_entry = segments.add()

        from starkware.starknet.core.os.contract_hash import compute_contract_hash

        ids.new_state_entry.contract_hash = int.from_bytes(
            compute_contract_hash(tx.contract_definition), 'big')
    %}

    assert state_entry.contract_hash = UNINITIALIZED_CONTRACT_HASH

    assert new_state_entry.storage_ptr = state_entry.storage_ptr

    dict_update{dict_ptr=global_state_changes}(
        key=contract_address,
        prev_value=cast(state_entry, felt),
        new_value=cast(new_state_entry, felt))

    return ()
end
