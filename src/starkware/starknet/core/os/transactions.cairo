from starkware.cairo.builtin_selection.select_builtins import select_builtins
from starkware.cairo.builtin_selection.validate_builtins import validate_builtin, validate_builtins
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin, HashBuiltin, SignatureBuiltin
from starkware.cairo.common.dict import dict_new, dict_read, dict_update, dict_write
from starkware.cairo.common.dict_access import DictAccess
from starkware.cairo.common.find_element import find_element, search_sorted
from starkware.cairo.common.math import assert_nn, assert_not_zero
from starkware.cairo.common.memcpy import memcpy
from starkware.cairo.common.registers import get_ap, get_fp_and_pc
from starkware.cairo.common.segments import relocate_segment
from starkware.starknet.common.syscalls import (
    CALL_CONTRACT_SELECTOR, DELEGATE_CALL_SELECTOR, DELEGATE_L1_HANDLER_SELECTOR,
    EMIT_EVENT_SELECTOR, GET_BLOCK_NUMBER_SELECTOR, GET_BLOCK_TIMESTAMP_SELECTOR,
    GET_CALLER_ADDRESS_SELECTOR, GET_CONTRACT_ADDRESS_SELECTOR, GET_SEQUENCER_ADDRESS_SELECTOR,
    GET_TX_SIGNATURE_SELECTOR, SEND_MESSAGE_TO_L1_SELECTOR, STORAGE_READ_SELECTOR,
    STORAGE_WRITE_SELECTOR, CallContract, CallContractResponse, EmitEvent, GetBlockNumber,
    GetBlockNumberResponse, GetBlockTimestamp, GetBlockTimestampResponse, GetCallerAddress,
    GetCallerAddressResponse, GetContractAddress, GetContractAddressResponse, GetSequencerAddress,
    GetSequencerAddressResponse, GetTxSignature, SendMessageToL1SysCall, StorageRead, StorageWrite)
from starkware.starknet.core.os.contracts import (
    ContractDefinition, ContractDefinitionFact, ContractEntryPoint, load_contract_definition_facts)
from starkware.starknet.core.os.output import (
    BlockInfo, DeploymentInfoHeader, MessageToL1Header, MessageToL2Header, OsCarriedOutputs)
from starkware.starknet.core.os.state import StateEntry

const UNINITIALIZED_CONTRACT_HASH = 0

# The dummy caller address of an externally originated transaction.
const ORIGIN_ADDRESS = 0

# An entry point offset that indicates that nothing needs to be done.
# Used to implement an empty constructor.
const NOP_ENTRY_POINT_OFFSET = -1

const TX_TYPE_EXTERNAL = 0
const TX_TYPE_L1_HANDLER = 1
const TX_TYPE_CONSTRUCTOR = 2

# get_selector_from_name('constructor').
const CONSTRUCTOR_SELECTOR = (
    0x28ffe4ff0f226a9107253e17a904099aa4f63a02a5621de0576e5aa71bc5194)

const DEFAULT_ENTRY_POINT_SELECTOR = 0

# An internal representation of an Invoke transaction to execute.
struct Transaction:
    member tx_type : felt
    member caller_address : felt
    # The address of the contract executing this transaction.
    # This address controls the storage being used, messages sent to L1, calling contracts, etc.
    member contract_address : felt
    # The address that holds the code to execute.
    # It may differ from contract_address in the case of delegate call.
    member code_address : felt
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
    member bitwise : felt
end

# A struct containing the ASCII encoding of each builtin.
struct BuiltinEncodings:
    member pedersen : felt
    member range_check : felt
    member ecdsa : felt
    member bitwise : felt
end

# A struct containing the instance size of each builtin.
struct BuiltinInstanceSizes:
    member pedersen : felt
    member range_check : felt
    member ecdsa : felt
    member bitwise : felt
end

struct BuiltinParams:
    member builtin_encodings : BuiltinEncodings*
    member builtin_instance_sizes : BuiltinInstanceSizes*
end

struct ExecuteTransactionContext:
    member builtin_params : BuiltinParams*
    member n_contract_definition_facts : felt
    member contract_definition_facts : ContractDefinitionFact*
    member sequencer_address : felt
    member block_info : BlockInfo*
end

func get_builtin_params() -> (builtin_params : BuiltinParams*):
    alloc_locals
    let (local __fp__, _) = get_fp_and_pc()

    local builtin_encodings : BuiltinEncodings = BuiltinEncodings(
        pedersen='pedersen',
        range_check='range_check',
        ecdsa='ecdsa',
        bitwise='bitwise')

    local builtin_instance_sizes : BuiltinInstanceSizes = BuiltinInstanceSizes(
        pedersen=HashBuiltin.SIZE,
        range_check=1,
        ecdsa=SignatureBuiltin.SIZE,
        bitwise=BitwiseBuiltin.SIZE)

    local builtin_params : BuiltinParams = BuiltinParams(
        builtin_encodings=&builtin_encodings,
        builtin_instance_sizes=&builtin_instance_sizes)
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
        pedersen_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr, bitwise_ptr,
        outputs : OsCarriedOutputs}(block_info : BlockInfo*) -> (
        reserved_range_checks_end, state_changes : StateChanges):
    alloc_locals
    local n_txs
    %{
        from starkware.python.utils import from_bytes

        ids.n_txs = len(os_input.transactions)

        initial_dict = {
            address: segments.gen_arg(
                (from_bytes(contract.contract_hash), segments.add()))
            for address, contract in os_input.contracts.items()
        }
    %}
    # A dict from contract address to a dict of storage changes.
    let (local global_state_changes : DictAccess*) = dict_new()

    let (n_contract_definition_facts, contract_definition_facts) = load_contract_definition_facts()

    let (local __fp__, _) = get_fp_and_pc()
    tempvar temp_range_check
    %{ ids.temp_range_check = segments.add_temp_segment() %}
    local local_builtin_ptrs : BuiltinPointers = BuiltinPointers(
        pedersen=pedersen_ptr,
        range_check=temp_range_check,
        ecdsa=ecdsa_ptr,
        bitwise=bitwise_ptr)

    let (builtin_params) = get_builtin_params()

    local execute_tx_context : ExecuteTransactionContext = ExecuteTransactionContext(
        builtin_params=builtin_params,
        n_contract_definition_facts=n_contract_definition_facts,
        contract_definition_facts=contract_definition_facts,
        sequencer_address=nondet %{ os_input.sequencer_address %},
        block_info=block_info)

    let builtin_ptrs = &local_builtin_ptrs
    %{
        vm_enter_scope({
            'storage_by_address' : storage_by_address,
            'transactions' : iter(os_input.transactions),
            'syscall_handler' : syscall_handler,
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
    let bitwise_ptr = builtin_ptrs.bitwise
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
    execute_externally_called_invoke_transaction(execute_tx_context=execute_tx_context)

    return execute_transactions_inner(execute_tx_context=execute_tx_context, n_txs=n_txs - 1)

    deploy_transaction:
    # Handle deploy_transaction.
    execute_deploy_transaction(execute_tx_context=execute_tx_context)

    return execute_transactions_inner(execute_tx_context=execute_tx_context, n_txs=n_txs - 1)
end

# Executes an externally called invoke transaction.
#
# The transaction should be passed in the hint variable 'tx'.
# If the transaction is an L1 handler, it is appended to the list of consumed L1->L2 messages.
#
# Arguments:
# execute_tx_context - a read-only context used for transaction execution.
func execute_externally_called_invoke_transaction{
        range_check_ptr, builtin_ptrs : BuiltinPointers*, global_state_changes : DictAccess*,
        outputs : OsCarriedOutputs}(execute_tx_context : ExecuteTransactionContext*):
    alloc_locals
    local tx : Transaction*
    %{
        from starkware.starknet.business_logic.internal_transaction import InternalInvokeFunction
        from starkware.starknet.services.api.contract_definition import EntryPointType

        if tx.entry_point_type is EntryPointType.L1_HANDLER:
            tx_type = ids.TX_TYPE_L1_HANDLER
            assert tx.nonce is not None, "L1 handlers must include a nonce."
        elif tx.entry_point_type is EntryPointType.EXTERNAL:
            tx_type = ids.TX_TYPE_EXTERNAL
        else:
            raise NotImplementedError(f'Unexpected EntryPointType: {tx.entry_point_type}.')

        assert isinstance(tx, InternalInvokeFunction), \
            f'Expected a transaction of type InternalInvokeFunction, got {tx}.'
        ids.tx = segments.gen_arg(
            arg=[
                tx_type,
                ids.ORIGIN_ADDRESS,
                tx.contract_address,
                tx.code_address,
                tx.entry_point_selector,
                len(tx.calldata),
                tx.calldata,
            ]
        )
    %}

    # External calls originate from ORIGIN_ADDRESS.
    assert tx.caller_address = ORIGIN_ADDRESS

    if tx.tx_type == TX_TYPE_L1_HANDLER:
        # Consume L1-to-L2 message.
        consume_l1_to_l2_message(tx=tx, nonce=nondet %{ tx.nonce %})
    else:
        # If tx.tx_type is not TX_TYPE_L1_HANDLER, it must be TX_TYPE_EXTERNAL.
        assert tx.tx_type = TX_TYPE_EXTERNAL
        tempvar outputs = outputs
    end

    # In external calls and l1 handlers, the code_address must match the contract_address.
    assert tx.code_address = tx.contract_address

    execute_invoke_transaction(execute_tx_context=execute_tx_context, tx=tx)
    return ()
end

# Executes a syscall that calls another contract, or invokes a delegate call.
func execute_contract_call{
        range_check_ptr, builtin_ptrs : BuiltinPointers*, global_state_changes : DictAccess*,
        outputs : OsCarriedOutputs}(
        execute_tx_context : ExecuteTransactionContext*, contract_address : felt,
        caller_address : felt, tx_type : felt, syscall_ptr : CallContract*):
    alloc_locals

    let call_req = syscall_ptr.request

    local tx : Transaction*
    %{ ids.tx = segments.add() %}
    assert [tx] = Transaction(
        tx_type=tx_type,
        caller_address=caller_address,
        contract_address=contract_address,
        code_address=call_req.contract_address,
        selector=call_req.function_selector,
        calldata_size=call_req.calldata_size,
        calldata=call_req.calldata)

    let (retdata_size, retdata) = execute_invoke_transaction(
        execute_tx_context=execute_tx_context, tx=tx)

    let call_resp = syscall_ptr.response
    %{
        expected = memory.get_range(addr=ids.call_resp.retdata, size=ids.retdata_size)
        actual = memory.get_range(addr=ids.retdata, size=ids.retdata_size)

        assert expected == actual, f'Return value mismatch expected={expected}, actual={actual}.'
    %}
    relocate_segment(src_ptr=call_resp.retdata, dest_ptr=retdata)

    assert call_resp = CallContractResponse(
        retdata_size=retdata_size,
        retdata=retdata)
    return ()
end

# Reads a value from the current contract's storage.
func execute_storage_read{global_state_changes : DictAccess*}(
        contract_address, syscall_ptr : StorageRead*):
    alloc_locals
    local state_entry : StateEntry*
    local new_state_entry : StateEntry*
    %{
        syscall_handler.execute_syscall_storage_read()

        # Fetch a state_entry in this hint and validate it in the update that comes next.
        ids.state_entry = __dict_manager.get_dict(ids.global_state_changes)[ids.contract_address]

        ids.new_state_entry = segments.add()
    %}

    tempvar value = syscall_ptr.response.value

    # Update the contract's storage.
    tempvar storage_ptr = state_entry.storage_ptr
    assert [storage_ptr] = DictAccess(
        key=syscall_ptr.request.address, prev_value=value, new_value=value)
    let storage_ptr = storage_ptr + DictAccess.SIZE

    # Update global_state_changes.
    assert [new_state_entry] = StateEntry(
        contract_hash=state_entry.contract_hash,
        storage_ptr=storage_ptr)
    dict_update{dict_ptr=global_state_changes}(
        key=contract_address,
        prev_value=cast(state_entry, felt),
        new_value=cast(new_state_entry, felt))

    return ()
end

# Write a value to the current contract's storage.
func execute_storage_write{global_state_changes : DictAccess*}(
        contract_address, syscall_ptr : StorageWrite*):
    alloc_locals
    local prev_value : felt
    local state_entry : StateEntry*
    local new_state_entry : StateEntry*
    %{
        ids.prev_value = syscall_handler.execute_syscall_storage_write()

        # Fetch a state_entry in this hint and validate it in the update that comes next.
        ids.state_entry = __dict_manager.get_dict(ids.global_state_changes)[ids.contract_address]

        ids.new_state_entry = segments.add()
    %}

    # Update the contract's storage.
    tempvar storage_ptr = state_entry.storage_ptr
    assert [storage_ptr] = DictAccess(
        key=syscall_ptr.address, prev_value=prev_value, new_value=syscall_ptr.value)
    let storage_ptr = storage_ptr + DictAccess.SIZE

    # Update global_state_changes.
    assert [new_state_entry] = StateEntry(
        contract_hash=state_entry.contract_hash,
        storage_ptr=storage_ptr)
    dict_update{dict_ptr=global_state_changes}(
        key=contract_address,
        prev_value=cast(state_entry, felt),
        new_value=cast(new_state_entry, felt))

    return ()
end

# Executes a system call.
#
# Arguments:
# execute_tx_context - a read-only context used for transaction execution.
# calling_tx - The transaction for which we are executing the system calls.
# syscall_ptr a pointer to the syscall segment associated with the 'calling_tx'.
func execute_syscalls{
        range_check_ptr, builtin_ptrs : BuiltinPointers*, global_state_changes : DictAccess*,
        outputs : OsCarriedOutputs}(
        execute_tx_context : ExecuteTransactionContext*, calling_tx : Transaction*, syscall_size,
        syscall_ptr : felt*):
    if syscall_size == 0:
        return ()
    end

    if [syscall_ptr] == CALL_CONTRACT_SELECTOR:
        let call_contract_syscall = cast(syscall_ptr, CallContract*)
        execute_contract_call(
            execute_tx_context=execute_tx_context,
            contract_address=call_contract_syscall.request.contract_address,
            caller_address=calling_tx.contract_address,
            tx_type=TX_TYPE_EXTERNAL,
            syscall_ptr=call_contract_syscall)
        return execute_syscalls(
            execute_tx_context=execute_tx_context,
            calling_tx=calling_tx,
            syscall_size=syscall_size - CallContract.SIZE,
            syscall_ptr=syscall_ptr + CallContract.SIZE)
    end

    if [syscall_ptr] == DELEGATE_CALL_SELECTOR:
        execute_contract_call(
            execute_tx_context=execute_tx_context,
            contract_address=calling_tx.contract_address,
            caller_address=calling_tx.caller_address,
            tx_type=TX_TYPE_EXTERNAL,
            syscall_ptr=cast(syscall_ptr, CallContract*))
        return execute_syscalls(
            execute_tx_context=execute_tx_context,
            calling_tx=calling_tx,
            syscall_size=syscall_size - CallContract.SIZE,
            syscall_ptr=syscall_ptr + CallContract.SIZE)
    end

    if [syscall_ptr] == DELEGATE_L1_HANDLER_SELECTOR:
        execute_contract_call(
            execute_tx_context=execute_tx_context,
            contract_address=calling_tx.contract_address,
            caller_address=calling_tx.caller_address,
            tx_type=TX_TYPE_L1_HANDLER,
            syscall_ptr=cast(syscall_ptr, CallContract*))
        return execute_syscalls(
            execute_tx_context=execute_tx_context,
            calling_tx=calling_tx,
            syscall_size=syscall_size - CallContract.SIZE,
            syscall_ptr=syscall_ptr + CallContract.SIZE)
    end

    if [syscall_ptr] == GET_CALLER_ADDRESS_SELECTOR:
        assert [cast(syscall_ptr, GetCallerAddress*)].response = GetCallerAddressResponse(
            caller_address=calling_tx.caller_address)
        return execute_syscalls(
            execute_tx_context=execute_tx_context,
            calling_tx=calling_tx,
            syscall_size=syscall_size - GetCallerAddress.SIZE,
            syscall_ptr=syscall_ptr + GetCallerAddress.SIZE)
    end

    if [syscall_ptr] == GET_SEQUENCER_ADDRESS_SELECTOR:
        assert [cast(syscall_ptr, GetSequencerAddress*)].response = GetSequencerAddressResponse(
            sequencer_address=execute_tx_context.sequencer_address)
        return execute_syscalls(
            execute_tx_context=execute_tx_context,
            calling_tx=calling_tx,
            syscall_size=syscall_size - GetSequencerAddress.SIZE,
            syscall_ptr=syscall_ptr + GetSequencerAddress.SIZE)
    end

    if [syscall_ptr] == GET_CONTRACT_ADDRESS_SELECTOR:
        assert [cast(syscall_ptr, GetContractAddress*)].response = GetContractAddressResponse(
            contract_address=calling_tx.contract_address)
        return execute_syscalls(
            execute_tx_context=execute_tx_context,
            calling_tx=calling_tx,
            syscall_size=syscall_size - GetContractAddress.SIZE,
            syscall_ptr=syscall_ptr + GetContractAddress.SIZE)
    end

    if [syscall_ptr] == GET_BLOCK_TIMESTAMP_SELECTOR:
        assert [cast(syscall_ptr, GetBlockTimestamp*)].response = GetBlockTimestampResponse(
            block_timestamp=execute_tx_context.block_info.block_timestamp)
        return execute_syscalls(
            execute_tx_context=execute_tx_context,
            calling_tx=calling_tx,
            syscall_size=syscall_size - GetBlockTimestamp.SIZE,
            syscall_ptr=syscall_ptr + GetBlockTimestamp.SIZE)
    end

    if [syscall_ptr] == GET_BLOCK_NUMBER_SELECTOR:
        assert [cast(syscall_ptr, GetBlockNumber*)].response = GetBlockNumberResponse(
            block_number=execute_tx_context.block_info.block_number)
        return execute_syscalls(
            execute_tx_context=execute_tx_context,
            calling_tx=calling_tx,
            syscall_size=syscall_size - GetBlockNumber.SIZE,
            syscall_ptr=syscall_ptr + GetBlockNumber.SIZE)
    end

    if [syscall_ptr] == GET_TX_SIGNATURE_SELECTOR:
        # Note that we don't enforce anything on the response.
        return execute_syscalls(
            execute_tx_context=execute_tx_context,
            calling_tx=calling_tx,
            syscall_size=syscall_size - GetTxSignature.SIZE,
            syscall_ptr=syscall_ptr + GetTxSignature.SIZE)
    end

    if [syscall_ptr] == STORAGE_READ_SELECTOR:
        execute_storage_read(
            contract_address=calling_tx.contract_address,
            syscall_ptr=cast(syscall_ptr, StorageRead*))
        return execute_syscalls(
            execute_tx_context=execute_tx_context,
            calling_tx=calling_tx,
            syscall_size=syscall_size - StorageRead.SIZE,
            syscall_ptr=syscall_ptr + StorageRead.SIZE)
    end

    if [syscall_ptr] == STORAGE_WRITE_SELECTOR:
        execute_storage_write(
            contract_address=calling_tx.contract_address,
            syscall_ptr=cast(syscall_ptr, StorageWrite*))
        return execute_syscalls(
            execute_tx_context=execute_tx_context,
            calling_tx=calling_tx,
            syscall_size=syscall_size - StorageWrite.SIZE,
            syscall_ptr=syscall_ptr + StorageWrite.SIZE)
    end

    if [syscall_ptr] == EMIT_EVENT_SELECTOR:
        # Skip as long as the block hash is not calculated by the OS.
        return execute_syscalls(
            execute_tx_context=execute_tx_context,
            calling_tx=calling_tx,
            syscall_size=syscall_size - EmitEvent.SIZE,
            syscall_ptr=syscall_ptr + EmitEvent.SIZE)
    end

    # Here the system call must be 'SendMessageToL1'.
    assert [syscall_ptr] = SEND_MESSAGE_TO_L1_SELECTOR

    let syscall = [cast(syscall_ptr, SendMessageToL1SysCall*)]

    assert [outputs.messages_to_l1] = MessageToL1Header(
        from_address=calling_tx.contract_address,
        to_address=syscall.to_address,
        payload_size=syscall.payload_size)
    memcpy(
        dst=outputs.messages_to_l1 + MessageToL1Header.SIZE,
        src=syscall.payload_ptr,
        len=syscall.payload_size)
    let outputs = OsCarriedOutputs(
        messages_to_l1=outputs.messages_to_l1 + MessageToL1Header.SIZE +
        outputs.messages_to_l1.payload_size,
        messages_to_l2=outputs.messages_to_l2,
        deployment_info=outputs.deployment_info)
    return execute_syscalls(
        execute_tx_context=execute_tx_context,
        calling_tx=calling_tx,
        syscall_size=syscall_size - SendMessageToL1SysCall.SIZE,
        syscall_ptr=syscall_ptr + SendMessageToL1SysCall.SIZE)
end

# Adds 'tx' with the given 'nonce' to 'outputs.messages_to_l2'.
func consume_l1_to_l2_message{outputs : OsCarriedOutputs}(tx : Transaction*, nonce : felt):
    assert_not_zero(tx.calldata_size)
    # The raw payload is the calldata without the from_address argument (which is the first).
    tempvar raw_payload : felt* = tx.calldata + 1
    tempvar raw_payload_size = tx.calldata_size - 1

    # Write the given transaction to the output.
    assert [outputs.messages_to_l2] = MessageToL2Header(
        from_address=[tx.calldata],
        to_address=tx.contract_address,
        nonce=nonce,
        selector=tx.selector,
        payload_size=raw_payload_size)

    # The payload consists of the selector and the raw payload.
    let message_payload = cast(outputs.messages_to_l2 + MessageToL2Header.SIZE, felt*)
    memcpy(dst=message_payload, src=raw_payload, len=raw_payload_size)

    let outputs = OsCarriedOutputs(
        messages_to_l1=outputs.messages_to_l1,
        messages_to_l2=outputs.messages_to_l2 + MessageToL2Header.SIZE +
        outputs.messages_to_l2.payload_size,
        deployment_info=outputs.deployment_info)
    return ()
end

# Returns the entry point's offset in the program based on the contract_definition and the
# transaction.
func get_entry_point_offset{range_check_ptr}(
        contract_definition : ContractDefinition*, tx : Transaction*) -> (
        entry_point_offset : felt):
    alloc_locals
    # Get the entry points corresponding to the transaction's type.
    local entry_points : ContractEntryPoint*
    local n_entry_points : felt

    if tx.tx_type == TX_TYPE_L1_HANDLER:
        entry_points = contract_definition.l1_handlers
        n_entry_points = contract_definition.n_l1_handlers
    else:
        if tx.tx_type == TX_TYPE_EXTERNAL:
            entry_points = contract_definition.external_functions
            n_entry_points = contract_definition.n_external_functions
        else:
            assert tx.tx_type = TX_TYPE_CONSTRUCTOR
            entry_points = contract_definition.constructors
            n_entry_points = contract_definition.n_constructors

            if n_entry_points == 0:
                return (entry_point_offset=NOP_ENTRY_POINT_OFFSET)
            end
        end
    end

    # The key must be at offset 0.
    static_assert ContractEntryPoint.selector == 0
    let (entry_point_desc : ContractEntryPoint*, success) = search_sorted(
        array_ptr=cast(entry_points, felt*),
        elm_size=ContractEntryPoint.SIZE,
        n_elms=n_entry_points,
        key=tx.selector)
    if success != 0:
        return (entry_point_offset=entry_point_desc.offset)
    end

    # If the selector was not found, verify that the first entry point is the default entry point,
    # and call it.
    assert entry_points[0].selector = DEFAULT_ENTRY_POINT_SELECTOR
    return (entry_point_offset=entry_points[0].offset)
end

# Executes an invoke transaction and returns its return value.
#
# Arguments:
# execute_tx_context - a read-only context used for transaction execution.
# tx - The transaction to execute.
func execute_invoke_transaction{
        range_check_ptr, builtin_ptrs : BuiltinPointers*, global_state_changes : DictAccess*,
        outputs : OsCarriedOutputs}(
        execute_tx_context : ExecuteTransactionContext*, tx : Transaction*) -> (
        retdata_size, retdata : felt*):
    alloc_locals

    let (local state_entry : StateEntry*) = dict_read{dict_ptr=global_state_changes}(
        key=tx.code_address)
    local global_state_changes : DictAccess* = global_state_changes

    # The key must be at offset 0.
    static_assert ContractDefinitionFact.hash == 0
    let (contract_definition_fact : ContractDefinitionFact*) = find_element(
        array_ptr=execute_tx_context.contract_definition_facts,
        elm_size=ContractDefinitionFact.SIZE,
        n_elms=execute_tx_context.n_contract_definition_facts,
        key=state_entry.contract_hash)
    local contract_definition : ContractDefinition* = contract_definition_fact.contract_definition

    let (entry_point_offset) = get_entry_point_offset(
        contract_definition=contract_definition, tx=tx)

    %{ syscall_handler.enter_call() %}
    if entry_point_offset == NOP_ENTRY_POINT_OFFSET:
        # Assert that there is no call data in the case of NOP entry point.
        assert tx.calldata_size = 0
        %{ syscall_handler.exit_call() %}
        return (retdata_size=0, retdata=cast(0, felt*))
    end

    local range_check_ptr = range_check_ptr
    local contract_entry_point : felt* = contract_definition.bytecode_ptr + entry_point_offset

    local os_context : felt*
    local syscall_ptr : felt*

    %{
        ids.os_context = segments.add()
        ids.syscall_ptr = segments.add()
    %}
    assert [os_context] = cast(syscall_ptr, felt)

    let n_builtins = BuiltinEncodings.SIZE
    local builtin_params : BuiltinParams* = execute_tx_context.builtin_params
    select_builtins(
        n_builtins=n_builtins,
        all_encodings=builtin_params.builtin_encodings,
        all_ptrs=builtin_ptrs,
        n_selected_builtins=contract_definition.n_builtins,
        selected_encodings=contract_definition.builtin_list,
        selected_ptrs=os_context + 1)

    # Use tempvar to pass arguments to contract_entry_point().
    tempvar selector = tx.selector
    tempvar context = os_context
    tempvar calldata_size = tx.calldata_size
    tempvar calldata = tx.calldata
    %{
        vm_enter_scope({
            '__storage' : storage_by_address[ids.tx.contract_address],
            'syscall_handler' : syscall_handler,
        })
    %}
    call abs contract_entry_point
    %{ vm_exit_scope() %}
    # Retrieve returned_builtin_ptrs_subset.
    # Note that returned_builtin_ptrs_subset cannot be set in a hint because doing so will allow a
    # malicious prover to lie about the storage changes of a valid contract.
    let (ap_val) = get_ap()
    local returned_builtin_ptrs_subset : felt* = cast(
        ap_val - contract_definition.n_builtins - 2, felt*)
    local retdata_size : felt = [ap_val - 2]
    local retdata : felt* = cast([ap_val - 1], felt*)

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

    let syscall_end = cast([returned_builtin_ptrs_subset - 1], felt*)

    let builtin_ptrs = return_builtin_ptrs
    execute_syscalls(
        execute_tx_context=execute_tx_context,
        calling_tx=tx,
        syscall_size=syscall_end - syscall_ptr,
        syscall_ptr=syscall_ptr)

    %{ syscall_handler.exit_call() %}
    return (retdata_size=retdata_size, retdata=retdata)
end

func execute_deploy_transaction{
        range_check_ptr, builtin_ptrs : BuiltinPointers*, global_state_changes : DictAccess*,
        outputs : OsCarriedOutputs}(execute_tx_context : ExecuteTransactionContext*):
    alloc_locals
    local contract_address
    local state_entry : StateEntry*
    local new_state_entry : StateEntry*

    %{
        ids.contract_address = tx.contract_address

        # Fetch a state_entry in this hint and validate it in the update at the end
        # of this function.
        ids.state_entry = __dict_manager.get_dict(
            ids.global_state_changes)[tx.contract_address]

        ids.new_state_entry = segments.add()

        from starkware.starknet.core.os.contract_hash import compute_contract_hash

        ids.new_state_entry.contract_hash = compute_contract_hash(tx.contract_definition)
    %}

    # Assert that we don't deploy to ORIGIN_ADDRESS.
    assert_not_zero(contract_address - ORIGIN_ADDRESS)

    assert state_entry.contract_hash = UNINITIALIZED_CONTRACT_HASH
    assert new_state_entry.storage_ptr = state_entry.storage_ptr

    dict_update{dict_ptr=global_state_changes}(
        key=contract_address,
        prev_value=cast(state_entry, felt),
        new_value=cast(new_state_entry, felt))

    local calldata_size
    local calldata : felt* = outputs.deployment_info + DeploymentInfoHeader.SIZE
    %{
        ids.calldata_size = len(tx.constructor_calldata)
        segments.write_arg(ptr=ids.calldata, arg=tx.constructor_calldata)
    %}
    assert_nn(calldata_size)

    # Write the contract address and hash to the output.
    assert [outputs.deployment_info] = DeploymentInfoHeader(
        contract_address=contract_address, contract_hash=new_state_entry.contract_hash,
        calldata_size=calldata_size)
    let outputs = OsCarriedOutputs(
        messages_to_l1=outputs.messages_to_l1,
        messages_to_l2=outputs.messages_to_l2,
        deployment_info=cast(calldata + calldata_size, DeploymentInfoHeader*))

    local tx : Transaction*
    %{ ids.tx = segments.add() %}
    assert [tx] = Transaction(
        tx_type=TX_TYPE_CONSTRUCTOR,
        caller_address=ORIGIN_ADDRESS,
        contract_address=contract_address,
        code_address=contract_address,
        selector=CONSTRUCTOR_SELECTOR,
        calldata_size=calldata_size,
        calldata=calldata)

    execute_invoke_transaction(execute_tx_context=execute_tx_context, tx=tx)

    return ()
end
