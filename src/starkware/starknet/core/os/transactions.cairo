from starkware.cairo.builtin_selection.select_builtins import select_builtins
from starkware.cairo.builtin_selection.validate_builtins import validate_builtin, validate_builtins
from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.dict import dict_new, dict_read, dict_update, dict_write
from starkware.cairo.common.dict_access import DictAccess
from starkware.cairo.common.find_element import find_element, search_sorted
from starkware.cairo.common.math import assert_nn, assert_nn_le, assert_not_zero
from starkware.cairo.common.memcpy import memcpy
from starkware.cairo.common.registers import get_ap, get_fp_and_pc
from starkware.cairo.common.segments import relocate_segment
from starkware.cairo.common.uint256 import Uint256
from starkware.starknet.common.constants import (
    DECLARE_HASH_PREFIX,
    DEPLOY_ACCOUNT_HASH_PREFIX,
    DEPLOY_HASH_PREFIX,
    INVOKE_HASH_PREFIX,
    L1_HANDLER_HASH_PREFIX,
    ORIGIN_ADDRESS,
)
from starkware.starknet.common.syscalls import (
    CALL_CONTRACT_SELECTOR,
    DELEGATE_CALL_SELECTOR,
    DELEGATE_L1_HANDLER_SELECTOR,
    DEPLOY_SELECTOR,
    EMIT_EVENT_SELECTOR,
    GET_BLOCK_NUMBER_SELECTOR,
    GET_BLOCK_TIMESTAMP_SELECTOR,
    GET_CALLER_ADDRESS_SELECTOR,
    GET_CONTRACT_ADDRESS_SELECTOR,
    GET_SEQUENCER_ADDRESS_SELECTOR,
    GET_TX_INFO_SELECTOR,
    GET_TX_SIGNATURE_SELECTOR,
    LIBRARY_CALL_L1_HANDLER_SELECTOR,
    LIBRARY_CALL_SELECTOR,
    SEND_MESSAGE_TO_L1_SELECTOR,
    STORAGE_READ_SELECTOR,
    STORAGE_WRITE_SELECTOR,
    CallContract,
    CallContractResponse,
    Deploy,
    DeployResponse,
    EmitEvent,
    GetBlockNumber,
    GetBlockNumberResponse,
    GetBlockTimestamp,
    GetBlockTimestampResponse,
    GetCallerAddress,
    GetCallerAddressResponse,
    GetContractAddress,
    GetContractAddressResponse,
    GetSequencerAddress,
    GetSequencerAddressResponse,
    GetTxInfo,
    GetTxInfoResponse,
    GetTxSignature,
    GetTxSignatureResponse,
    LibraryCall,
    SendMessageToL1SysCall,
    StorageRead,
    StorageWrite,
    TxInfo,
)
from starkware.starknet.core.os.block_context import BlockContext
from starkware.starknet.core.os.builtins import BuiltinEncodings, BuiltinParams, BuiltinPointers
from starkware.starknet.core.os.contract_address.contract_address import get_contract_address
from starkware.starknet.core.os.contracts import (
    ContractClass,
    ContractClassFact,
    ContractEntryPoint,
)
from starkware.starknet.core.os.output import (
    BlockInfo,
    DeploymentInfo,
    MessageToL1Header,
    MessageToL2Header,
    OsCarriedOutputs,
    os_carried_outputs_new,
)
from starkware.starknet.core.os.state import UNINITIALIZED_CLASS_HASH, StateEntry
from starkware.starknet.core.os.transaction_hash.transaction_hash import get_transaction_hash

// An entry point offset that indicates that nothing needs to be done.
// Used to implement an empty constructor.
const NOP_ENTRY_POINT_OFFSET = -1;

const ENTRY_POINT_TYPE_EXTERNAL = 0;
const ENTRY_POINT_TYPE_L1_HANDLER = 1;
const ENTRY_POINT_TYPE_CONSTRUCTOR = 2;

const TRANSACTION_VERSION = 1;
const L1_HANDLER_VERSION = 0;

// get_selector_from_name('constructor').
const CONSTRUCTOR_ENTRY_POINT_SELECTOR = (
    0x28ffe4ff0f226a9107253e17a904099aa4f63a02a5621de0576e5aa71bc5194);

// get_selector_from_name('__execute__').
const EXECUTE_ENTRY_POINT_SELECTOR = (
    0x15d40a3d6ca2ac30f4031e42be28da9b056fef9bb7357ac5e85627ee876e5ad);

// get_selector_from_name('__validate__').
const VALIDATE_ENTRY_POINT_SELECTOR = (
    0x162da33a4585851fe8d3af3c2a9c60b557814e221e0d4f30ff0b2189d9c7775);

// get_selector_from_name('__validate_declare__').
const VALIDATE_DECLARE_ENTRY_POINT_SELECTOR = (
    0x289da278a8dc833409cabfdad1581e8e7d40e42dcaed693fa4008dcdb4963b3);

// get_selector_from_name('__validate_deploy__').
const VALIDATE_DEPLOY_ENTRY_POINT_SELECTOR = (
    0x36fcbf06cd96843058359e1a75928beacfac10727dab22a3972f0af8aa92895);

// get_selector_from_name('transfer').
const TRANSFER_ENTRY_POINT_SELECTOR = (
    0x83afd3f4caedc6eebf44246fe54e38c95e3179a5ec9ea81740eca5b482d12e);

const DEFAULT_ENTRY_POINT_SELECTOR = 0;

// Represents the execution context during the execution of contract code.
struct ExecutionContext {
    entry_point_type: felt,
    caller_address: felt,
    // The execution is done in the context of the contract at 'contract_address'.
    // This address controls the storage being used, messages sent to L1, calling contracts, etc.
    contract_address: felt,
    // The hash of the contract class to execute.
    class_hash: felt,
    selector: felt,
    calldata_size: felt,
    calldata: felt*,
    // Information about the transaction that triggered the execution.
    original_tx_info: TxInfo*,
}

// A dictionary from address to StateEntry.
struct StateChanges {
    changes_start: DictAccess*,
    changes_end: DictAccess*,
}

// Executes the transactions in the hint variable os_input.transactions.
//
// Returns:
// reserved_range_checks_end - end pointer for the reserved range checks.
// state_changes - StateChanges struct corresponding to the changes that were done by
//   the transactions.
//
// Assumptions:
//   The caller verifies that the memory range [range_check_ptr, reserved_range_checks_end)
//   corresponds to valid range check instances.
//   Note that if the assumption above does not hold it might be the case that
//   the returned range_check_ptr is smaller then reserved_range_checks_end.
func execute_transactions{
    pedersen_ptr: HashBuiltin*,
    range_check_ptr,
    ecdsa_ptr,
    bitwise_ptr,
    ec_op_ptr,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*) -> (reserved_range_checks_end: felt, state_changes: StateChanges) {
    alloc_locals;
    local n_txs;
    %{
        from starkware.python.utils import from_bytes

        ids.n_txs = len(os_input.transactions)

        initial_dict = {
            address: segments.gen_arg(
                (from_bytes(contract.contract_hash), segments.add(), contract.nonce))
            for address, contract in os_input.contracts.items()
        }
    %}
    // A dict from contract address to a dict of storage changes.
    let (local global_state_changes: DictAccess*) = dict_new();

    let (__fp__, _) = get_fp_and_pc();
    local local_builtin_ptrs: BuiltinPointers = BuiltinPointers(
        pedersen=pedersen_ptr,
        range_check=nondet %{ segments.add_temp_segment() %},
        ecdsa=ecdsa_ptr,
        bitwise=bitwise_ptr,
        ec_op=ec_op_ptr);

    let builtin_ptrs = &local_builtin_ptrs;
    %{
        vm_enter_scope({
            'transactions': iter(os_input.transactions),
            'syscall_handler': syscall_handler,
             '__dict_manager': __dict_manager,
        })
    %}
    // Keep a reference to the start of global_state_changes.
    let global_state_changes_start = global_state_changes;
    execute_transactions_inner{
        builtin_ptrs=builtin_ptrs, global_state_changes=global_state_changes
    }(block_context=block_context, n_txs=n_txs);
    %{ vm_exit_scope() %}

    let reserved_range_checks_end = range_check_ptr;
    // Relocate the range checks used by the transactions to reserved_range_checks_end.
    relocate_segment(
        src_ptr=cast(local_builtin_ptrs.range_check, felt*),
        dest_ptr=cast(reserved_range_checks_end, felt*),
    );

    let pedersen_ptr = builtin_ptrs.pedersen;
    let range_check_ptr = builtin_ptrs.range_check;
    let ecdsa_ptr = builtin_ptrs.ecdsa;
    let bitwise_ptr = builtin_ptrs.bitwise;
    let ec_op_ptr = builtin_ptrs.ec_op;
    return (
        reserved_range_checks_end=reserved_range_checks_end,
        state_changes=StateChanges(global_state_changes_start, global_state_changes),
    );
}

// Inner function for execute_transactions.
// Arguments:
// block_context - a read-only context used for transaction execution.
// n_txs - the number of transactions to execute.
//
// Implicit arguments:
// range_check_ptr - a range check builtin, used and advanced by the OS, not the transactions.
// builtin_ptrs - a struct of builtin pointer that are going to be used by the
// executed transactions.
// The range-checks used internally by the transactions do not affect range_check_ptr.
// They are accounted for in builtin_ptrs.
func execute_transactions_inner{
    range_check_ptr,
    builtin_ptrs: BuiltinPointers*,
    global_state_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*, n_txs) {
    if (n_txs == 0) {
        return ();
    }

    alloc_locals;
    local tx_type;
    // Guess the current transaction's type.
    %{
        tx = next(transactions)
        tx_type_bytes = tx.tx_type.name.encode("ascii")
        ids.tx_type = int.from_bytes(tx_type_bytes, "big")
    %}

    if (tx_type == 'INVOKE_FUNCTION') {
        // Handle the invoke-function transaction.
        execute_invoke_function_transaction(block_context=block_context);
        return execute_transactions_inner(block_context=block_context, n_txs=n_txs - 1);
    }

    if (tx_type == 'L1_HANDLER') {
        // Handle the L1-handler transaction.
        execute_l1_handler_transaction(block_context=block_context);
        return execute_transactions_inner(block_context=block_context, n_txs=n_txs - 1);
    }

    if (tx_type == 'DEPLOY') {
        // Handle the deploy transaction.
        execute_deploy_transaction(block_context=block_context);
        return execute_transactions_inner(block_context=block_context, n_txs=n_txs - 1);
    }

    if (tx_type == 'DEPLOY_ACCOUNT') {
        // Handle the deploy-account transaction.
        execute_deploy_account_transaction(block_context=block_context);
        return execute_transactions_inner(block_context=block_context, n_txs=n_txs - 1);
    }

    assert tx_type = 'DECLARE';
    // Handle the declare transaction.
    execute_declare_transaction(block_context=block_context);
    return execute_transactions_inner(block_context=block_context, n_txs=n_txs - 1);
}

// Represents the calldata of an ERC20 transfer.
struct TransferCallData {
    recipient: felt,
    amount: Uint256,
}

// Charges a fee from the user.
// If max_fee is not 0, validates that the selector matches the entry point of an account contract
// and executes an ERC20 transfer on the behalf of that account contract.
//
// Arguments:
// block_context - a global context that is fixed throughout the block.
// tx_execution_context - The execution context of the transaction that pays the fee.
func charge_fee{
    range_check_ptr,
    builtin_ptrs: BuiltinPointers*,
    global_state_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*, tx_execution_context: ExecutionContext*) {
    alloc_locals;
    local original_tx_info: TxInfo* = tx_execution_context.original_tx_info;
    local max_fee = original_tx_info.max_fee;
    if (max_fee == 0) {
        return ();
    }

    // Transactions with fee should go through an account contract.
    tempvar selector = tx_execution_context.selector;
    assert (selector - EXECUTE_ENTRY_POINT_SELECTOR) *
        (selector - VALIDATE_DECLARE_ENTRY_POINT_SELECTOR) *
        (selector - VALIDATE_DEPLOY_ENTRY_POINT_SELECTOR) = 0;

    local calldata: TransferCallData = TransferCallData(
        recipient=block_context.sequencer_address,
        amount=Uint256(low=nondet %{ syscall_handler.tx_execution_info.actual_fee %}, high=0));

    // Verify that the charged amount is not larger than the transaction's max_fee field.
    assert_nn_le(calldata.amount.low, max_fee);

    tempvar fee_token_address = block_context.starknet_os_config.fee_token_address;
    let (fee_state_entry: StateEntry*) = dict_read{dict_ptr=global_state_changes}(
        key=fee_token_address
    );
    let (__fp__, _) = get_fp_and_pc();
    local execution_context: ExecutionContext = ExecutionContext(
        entry_point_type=ENTRY_POINT_TYPE_EXTERNAL,
        caller_address=original_tx_info.account_contract_address,
        contract_address=fee_token_address,
        class_hash=fee_state_entry.class_hash,
        selector=TRANSFER_ENTRY_POINT_SELECTOR,
        calldata_size=TransferCallData.SIZE,
        calldata=&calldata,
        original_tx_info=original_tx_info,
        );

    execute_entry_point(block_context=block_context, execution_context=&execution_context);

    return ();
}

// Checks that the given transaction version is one of the supported versions.
func validate_transaction_version(tx_version: felt) {
    with_attr error_message("Invalid transaction version: {tx_version}.") {
        static_assert TRANSACTION_VERSION == 1;
        assert (tx_version - 0) * (tx_version - TRANSACTION_VERSION) = 0;
    }
    return ();
}

// Executes an invoke-function transaction.
//
// The transaction should be passed in the hint variable 'tx'.
//
// Arguments:
// block_context - a global context that is fixed throughout the block.
func execute_invoke_function_transaction{
    range_check_ptr,
    builtin_ptrs: BuiltinPointers*,
    global_state_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*) {
    alloc_locals;

    let (local tx_execution_context: ExecutionContext*) = get_invoke_tx_execution_context(
        entry_point_type=ENTRY_POINT_TYPE_EXTERNAL
    );

    // Guess tx version and make sure it's valid.
    local tx_version = nondet %{ tx.version %};
    validate_transaction_version(tx_version=tx_version);

    local nonce = nondet %{ 0 if tx.nonce is None else tx.nonce %};
    local max_fee = nondet %{ tx.max_fee %};
    let (__fp__, _) = get_fp_and_pc();

    if (tx_version == 0) {
        tempvar entry_point_selector_field = tx_execution_context.selector;
        tempvar additional_data_size = 0;
        tempvar additional_data = cast(0, felt*);
    } else {
        assert tx_execution_context.selector = EXECUTE_ENTRY_POINT_SELECTOR;
        tempvar entry_point_selector_field = 0;
        tempvar additional_data_size = 1;
        tempvar additional_data = &nonce;
    }

    local chain_id = block_context.starknet_os_config.chain_id;
    let (transaction_hash) = compute_transaction_hash(
        tx_hash_prefix=INVOKE_HASH_PREFIX,
        version=tx_version,
        execution_context=tx_execution_context,
        entry_point_selector_field=entry_point_selector_field,
        max_fee=max_fee,
        chain_id=chain_id,
        additional_data_size=additional_data_size,
        additional_data=additional_data,
    );

    assert [tx_execution_context.original_tx_info] = TxInfo(
        version=tx_version,
        account_contract_address=tx_execution_context.contract_address,
        max_fee=max_fee,
        signature_len=nondet %{ len(tx.signature) %},
        signature=cast(nondet %{ segments.gen_arg(arg=tx.signature) %}, felt*),
        transaction_hash=transaction_hash,
        chain_id=chain_id,
        nonce=nonce,
        );

    check_and_increment_nonce(execution_context=tx_execution_context, nonce=nonce);

    %{ syscall_handler.start_tx(tx_info_ptr=ids.tx_execution_context.original_tx_info.address_) %}

    run_validate(block_context=block_context, tx_execution_context=tx_execution_context);
    execute_entry_point(block_context=block_context, execution_context=tx_execution_context);
    charge_fee(block_context=block_context, tx_execution_context=tx_execution_context);

    %{ syscall_handler.end_tx() %}

    return ();
}

// Executes an L1-handler transaction.
//
// The transaction should be passed in the hint variable 'tx'.
//
// Arguments:
// block_context - a global context that is fixed throughout the block.
func execute_l1_handler_transaction{
    range_check_ptr,
    builtin_ptrs: BuiltinPointers*,
    global_state_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*) {
    alloc_locals;

    let (local tx_execution_context: ExecutionContext*) = get_invoke_tx_execution_context(
        entry_point_type=ENTRY_POINT_TYPE_L1_HANDLER
    );

    local nonce = nondet %{ tx.nonce %};
    local chain_id = block_context.starknet_os_config.chain_id;

    let (__fp__, _) = get_fp_and_pc();
    let (transaction_hash) = compute_transaction_hash(
        tx_hash_prefix=L1_HANDLER_HASH_PREFIX,
        version=L1_HANDLER_VERSION,
        execution_context=tx_execution_context,
        entry_point_selector_field=tx_execution_context.selector,
        max_fee=0,
        chain_id=chain_id,
        additional_data_size=1,
        additional_data=&nonce,
    );

    assert [tx_execution_context.original_tx_info] = TxInfo(
        version=L1_HANDLER_VERSION,
        account_contract_address=tx_execution_context.contract_address,
        max_fee=0,
        signature_len=0,
        signature=cast(0, felt*),
        transaction_hash=transaction_hash,
        chain_id=chain_id,
        nonce=nonce,
        );

    // Consume L1-to-L2 message.
    consume_l1_to_l2_message(execution_context=tx_execution_context, nonce=nonce);

    %{ syscall_handler.start_tx(tx_info_ptr=ids.tx_execution_context.original_tx_info.address_) %}
    execute_entry_point(block_context=block_context, execution_context=tx_execution_context);
    %{ syscall_handler.end_tx() %}

    return ();
}

// Guess the execution context of an invoke transaction (either invoke function or L1 handler).
// Leaves 'original_tx_info' empty - should be filled later on.
func get_invoke_tx_execution_context{global_state_changes: DictAccess*}(entry_point_type: felt) -> (
    tx_execution_context: ExecutionContext*
) {
    alloc_locals;

    local contract_address = nondet %{ tx.contract_address %};
    let (state_entry: StateEntry*) = dict_read{dict_ptr=global_state_changes}(key=contract_address);
    local tx_execution_context: ExecutionContext* = new ExecutionContext(
        entry_point_type=entry_point_type,
        caller_address=ORIGIN_ADDRESS,
        contract_address=contract_address,
        class_hash=state_entry.class_hash,
        selector=nondet %{ tx.entry_point_selector %},
        calldata_size=nondet %{ len(tx.calldata) %},
        calldata=cast(nondet %{ segments.gen_arg(tx.calldata) %}, felt*),
        original_tx_info=cast(nondet %{ segments.add() %}, TxInfo*),
        );

    return (tx_execution_context=tx_execution_context);
}

// Verifies that the transaction's nonce matches the contract's nonce and increments the
// latter.
func check_and_increment_nonce{global_state_changes: DictAccess*}(
    execution_context: ExecutionContext*, nonce: felt
) -> () {
    alloc_locals;

    // Do not handle nonce for version 0.
    local tx_version = execution_context.original_tx_info.version;
    if (tx_version == 0) {
        return ();
    }

    tempvar contract_address = execution_context.contract_address;
    local state_entry: StateEntry*;
    %{
        # Fetch a state_entry in this hint and validate it in the update that comes next.
        ids.state_entry = __dict_manager.get_dict(ids.global_state_changes)[ids.contract_address]
    %}

    local current_nonce = state_entry.nonce;
    with_attr error_message("Unexpected nonce. Expected {current_nonce}, got {nonce}.") {
        assert current_nonce = nonce;
    }

    // Update global_state_changes.
    tempvar new_state_entry = new StateEntry(
        class_hash=state_entry.class_hash,
        storage_ptr=state_entry.storage_ptr,
        nonce=current_nonce + 1);
    dict_update{dict_ptr=global_state_changes}(
        key=contract_address,
        prev_value=cast(state_entry, felt),
        new_value=cast(new_state_entry, felt),
    );
    return ();
}

// Runs the account contract's "__validate__" entry point, which is responsible for
// signature verification.
//
// Arguments:
// block_context - a global context that is fixed throughout the block.
// tx_execution_context - The execution context of the underlying invoke transaction.
func run_validate{
    range_check_ptr,
    builtin_ptrs: BuiltinPointers*,
    global_state_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*, tx_execution_context: ExecutionContext*) {
    alloc_locals;

    // Do not run "__validate__" for version 0.
    if (tx_execution_context.original_tx_info.version == 0) {
        return ();
    }

    // "__validate__" is expected to get the same calldata as "__execute__".
    local validate_execution_context: ExecutionContext* = new ExecutionContext(
        entry_point_type=ENTRY_POINT_TYPE_EXTERNAL,
        caller_address=ORIGIN_ADDRESS,
        contract_address=tx_execution_context.contract_address,
        class_hash=tx_execution_context.class_hash,
        selector=VALIDATE_ENTRY_POINT_SELECTOR,
        calldata_size=tx_execution_context.calldata_size,
        calldata=tx_execution_context.calldata,
        original_tx_info=tx_execution_context.original_tx_info,
        );

    execute_entry_point(block_context=block_context, execution_context=validate_execution_context);
    return ();
}

// Calls execute_entry_point and generates the corresponding CallContractResponse.
func contract_call_helper{
    range_check_ptr,
    builtin_ptrs: BuiltinPointers*,
    global_state_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(
    block_context: BlockContext*,
    execution_context: ExecutionContext*,
    call_response: CallContractResponse*,
) {
    let (retdata_size, retdata) = execute_entry_point(
        block_context=block_context, execution_context=execution_context
    );

    %{
        # Check that the actual return value matches the expected one.
        expected = memory.get_range(addr=ids.call_response.retdata, size=ids.retdata_size)
        actual = memory.get_range(addr=ids.retdata, size=ids.retdata_size)

        assert expected == actual, f'Return value mismatch expected={expected}, actual={actual}.'
    %}
    relocate_segment(src_ptr=call_response.retdata, dest_ptr=retdata);

    assert [call_response] = CallContractResponse(
        retdata_size=retdata_size,
        retdata=retdata);
    return ();
}

// Executes a syscall that calls another contract, invokes a delegate call or a library call.
func execute_contract_call_syscall{
    range_check_ptr,
    builtin_ptrs: BuiltinPointers*,
    global_state_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(
    block_context: BlockContext*,
    contract_address: felt,
    caller_address: felt,
    entry_point_type: felt,
    original_tx_info: TxInfo*,
    syscall_ptr: CallContract*,
) {
    alloc_locals;

    let call_req = syscall_ptr.request;

    let (state_entry: StateEntry*) = dict_read{dict_ptr=global_state_changes}(
        key=call_req.contract_address
    );

    local execution_context: ExecutionContext* = new ExecutionContext(
        entry_point_type=entry_point_type,
        caller_address=caller_address,
        contract_address=contract_address,
        class_hash=state_entry.class_hash,
        selector=call_req.function_selector,
        calldata_size=call_req.calldata_size,
        calldata=call_req.calldata,
        original_tx_info=original_tx_info,
        );

    return contract_call_helper(
        block_context=block_context,
        execution_context=execution_context,
        call_response=&syscall_ptr.response,
    );
}

// Implements the library_call and library_call_l1_handler system calls.
func execute_library_call_syscall{
    range_check_ptr,
    builtin_ptrs: BuiltinPointers*,
    global_state_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(
    block_context: BlockContext*,
    caller_execution_context: ExecutionContext*,
    entry_point_type: felt,
    syscall_ptr: LibraryCall*,
) {
    alloc_locals;

    let call_req = syscall_ptr.request;

    local execution_context: ExecutionContext* = new ExecutionContext(
        entry_point_type=entry_point_type,
        caller_address=caller_execution_context.caller_address,
        contract_address=caller_execution_context.contract_address,
        class_hash=call_req.class_hash,
        selector=call_req.function_selector,
        calldata_size=call_req.calldata_size,
        calldata=call_req.calldata,
        original_tx_info=caller_execution_context.original_tx_info,
        );

    return contract_call_helper(
        block_context=block_context,
        execution_context=execution_context,
        call_response=&syscall_ptr.response,
    );
}

func execute_deploy_syscall{
    range_check_ptr,
    builtin_ptrs: BuiltinPointers*,
    global_state_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*, caller_execution_context: ExecutionContext*, syscall_ptr: Deploy*) {
    let request = syscall_ptr.request;
    // Verify deploy_from_zero is either 0 (FALSE) or 1 (TRUE).
    assert request.deploy_from_zero * (request.deploy_from_zero - 1) = 0;
    // Set deployer_address to 0 if request.deploy_from_zero is TRUE.
    let deployer_address = (
        (1 - request.deploy_from_zero) * caller_execution_context.contract_address);

    let hash_ptr = builtin_ptrs.pedersen;
    with hash_ptr {
        let (contract_address) = get_contract_address(
            salt=request.contract_address_salt,
            class_hash=request.class_hash,
            constructor_calldata_size=request.constructor_calldata_size,
            constructor_calldata=request.constructor_calldata,
            deployer_address=deployer_address,
        );
    }
    tempvar builtin_ptrs = new BuiltinPointers(
        pedersen=hash_ptr,
        range_check=builtin_ptrs.range_check,
        ecdsa=builtin_ptrs.ecdsa,
        bitwise=builtin_ptrs.bitwise,
        ec_op=builtin_ptrs.ec_op,
        );

    // Fill the syscall response, before contract_address is revoked.
    assert syscall_ptr.response = DeployResponse(
        contract_address=contract_address,
        constructor_retdata_size=0,
        constructor_retdata=cast(0, felt*),
        );

    tempvar constructor_execution_context = new ExecutionContext(
        entry_point_type=ENTRY_POINT_TYPE_CONSTRUCTOR,
        caller_address=caller_execution_context.contract_address,
        contract_address=contract_address,
        class_hash=request.class_hash,
        selector=CONSTRUCTOR_ENTRY_POINT_SELECTOR,
        calldata_size=request.constructor_calldata_size,
        calldata=request.constructor_calldata,
        original_tx_info=caller_execution_context.original_tx_info,
        );

    deploy_contract(
        block_context=block_context, constructor_execution_context=constructor_execution_context
    );

    return ();
}

// Reads a value from the current contract's storage.
func execute_storage_read{global_state_changes: DictAccess*}(
    contract_address, syscall_ptr: StorageRead*
) {
    alloc_locals;
    local state_entry: StateEntry*;
    local new_state_entry: StateEntry*;
    %{
        # Fetch a state_entry in this hint and validate it in the update that comes next.
        ids.state_entry = __dict_manager.get_dict(ids.global_state_changes)[ids.contract_address]

        ids.new_state_entry = segments.add()
    %}

    tempvar value = syscall_ptr.response.value;

    // Update the contract's storage.
    tempvar storage_ptr = state_entry.storage_ptr;
    assert [storage_ptr] = DictAccess(
        key=syscall_ptr.request.address, prev_value=value, new_value=value);
    let storage_ptr = storage_ptr + DictAccess.SIZE;

    // Update global_state_changes.
    assert [new_state_entry] = StateEntry(
        class_hash=state_entry.class_hash,
        storage_ptr=storage_ptr,
        nonce=state_entry.nonce);
    dict_update{dict_ptr=global_state_changes}(
        key=contract_address,
        prev_value=cast(state_entry, felt),
        new_value=cast(new_state_entry, felt),
    );

    return ();
}

// Write a value to the current contract's storage.
func execute_storage_write{global_state_changes: DictAccess*}(
    contract_address, syscall_ptr: StorageWrite*
) {
    alloc_locals;
    local prev_value: felt;
    local state_entry: StateEntry*;
    local new_state_entry: StateEntry*;
    %{
        ids.prev_value = syscall_handler.execute_syscall_storage_write(
            contract_address=ids.contract_address,
            key=ids.syscall_ptr.address,
            value=ids.syscall_ptr.value
        )

        # Fetch a state_entry in this hint and validate it in the update that comes next.
        ids.state_entry = __dict_manager.get_dict(ids.global_state_changes)[ids.contract_address]

        ids.new_state_entry = segments.add()
    %}

    // Update the contract's storage.
    tempvar storage_ptr = state_entry.storage_ptr;
    assert [storage_ptr] = DictAccess(
        key=syscall_ptr.address, prev_value=prev_value, new_value=syscall_ptr.value);
    let storage_ptr = storage_ptr + DictAccess.SIZE;

    // Update global_state_changes.
    assert [new_state_entry] = StateEntry(
        class_hash=state_entry.class_hash,
        storage_ptr=storage_ptr,
        nonce=state_entry.nonce);
    dict_update{dict_ptr=global_state_changes}(
        key=contract_address,
        prev_value=cast(state_entry, felt),
        new_value=cast(new_state_entry, felt),
    );

    return ();
}

// Executes the system calls in syscall_ptr.
//
// Arguments:
// block_context - a read-only context used for transaction execution.
// execution_context - The execution context in which the system calls need to be executed.
// syscall_ptr - a pointer to the syscall segment that needs to be executed.
// syscall_size - The size of the system call segment to be executed.
func execute_syscalls{
    range_check_ptr,
    builtin_ptrs: BuiltinPointers*,
    global_state_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(
    block_context: BlockContext*,
    execution_context: ExecutionContext*,
    syscall_size,
    syscall_ptr: felt*,
) {
    if (syscall_size == 0) {
        return ();
    }

    tempvar selector = [syscall_ptr];

    if (selector == STORAGE_READ_SELECTOR) {
        execute_storage_read(
            contract_address=execution_context.contract_address,
            syscall_ptr=cast(syscall_ptr, StorageRead*),
        );
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_size=syscall_size - StorageRead.SIZE,
            syscall_ptr=syscall_ptr + StorageRead.SIZE,
        );
    }

    if (selector == STORAGE_WRITE_SELECTOR) {
        execute_storage_write(
            contract_address=execution_context.contract_address,
            syscall_ptr=cast(syscall_ptr, StorageWrite*),
        );
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_size=syscall_size - StorageWrite.SIZE,
            syscall_ptr=syscall_ptr + StorageWrite.SIZE,
        );
    }

    if (selector == EMIT_EVENT_SELECTOR) {
        // Skip as long as the block hash is not calculated by the OS.
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_size=syscall_size - EmitEvent.SIZE,
            syscall_ptr=syscall_ptr + EmitEvent.SIZE,
        );
    }

    if (selector == CALL_CONTRACT_SELECTOR) {
        let call_contract_syscall = cast(syscall_ptr, CallContract*);
        execute_contract_call_syscall(
            block_context=block_context,
            contract_address=call_contract_syscall.request.contract_address,
            caller_address=execution_context.contract_address,
            entry_point_type=ENTRY_POINT_TYPE_EXTERNAL,
            original_tx_info=execution_context.original_tx_info,
            syscall_ptr=call_contract_syscall,
        );
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_size=syscall_size - CallContract.SIZE,
            syscall_ptr=syscall_ptr + CallContract.SIZE,
        );
    }

    if (selector == LIBRARY_CALL_SELECTOR) {
        execute_library_call_syscall(
            block_context=block_context,
            caller_execution_context=execution_context,
            entry_point_type=ENTRY_POINT_TYPE_EXTERNAL,
            syscall_ptr=cast(syscall_ptr, LibraryCall*),
        );
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_size=syscall_size - LibraryCall.SIZE,
            syscall_ptr=syscall_ptr + LibraryCall.SIZE,
        );
    }

    if (selector == LIBRARY_CALL_L1_HANDLER_SELECTOR) {
        execute_library_call_syscall(
            block_context=block_context,
            caller_execution_context=execution_context,
            entry_point_type=ENTRY_POINT_TYPE_L1_HANDLER,
            syscall_ptr=cast(syscall_ptr, LibraryCall*),
        );
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_size=syscall_size - LibraryCall.SIZE,
            syscall_ptr=syscall_ptr + LibraryCall.SIZE,
        );
    }

    if (selector == GET_TX_INFO_SELECTOR) {
        assert cast(syscall_ptr, GetTxInfo*).response = GetTxInfoResponse(
            tx_info=execution_context.original_tx_info);
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_size=syscall_size - GetTxInfo.SIZE,
            syscall_ptr=syscall_ptr + GetTxInfo.SIZE,
        );
    }

    if (selector == GET_CALLER_ADDRESS_SELECTOR) {
        assert [cast(syscall_ptr, GetCallerAddress*)].response = GetCallerAddressResponse(
            caller_address=execution_context.caller_address);
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_size=syscall_size - GetCallerAddress.SIZE,
            syscall_ptr=syscall_ptr + GetCallerAddress.SIZE,
        );
    }

    if (selector == GET_SEQUENCER_ADDRESS_SELECTOR) {
        assert [cast(syscall_ptr, GetSequencerAddress*)].response = GetSequencerAddressResponse(
            sequencer_address=block_context.sequencer_address);
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_size=syscall_size - GetSequencerAddress.SIZE,
            syscall_ptr=syscall_ptr + GetSequencerAddress.SIZE,
        );
    }

    if (selector == GET_CONTRACT_ADDRESS_SELECTOR) {
        assert [cast(syscall_ptr, GetContractAddress*)].response = GetContractAddressResponse(
            contract_address=execution_context.contract_address);
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_size=syscall_size - GetContractAddress.SIZE,
            syscall_ptr=syscall_ptr + GetContractAddress.SIZE,
        );
    }

    if (selector == GET_BLOCK_TIMESTAMP_SELECTOR) {
        assert [cast(syscall_ptr, GetBlockTimestamp*)].response = GetBlockTimestampResponse(
            block_timestamp=block_context.block_info.block_timestamp);
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_size=syscall_size - GetBlockTimestamp.SIZE,
            syscall_ptr=syscall_ptr + GetBlockTimestamp.SIZE,
        );
    }

    if (selector == GET_BLOCK_NUMBER_SELECTOR) {
        assert [cast(syscall_ptr, GetBlockNumber*)].response = GetBlockNumberResponse(
            block_number=block_context.block_info.block_number);
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_size=syscall_size - GetBlockNumber.SIZE,
            syscall_ptr=syscall_ptr + GetBlockNumber.SIZE,
        );
    }

    if (selector == GET_TX_SIGNATURE_SELECTOR) {
        tempvar original_tx_info: TxInfo* = execution_context.original_tx_info;
        assert [cast(syscall_ptr, GetTxSignature*)].response = GetTxSignatureResponse(
            signature_len=original_tx_info.signature_len,
            signature=original_tx_info.signature
            );
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_size=syscall_size - GetTxSignature.SIZE,
            syscall_ptr=syscall_ptr + GetTxSignature.SIZE,
        );
    }

    if (selector == DEPLOY_SELECTOR) {
        execute_deploy_syscall(
            block_context=block_context,
            caller_execution_context=execution_context,
            syscall_ptr=cast(syscall_ptr, Deploy*),
        );
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_size=syscall_size - Deploy.SIZE,
            syscall_ptr=syscall_ptr + Deploy.SIZE,
        );
    }

    // DEPRECATED.
    if (selector == DELEGATE_CALL_SELECTOR) {
        execute_contract_call_syscall(
            block_context=block_context,
            contract_address=execution_context.contract_address,
            caller_address=execution_context.caller_address,
            entry_point_type=ENTRY_POINT_TYPE_EXTERNAL,
            original_tx_info=execution_context.original_tx_info,
            syscall_ptr=cast(syscall_ptr, CallContract*),
        );
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_size=syscall_size - CallContract.SIZE,
            syscall_ptr=syscall_ptr + CallContract.SIZE,
        );
    }

    // DEPRECATED.
    if (selector == DELEGATE_L1_HANDLER_SELECTOR) {
        execute_contract_call_syscall(
            block_context=block_context,
            contract_address=execution_context.contract_address,
            caller_address=execution_context.caller_address,
            entry_point_type=ENTRY_POINT_TYPE_L1_HANDLER,
            original_tx_info=execution_context.original_tx_info,
            syscall_ptr=cast(syscall_ptr, CallContract*),
        );
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_size=syscall_size - CallContract.SIZE,
            syscall_ptr=syscall_ptr + CallContract.SIZE,
        );
    }

    // Here the system call must be 'SendMessageToL1'.
    assert selector = SEND_MESSAGE_TO_L1_SELECTOR;

    let syscall = [cast(syscall_ptr, SendMessageToL1SysCall*)];

    assert [outputs.messages_to_l1] = MessageToL1Header(
        from_address=execution_context.contract_address,
        to_address=syscall.to_address,
        payload_size=syscall.payload_size);
    memcpy(
        dst=outputs.messages_to_l1 + MessageToL1Header.SIZE,
        src=syscall.payload_ptr,
        len=syscall.payload_size,
    );
    let (outputs) = os_carried_outputs_new(
        messages_to_l1=outputs.messages_to_l1 + MessageToL1Header.SIZE +
        outputs.messages_to_l1.payload_size,
        messages_to_l2=outputs.messages_to_l2,
        deployment_info=outputs.deployment_info,
    );
    return execute_syscalls(
        block_context=block_context,
        execution_context=execution_context,
        syscall_size=syscall_size - SendMessageToL1SysCall.SIZE,
        syscall_ptr=syscall_ptr + SendMessageToL1SysCall.SIZE,
    );
}

// Adds 'tx' with the given 'nonce' to 'outputs.messages_to_l2'.
func consume_l1_to_l2_message{outputs: OsCarriedOutputs*}(
    execution_context: ExecutionContext*, nonce: felt
) {
    assert_not_zero(execution_context.calldata_size);
    // The payload is the calldata without the from_address argument (which is the first).
    let payload: felt* = execution_context.calldata + 1;
    tempvar payload_size = execution_context.calldata_size - 1;

    // Write the given transaction to the output.
    assert [outputs.messages_to_l2] = MessageToL2Header(
        from_address=[execution_context.calldata],
        to_address=execution_context.contract_address,
        nonce=nonce,
        selector=execution_context.selector,
        payload_size=payload_size);

    let message_payload = cast(outputs.messages_to_l2 + MessageToL2Header.SIZE, felt*);
    memcpy(dst=message_payload, src=payload, len=payload_size);

    let (outputs) = os_carried_outputs_new(
        messages_to_l1=outputs.messages_to_l1,
        messages_to_l2=outputs.messages_to_l2 + MessageToL2Header.SIZE +
        outputs.messages_to_l2.payload_size,
        deployment_info=outputs.deployment_info,
    );
    return ();
}

// Returns the entry point's offset in the program based on 'contract_class' and
// 'execution_context'.
func get_entry_point_offset{range_check_ptr}(
    contract_class: ContractClass*, execution_context: ExecutionContext*
) -> (entry_point_offset: felt) {
    alloc_locals;
    // Get the entry points corresponding to the transaction's type.
    local entry_points: ContractEntryPoint*;
    local n_entry_points: felt;

    tempvar entry_point_type = execution_context.entry_point_type;
    if (entry_point_type == ENTRY_POINT_TYPE_L1_HANDLER) {
        entry_points = contract_class.l1_handlers;
        n_entry_points = contract_class.n_l1_handlers;
    } else {
        if (entry_point_type == ENTRY_POINT_TYPE_EXTERNAL) {
            entry_points = contract_class.external_functions;
            n_entry_points = contract_class.n_external_functions;
        } else {
            assert entry_point_type = ENTRY_POINT_TYPE_CONSTRUCTOR;
            entry_points = contract_class.constructors;
            n_entry_points = contract_class.n_constructors;

            if (n_entry_points == 0) {
                return (entry_point_offset=NOP_ENTRY_POINT_OFFSET);
            }
        }
    }

    // The key must be at offset 0.
    static_assert ContractEntryPoint.selector == 0;
    let (entry_point_desc: ContractEntryPoint*, success) = search_sorted(
        array_ptr=cast(entry_points, felt*),
        elm_size=ContractEntryPoint.SIZE,
        n_elms=n_entry_points,
        key=execution_context.selector,
    );
    if (success != 0) {
        return (entry_point_offset=entry_point_desc.offset);
    }

    // If the selector was not found, verify that the first entry point is the default entry point,
    // and call it.
    assert entry_points[0].selector = DEFAULT_ENTRY_POINT_SELECTOR;
    return (entry_point_offset=entry_points[0].offset);
}

// Executes an entry point in a contract.
// The contract entry point is selected based on execution_context.entry_point_type
// and execution_context.selector.
//
// Arguments:
// block_context - a global context that is fixed throughout the block.
// execution_context - The context for the current execution.
func execute_entry_point{
    range_check_ptr,
    builtin_ptrs: BuiltinPointers*,
    global_state_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*, execution_context: ExecutionContext*) -> (
    retdata_size: felt, retdata: felt*
) {
    alloc_locals;

    // The key must be at offset 0.
    static_assert ContractClassFact.hash == 0;
    let (contract_class_fact: ContractClassFact*) = find_element(
        array_ptr=block_context.contract_class_facts,
        elm_size=ContractClassFact.SIZE,
        n_elms=block_context.n_contract_class_facts,
        key=execution_context.class_hash,
    );
    local contract_class: ContractClass* = contract_class_fact.contract_class;

    let (entry_point_offset) = get_entry_point_offset(
        contract_class=contract_class, execution_context=execution_context
    );

    %{ syscall_handler.enter_call() %}
    if (entry_point_offset == NOP_ENTRY_POINT_OFFSET) {
        // Assert that there is no call data in the case of NOP entry point.
        assert execution_context.calldata_size = 0;
        %{ syscall_handler.exit_call() %}
        return (retdata_size=0, retdata=cast(0, felt*));
    }

    local range_check_ptr = range_check_ptr;
    local contract_entry_point: felt* = contract_class.bytecode_ptr + entry_point_offset;

    local os_context: felt*;
    local syscall_ptr: felt*;

    %{
        ids.os_context = segments.add()
        ids.syscall_ptr = segments.add()
    %}
    assert [os_context] = cast(syscall_ptr, felt);

    let n_builtins = BuiltinEncodings.SIZE;
    local builtin_params: BuiltinParams* = block_context.builtin_params;
    select_builtins(
        n_builtins=n_builtins,
        all_encodings=builtin_params.builtin_encodings,
        all_ptrs=builtin_ptrs,
        n_selected_builtins=contract_class.n_builtins,
        selected_encodings=contract_class.builtin_list,
        selected_ptrs=os_context + 1,
    );

    // Use tempvar to pass arguments to contract_entry_point().
    tempvar selector = execution_context.selector;
    tempvar context = os_context;
    tempvar calldata_size = execution_context.calldata_size;
    tempvar calldata = execution_context.calldata;
    %{ vm_enter_scope({'syscall_handler': syscall_handler}) %}
    call abs contract_entry_point;
    %{ vm_exit_scope() %}
    // Retrieve returned_builtin_ptrs_subset.
    // Note that returned_builtin_ptrs_subset cannot be set in a hint because doing so will allow a
    // malicious prover to lie about the storage changes of a valid contract.
    let (ap_val) = get_ap();
    local returned_builtin_ptrs_subset: felt* = cast(
        ap_val - contract_class.n_builtins - 2, felt*);
    local retdata_size: felt = [ap_val - 2];
    local retdata: felt* = cast([ap_val - 1], felt*);

    local return_builtin_ptrs: BuiltinPointers*;
    %{
        from starkware.starknet.core.os.os_utils import update_builtin_pointers

        # Fill the values of all builtin pointers after the current transaction.
        ids.return_builtin_ptrs = segments.gen_arg(
            update_builtin_pointers(
                memory=memory,
                n_builtins=ids.n_builtins,
                builtins_encoding_addr=ids.builtin_params.builtin_encodings.address_,
                n_selected_builtins=ids.contract_class.n_builtins,
                selected_builtins_encoding_addr=ids.contract_class.builtin_list,
                orig_builtins_ptrs_addr=ids.builtin_ptrs.address_,
                selected_builtins_ptrs_addr=ids.returned_builtin_ptrs_subset,
                ),
            )
    %}
    select_builtins(
        n_builtins=n_builtins,
        all_encodings=builtin_params.builtin_encodings,
        all_ptrs=return_builtin_ptrs,
        n_selected_builtins=contract_class.n_builtins,
        selected_encodings=contract_class.builtin_list,
        selected_ptrs=returned_builtin_ptrs_subset,
    );

    // Call validate_builtins to validate that the builtin pointers have advanced correctly.
    validate_builtins(
        prev_builtin_ptrs=builtin_ptrs,
        new_builtin_ptrs=return_builtin_ptrs,
        builtin_instance_sizes=builtin_params.builtin_instance_sizes,
        n_builtins=n_builtins,
    );

    let syscall_end = cast([returned_builtin_ptrs_subset - 1], felt*);

    let builtin_ptrs = return_builtin_ptrs;
    execute_syscalls(
        block_context=block_context,
        execution_context=execution_context,
        syscall_size=syscall_end - syscall_ptr,
        syscall_ptr=syscall_ptr,
    );

    %{ syscall_handler.exit_call() %}
    return (retdata_size=retdata_size, retdata=retdata);
}

// Deploys a contract.
//
// Arguments:
// block_context - A global context that is fixed throughout the block.
// constructor_execution_context - The ExecutionContext of the constructor.
func deploy_contract{
    range_check_ptr,
    builtin_ptrs: BuiltinPointers*,
    global_state_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*, constructor_execution_context: ExecutionContext*) {
    alloc_locals;

    local contract_address = constructor_execution_context.contract_address;

    // Assert that we don't deploy to ORIGIN_ADDRESS.
    assert_not_zero(contract_address - ORIGIN_ADDRESS);

    local state_entry: StateEntry*;
    %{
        # Fetch a state_entry in this hint and validate it in the update at the end
        # of this function.
        ids.state_entry = __dict_manager.get_dict(ids.global_state_changes)[ids.contract_address]
    %}
    assert state_entry.class_hash = UNINITIALIZED_CLASS_HASH;
    assert state_entry.nonce = 0;

    tempvar new_state_entry = new StateEntry(
        class_hash=constructor_execution_context.class_hash,
        storage_ptr=state_entry.storage_ptr,
        nonce=0);

    dict_update{dict_ptr=global_state_changes}(
        key=contract_address,
        prev_value=cast(state_entry, felt),
        new_value=cast(new_state_entry, felt),
    );

    // Write the contract address and hash to the output.
    assert [outputs.deployment_info] = DeploymentInfo(
        contract_address=contract_address,
        class_hash=new_state_entry.class_hash,
        );

    // Advance outputs.deployment_info.
    let (outputs) = os_carried_outputs_new(
        messages_to_l1=outputs.messages_to_l1,
        messages_to_l2=outputs.messages_to_l2,
        deployment_info=&outputs.deployment_info[1],
    );

    // Invoke the contract constructor.
    execute_entry_point(
        block_context=block_context, execution_context=constructor_execution_context
    );

    return ();
}

// Prepares a constructor execution context based on the 'tx' hint variable.
// Leaves 'original_tx_info' empty - should be filled later on.
func prepare_constructor_execution_context{range_check_ptr, builtin_ptrs: BuiltinPointers*}() -> (
    constructor_execution_context: ExecutionContext*, salt: felt
) {
    alloc_locals;

    local contract_address_salt;
    local class_hash;
    local constructor_calldata_size;
    local constructor_calldata: felt*;
    %{
        # Import from_bytes for the class_hash assignment below.
        from starkware.python.utils import from_bytes

        ids.contract_address_salt = tx.contract_address_salt
        ids.class_hash = from_bytes(tx.class_hash)
        ids.constructor_calldata_size = len(tx.constructor_calldata)
        ids.constructor_calldata = segments.gen_arg(arg=tx.constructor_calldata)
    %}
    assert_nn(constructor_calldata_size);

    let hash_ptr = builtin_ptrs.pedersen;
    with hash_ptr {
        let (contract_address) = get_contract_address(
            salt=contract_address_salt,
            class_hash=class_hash,
            constructor_calldata_size=constructor_calldata_size,
            constructor_calldata=constructor_calldata,
            deployer_address=0,
        );
    }
    tempvar builtin_ptrs = new BuiltinPointers(
        pedersen=hash_ptr,
        range_check=builtin_ptrs.range_check,
        ecdsa=builtin_ptrs.ecdsa,
        bitwise=builtin_ptrs.bitwise,
        ec_op=builtin_ptrs.ec_op,
        );

    tempvar constructor_execution_context = new ExecutionContext(
        entry_point_type=ENTRY_POINT_TYPE_CONSTRUCTOR,
        caller_address=ORIGIN_ADDRESS,
        contract_address=contract_address,
        class_hash=class_hash,
        selector=CONSTRUCTOR_ENTRY_POINT_SELECTOR,
        calldata_size=constructor_calldata_size,
        calldata=constructor_calldata,
        original_tx_info=cast(nondet %{ segments.add() %}, TxInfo*),
        );

    return (
        constructor_execution_context=constructor_execution_context, salt=contract_address_salt
    );
}

func execute_deploy_account_transaction{
    range_check_ptr,
    builtin_ptrs: BuiltinPointers*,
    global_state_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*) {
    alloc_locals;

    // Calculate address and prepare constructor execution context.
    let (
        local constructor_execution_context: ExecutionContext*, local salt
    ) = prepare_constructor_execution_context();

    // Prepare validate_deploy calldata.
    let (validate_deploy_calldata: felt*) = alloc();
    assert validate_deploy_calldata[0] = constructor_execution_context.class_hash;
    assert validate_deploy_calldata[1] = salt;
    memcpy(
        dst=&validate_deploy_calldata[2],
        src=constructor_execution_context.calldata,
        len=constructor_execution_context.calldata_size,
    );

    // Note that the members of original_tx_info are not initialized at this point.
    local original_tx_info: TxInfo* = constructor_execution_context.original_tx_info;
    local validate_deploy_execution_context: ExecutionContext* = new ExecutionContext(
        entry_point_type=ENTRY_POINT_TYPE_EXTERNAL,
        caller_address=ORIGIN_ADDRESS,
        contract_address=constructor_execution_context.contract_address,
        class_hash=constructor_execution_context.class_hash,
        selector=VALIDATE_DEPLOY_ENTRY_POINT_SELECTOR,
        calldata_size=constructor_execution_context.calldata_size + 2,
        calldata=validate_deploy_calldata,
        original_tx_info=original_tx_info,
        );

    // Compute transaction hash and prepare transaction info.
    let tx_version = TRANSACTION_VERSION;
    local max_fee = nondet %{ tx.max_fee %};
    local nonce_ptr: felt* = cast(nondet %{ segments.gen_arg([tx.nonce]) %}, felt*);
    let (transaction_hash) = compute_transaction_hash(
        tx_hash_prefix=DEPLOY_ACCOUNT_HASH_PREFIX,
        version=tx_version,
        execution_context=validate_deploy_execution_context,
        entry_point_selector_field=0,
        max_fee=max_fee,
        chain_id=block_context.starknet_os_config.chain_id,
        additional_data_size=1,
        additional_data=nonce_ptr,
    );

    // Assign the transaction info to both calls.
    // Note that both constructor_execution_context and
    // validate_deploy_execution_context hold this pointer.
    assert [original_tx_info] = TxInfo(
        version=tx_version,
        account_contract_address=validate_deploy_execution_context.contract_address,
        max_fee=max_fee,
        signature_len=nondet %{ len(tx.signature) %},
        signature=cast(nondet %{ segments.gen_arg(arg=tx.signature) %}, felt*),
        transaction_hash=transaction_hash,
        chain_id=block_context.starknet_os_config.chain_id,
        nonce=[nonce_ptr],
        );

    %{ syscall_handler.start_tx(tx_info_ptr=ids.original_tx_info.address_) %}

    deploy_contract(
        block_context=block_context, constructor_execution_context=constructor_execution_context
    );

    // Handle nonce here since 'deploy_contract' verifies that the nonce is zeroed.
    check_and_increment_nonce(
        execution_context=validate_deploy_execution_context, nonce=[nonce_ptr]
    );

    // Runs the account contract's "__validate_deploy__" entry point,
    // which is responsible for signature verification.
    execute_entry_point(
        block_context=block_context, execution_context=validate_deploy_execution_context
    );
    charge_fee(block_context=block_context, tx_execution_context=validate_deploy_execution_context);

    %{ syscall_handler.end_tx() %}
    return ();
}

func execute_deploy_transaction{
    range_check_ptr,
    builtin_ptrs: BuiltinPointers*,
    global_state_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*) {
    alloc_locals;

    let (
        local constructor_execution_context: ExecutionContext*, _
    ) = prepare_constructor_execution_context();

    // Guess tx version and make sure it's valid.
    local tx_version = nondet %{ tx.version %};
    validate_transaction_version(tx_version=tx_version);

    let nullptr = cast(0, felt*);
    local chain_id = block_context.starknet_os_config.chain_id;
    let (transaction_hash) = compute_transaction_hash(
        tx_hash_prefix=DEPLOY_HASH_PREFIX,
        version=tx_version,
        execution_context=constructor_execution_context,
        entry_point_selector_field=CONSTRUCTOR_ENTRY_POINT_SELECTOR,
        max_fee=0,
        chain_id=chain_id,
        additional_data_size=0,
        additional_data=nullptr,
    );

    assert [constructor_execution_context.original_tx_info] = TxInfo(
        version=tx_version,
        account_contract_address=ORIGIN_ADDRESS,
        max_fee=0,
        signature_len=0,
        signature=nullptr,
        transaction_hash=transaction_hash,
        chain_id=chain_id,
        nonce=0,
        );

    %{
        syscall_handler.start_tx(
            tx_info_ptr=ids.constructor_execution_context.original_tx_info.address_
        )
    %}

    deploy_contract(
        block_context=block_context, constructor_execution_context=constructor_execution_context
    );
    %{ syscall_handler.end_tx() %}
    return ();
}

func execute_declare_transaction{
    range_check_ptr,
    builtin_ptrs: BuiltinPointers*,
    global_state_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*) {
    alloc_locals;

    // Guess tx fields.
    local tx_version;
    local nonce_ptr: felt*;
    local max_fee;
    local sender_address;
    local declared_class_hash_ptr: felt*;
    %{
        from starkware.python.utils import from_bytes

        ids.tx_version = tx.version
        ids.nonce_ptr = segments.gen_arg([tx.nonce])
        ids.max_fee = tx.max_fee
        ids.sender_address = tx.sender_address
        ids.declared_class_hash_ptr = segments.gen_arg([from_bytes(tx.class_hash)])
    %}
    validate_transaction_version(tx_version=tx_version);

    if (tx_version == 0) {
        %{ syscall_handler.skip_tx() %}
        return ();
    }

    local chain_id = block_context.starknet_os_config.chain_id;
    let (state_entry: StateEntry*) = dict_read{dict_ptr=global_state_changes}(key=sender_address);
    local validate_declare_execution_context: ExecutionContext* = new ExecutionContext(
        entry_point_type=ENTRY_POINT_TYPE_EXTERNAL,
        caller_address=ORIGIN_ADDRESS,
        contract_address=sender_address,
        class_hash=state_entry.class_hash,
        selector=VALIDATE_DECLARE_ENTRY_POINT_SELECTOR,
        calldata_size=1,
        calldata=declared_class_hash_ptr,
        original_tx_info=cast(nondet %{ segments.add() %}, TxInfo*),
        );
    let (transaction_hash) = compute_transaction_hash(
        tx_hash_prefix=DECLARE_HASH_PREFIX,
        version=tx_version,
        execution_context=validate_declare_execution_context,
        entry_point_selector_field=0,
        max_fee=max_fee,
        chain_id=chain_id,
        additional_data_size=1,
        additional_data=nonce_ptr,
    );
    assert [validate_declare_execution_context.original_tx_info] = TxInfo(
        version=tx_version,
        account_contract_address=sender_address,
        max_fee=max_fee,
        signature_len=nondet %{ len(tx.signature) %},
        signature=cast(nondet %{ segments.gen_arg(arg=tx.signature) %}, felt*),
        transaction_hash=transaction_hash,
        chain_id=chain_id,
        nonce=[nonce_ptr],
        );

    check_and_increment_nonce(
        execution_context=validate_declare_execution_context, nonce=[nonce_ptr]
    );

    %{
        syscall_handler.start_tx(
            tx_info_ptr=ids.validate_declare_execution_context.original_tx_info.address_
        )
    %}

    // Run the account contract's "__validate_declare__" entry point.
    execute_entry_point(
        block_context=block_context, execution_context=validate_declare_execution_context
    );
    charge_fee(
        block_context=block_context, tx_execution_context=validate_declare_execution_context
    );

    %{ syscall_handler.end_tx() %}

    return ();
}

// Computes the hash of the transaction.
//
// Note that execution_context.original_tx_info is uninitialized when this function is called.
// In particular, this field is not used in this function.
func compute_transaction_hash{builtin_ptrs: BuiltinPointers*}(
    tx_hash_prefix: felt,
    version: felt,
    execution_context: ExecutionContext*,
    entry_point_selector_field: felt,
    max_fee: felt,
    chain_id: felt,
    additional_data_size: felt,
    additional_data: felt*,
) -> (transaction_hash: felt) {
    let hash_ptr = builtin_ptrs.pedersen;
    with hash_ptr {
        let (transaction_hash) = get_transaction_hash(
            tx_hash_prefix=tx_hash_prefix,
            version=version,
            contract_address=execution_context.contract_address,
            entry_point_selector=entry_point_selector_field,
            calldata_size=execution_context.calldata_size,
            calldata=execution_context.calldata,
            max_fee=max_fee,
            chain_id=chain_id,
            additional_data_size=additional_data_size,
            additional_data=additional_data,
        );
    }

    %{
        assert ids.transaction_hash == tx.hash_value, (
            "Computed transaction_hash is inconsistent with the hash in the transaction. "
            f"Computed hash = {ids.transaction_hash}, Expected hash = {tx.hash_value}.")
    %}

    tempvar builtin_ptrs = new BuiltinPointers(
        pedersen=hash_ptr,
        range_check=builtin_ptrs.range_check,
        ecdsa=builtin_ptrs.ecdsa,
        bitwise=builtin_ptrs.bitwise,
        ec_op=builtin_ptrs.ec_op,
        );

    return (transaction_hash=transaction_hash);
}
