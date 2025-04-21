from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.builtin_poseidon.poseidon import poseidon_hash_many
from starkware.cairo.common.cairo_builtins import (
    BitwiseBuiltin,
    HashBuiltin,
    KeccakBuiltin,
    ModBuiltin,
    PoseidonBuiltin,
)
from starkware.cairo.common.cairo_sha256.sha256_utils import finalize_sha256
from starkware.cairo.common.dict import dict_new, dict_read, dict_update
from starkware.cairo.common.dict_access import DictAccess
from starkware.cairo.common.math import assert_nn, assert_nn_le, assert_not_zero
from starkware.cairo.common.memcpy import memcpy
from starkware.cairo.common.registers import get_fp_and_pc
from starkware.cairo.common.segments import relocate_segment
from starkware.cairo.common.sha256_state import Sha256ProcessBlock
from starkware.cairo.common.uint256 import Uint256
from starkware.starknet.builtins.segment_arena.segment_arena import new_arena
from starkware.starknet.common.constants import (
    DECLARE_HASH_PREFIX,
    DEPLOY_ACCOUNT_HASH_PREFIX,
    INVOKE_HASH_PREFIX,
    ORIGIN_ADDRESS,
)
from starkware.starknet.common.new_syscalls import BlockInfo, ExecutionInfo, ResourceBounds, TxInfo
from starkware.starknet.common.syscalls import Deploy
from starkware.starknet.common.syscalls import TxInfo as DeprecatedTxInfo
from starkware.starknet.core.os.block_context import BlockContext
from starkware.starknet.core.os.builtins import (
    BuiltinPointers,
    NonSelectableBuiltins,
    SelectableBuiltins,
)
from starkware.starknet.core.os.constants import (
    CONSTRUCTOR_ENTRY_POINT_SELECTOR,
    DEFAULT_ENTRY_POINT_SELECTOR,
    DEFAULT_INITIAL_GAS_COST,
    DEFAULT_INITIAL_GAS_COST_NO_L2,
    ENTRY_POINT_TYPE_CONSTRUCTOR,
    ENTRY_POINT_TYPE_EXTERNAL,
    ENTRY_POINT_TYPE_L1_HANDLER,
    EXECUTE_ENTRY_POINT_SELECTOR,
    EXECUTE_MAX_SIERRA_GAS,
    L1_DATA_GAS,
    L1_DATA_GAS_INDEX,
    L1_GAS_INDEX,
    L1_HANDLER_L2_GAS_MAX_AMOUNT,
    L1_HANDLER_VERSION,
    L2_GAS_INDEX,
    SIERRA_ARRAY_LEN_BOUND,
    TRANSFER_ENTRY_POINT_SELECTOR,
    VALIDATE_DECLARE_ENTRY_POINT_SELECTOR,
    VALIDATE_DEPLOY_ENTRY_POINT_SELECTOR,
    VALIDATE_MAX_SIERRA_GAS,
    VALIDATED,
)
from starkware.starknet.core.os.contract_address.contract_address import get_contract_address
from starkware.starknet.core.os.contract_class.contract_class import (
    ContractClassComponentHashes,
    finalize_class_hash,
)
from starkware.starknet.core.os.contract_class.deprecated_compiled_class import (
    DeprecatedCompiledClassFact,
)
from starkware.starknet.core.os.execution.deprecated_execute_entry_point import (
    deprecated_execute_entry_point,
    non_reverting_select_execute_entry_point_func,
)
from starkware.starknet.core.os.execution.deprecated_execute_syscalls import deploy_contract
from starkware.starknet.core.os.execution.execute_entry_point import ExecutionContext
from starkware.starknet.core.os.execution.execute_transaction_utils import (
    assert_deprecated_tx_fields_consistency,
    cap_remaining_gas,
    check_and_increment_nonce,
    fill_deprecated_tx_info,
    run_validate,
    update_class_hash_in_execution_context,
)
from starkware.starknet.core.os.execution.revert import init_revert_log
from starkware.starknet.core.os.output import (
    MessageToL2Header,
    OsCarriedOutputs,
    os_carried_outputs_new,
)
from starkware.starknet.core.os.state.commitment import StateEntry
from starkware.starknet.core.os.transaction_hash.transaction_hash import (
    CommonTxFields,
    compute_declare_transaction_hash,
    compute_deploy_account_transaction_hash,
    compute_invoke_transaction_hash,
    compute_l1_handler_transaction_hash,
    update_pedersen_in_builtin_ptrs,
    update_poseidon_in_builtin_ptrs,
)

// Returns the transaction's initial gas derived from its resource bounds.
func get_initial_user_gas_bound(common_tx_fields: CommonTxFields*) -> felt {
    assert common_tx_fields.n_resource_bounds = 3;
    return common_tx_fields.resource_bounds[L2_GAS_INDEX].max_amount;
}

// Executes the transactions in the hint variable block_input.transactions.
//
// Returns:
// reserved_range_checks_end - end pointer for the reserved range checks.
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
    bitwise_ptr: BitwiseBuiltin*,
    ec_op_ptr,
    keccak_ptr: KeccakBuiltin*,
    poseidon_ptr: PoseidonBuiltin*,
    range_check96_ptr: felt*,
    add_mod_ptr: ModBuiltin*,
    mul_mod_ptr: ModBuiltin*,
    contract_state_changes: DictAccess*,
    contract_class_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
    txs_range_check_ptr,
}(block_context: BlockContext*) {
    alloc_locals;

    // Prepare builtin pointers.
    let segment_arena_ptr = new_arena();
    let (sha256_ptr: Sha256ProcessBlock*) = alloc();
    %{ syscall_handler.sha256_segment = ids.sha256_ptr %}

    let (__fp__, _) = get_fp_and_pc();
    local local_builtin_ptrs: BuiltinPointers = BuiltinPointers(
        selectable=SelectableBuiltins(
            pedersen=pedersen_ptr,
            range_check=txs_range_check_ptr,
            ecdsa=ecdsa_ptr,
            bitwise=bitwise_ptr,
            ec_op=ec_op_ptr,
            poseidon=poseidon_ptr,
            segment_arena=segment_arena_ptr,
            range_check96=range_check96_ptr,
            add_mod=add_mod_ptr,
            mul_mod=mul_mod_ptr,
        ),
        non_selectable=NonSelectableBuiltins(keccak=keccak_ptr, sha256=sha256_ptr),
    );

    let builtin_ptrs = &local_builtin_ptrs;
    let sha256_ptr_start = builtin_ptrs.non_selectable.sha256;

    // Execute transactions.
    local n_txs = nondet %{ len(block_input.transactions) %};
    %{
        vm_enter_scope({
            '__deprecated_class_hashes': __deprecated_class_hashes,
            'transactions': iter(block_input.transactions),
            'component_hashes': block_input.declared_class_hash_to_component_hashes,
            'execution_helper': execution_helper,
            'deprecated_syscall_handler': deprecated_syscall_handler,
            'syscall_handler': syscall_handler,
             '__dict_manager': __dict_manager,
        })
    %}
    execute_transactions_inner{
        builtin_ptrs=builtin_ptrs,
        contract_state_changes=contract_state_changes,
        contract_class_changes=contract_class_changes,
    }(block_context=block_context, n_txs=n_txs);
    %{ vm_exit_scope() %}

    let selectable_builtins = &builtin_ptrs.selectable;
    let pedersen_ptr = selectable_builtins.pedersen;
    let ecdsa_ptr = selectable_builtins.ecdsa;
    let bitwise_ptr = selectable_builtins.bitwise;
    let ec_op_ptr = selectable_builtins.ec_op;
    let poseidon_ptr = selectable_builtins.poseidon;
    let range_check96_ptr = selectable_builtins.range_check96;
    let add_mod_ptr = selectable_builtins.add_mod;
    let mul_mod_ptr = selectable_builtins.mul_mod;
    let keccak_ptr = builtin_ptrs.non_selectable.keccak;

    let txs_range_check_ptr = selectable_builtins.range_check;

    // Fill holes in the rc96 segment.
    %{
        rc96_ptr = ids.range_check96_ptr
        segment_size = rc96_ptr.offset
        base = rc96_ptr - segment_size

        for i in range(segment_size):
            memory.setdefault(base + i, 0)
    %}

    // Finalize the sha256 segment.
    finalize_sha256(
        sha256_ptr_start=sha256_ptr_start, sha256_ptr_end=builtin_ptrs.non_selectable.sha256
    );

    return ();
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
    contract_state_changes: DictAccess*,
    contract_class_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*, n_txs) {
    %{ print(f"execute_transactions_inner: {ids.n_txs} transactions remaining.") %}
    if (n_txs == 0) {
        return ();
    }

    alloc_locals;
    local tx_type;
    local n_resource_bounds: felt;
    local resource_bounds: ResourceBounds*;

    // Guess the current transaction's type.
    %{
        tx = next(transactions)
        assert tx.tx_type.name in ('INVOKE_FUNCTION', 'L1_HANDLER', 'DEPLOY_ACCOUNT', 'DECLARE'), (
            f"Unexpected transaction type: {tx.type.name}."
        )

        tx_type_bytes = tx.tx_type.name.encode("ascii")
        ids.tx_type = int.from_bytes(tx_type_bytes, "big")
        execution_helper.os_logger.enter_tx(
            tx=tx,
            n_steps=current_step,
            builtin_ptrs=ids.builtin_ptrs,
            range_check_ptr=ids.range_check_ptr,
        )

        # Prepare a short callable to save code duplication.
        exit_tx = lambda: execution_helper.os_logger.exit_tx(
            n_steps=current_step,
            builtin_ptrs=ids.builtin_ptrs,
            range_check_ptr=ids.range_check_ptr,
        )
    %}

    if (tx_type == 'INVOKE_FUNCTION') {
        // Handle the invoke-function transaction.
        execute_invoke_function_transaction(block_context=block_context);
        %{ exit_tx() %}
        return execute_transactions_inner(block_context=block_context, n_txs=n_txs - 1);
    }
    if (tx_type == 'L1_HANDLER') {
        // Handle the L1-handler transaction.
        execute_l1_handler_transaction(block_context=block_context);
        %{ exit_tx() %}
        return execute_transactions_inner(block_context=block_context, n_txs=n_txs - 1);
    }
    if (tx_type == 'DEPLOY_ACCOUNT') {
        // Handle the deploy-account transaction.
        execute_deploy_account_transaction(block_context=block_context);
        %{ exit_tx() %}
        return execute_transactions_inner(block_context=block_context, n_txs=n_txs - 1);
    }

    assert tx_type = 'DECLARE';
    // Handle the declare transaction.
    execute_declare_transaction(block_context=block_context);
    %{ exit_tx() %}
    return execute_transactions_inner(block_context=block_context, n_txs=n_txs - 1);
}

// Represents the calldata of an ERC20 transfer.
struct TransferCallData {
    recipient: felt,
    amount: Uint256,
}

// Returns the maximum possible fee that can be charged for the transaction.
func compute_max_possible_fee(tx_info: TxInfo*) -> felt {
    tempvar resource_bounds: ResourceBounds* = tx_info.resource_bounds_start;
    let n_resource_bounds = (tx_info.resource_bounds_end - resource_bounds) / ResourceBounds.SIZE;

    // Only V3 transactions with all resource bounds are supported.
    assert tx_info.version = 3;
    assert n_resource_bounds = 3;

    tempvar l1_gas_bounds: ResourceBounds = resource_bounds[L1_GAS_INDEX];
    tempvar l2_gas_bounds: ResourceBounds = resource_bounds[L2_GAS_INDEX];
    tempvar l1_data_gas_bounds = resource_bounds[L1_DATA_GAS_INDEX];

    return l1_gas_bounds.max_amount * l1_gas_bounds.max_price_per_unit + l2_gas_bounds.max_amount *
        (l2_gas_bounds.max_price_per_unit + tx_info.tip) + l1_data_gas_bounds.max_amount *
        l1_data_gas_bounds.max_price_per_unit;
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
    contract_state_changes: DictAccess*,
    contract_class_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*, tx_execution_context: ExecutionContext*) {
    alloc_locals;

    local tx_info: TxInfo* = tx_execution_context.execution_info.tx_info;
    let max_fee = compute_max_possible_fee(tx_info=tx_info);

    if (max_fee == 0) {
        return ();
    }

    local calldata: TransferCallData = TransferCallData(
        recipient=block_context.block_info_for_execute.sequencer_address,
        amount=Uint256(low=nondet %{ execution_helper.tx_execution_info.actual_fee %}, high=0),
    );

    // Verify that the charged amount is not larger than the transaction's max_fee field.
    assert_nn_le(calldata.amount.low, max_fee);

    local fee_token_address = block_context.starknet_os_config.fee_token_address;
    let (fee_state_entry: StateEntry*) = dict_read{dict_ptr=contract_state_changes}(
        key=fee_token_address
    );
    let (__fp__, _) = get_fp_and_pc();
    // Use block_info directly from block_context, so that charge_fee will always run in
    // execute-mode rather than validate-mode.
    local execution_context: ExecutionContext = ExecutionContext(
        entry_point_type=ENTRY_POINT_TYPE_EXTERNAL,
        class_hash=fee_state_entry.class_hash,
        calldata_size=TransferCallData.SIZE,
        calldata=&calldata,
        execution_info=new ExecutionInfo(
            block_info=block_context.block_info_for_execute,
            tx_info=tx_info,
            caller_address=tx_info.account_contract_address,
            contract_address=fee_token_address,
            selector=TRANSFER_ENTRY_POINT_SELECTOR,
        ),
        deprecated_tx_info=tx_execution_context.deprecated_tx_info,
    );

    let remaining_gas = DEFAULT_INITIAL_GAS_COST;
    non_reverting_select_execute_entry_point_func{remaining_gas=remaining_gas}(
        block_context=block_context, execution_context=&execution_context
    );
    return ();
}

// Guesses and returns the account transaction common fields.
//
// The account transaction should be passed in the hint variable 'tx'.
func get_account_tx_common_fields(
    block_context: BlockContext*, tx_hash_prefix: felt, sender_address: felt
) -> CommonTxFields* {
    tempvar resource_bounds: ResourceBounds*;
    %{
        from src.starkware.starknet.core.os.transaction_hash.transaction_hash import (
            create_resource_bounds_list,
        )
        assert len(tx.resource_bounds) == 3, (
            "Only transactions with 3 resource bounds are supported. "
            f"Got {len(tx.resource_bounds)} resource bounds."
        )
        ids.resource_bounds = segments.gen_arg(create_resource_bounds_list(tx.resource_bounds))
    %}
    tempvar common_tx_fields = new CommonTxFields(
        tx_hash_prefix=tx_hash_prefix,
        version=3,
        sender_address=sender_address,
        chain_id=block_context.starknet_os_config.chain_id,
        nonce=nondet %{ tx.nonce %},
        tip=nondet %{ tx.tip %},
        n_resource_bounds=3,
        resource_bounds=resource_bounds,
        paymaster_data_length=nondet %{ len(tx.paymaster_data) %},
        paymaster_data=cast(nondet %{ segments.gen_arg(tx.paymaster_data) %}, felt*),
        nonce_data_availability_mode=nondet %{ tx.nonce_data_availability_mode %},
        fee_data_availability_mode=nondet %{ tx.fee_data_availability_mode %},
    );
    return common_tx_fields;
}

// Fills the transaction info and deprecated transaction info structs for account transactions.
//
// The account transaction should be passed in the hint variable 'tx'.
func fill_account_tx_info{range_check_ptr}(
    transaction_hash: felt,
    common_tx_fields: CommonTxFields*,
    account_deployment_data_size: felt,
    account_deployment_data: felt*,
    tx_info_dst: TxInfo*,
    deprecated_tx_info_dst: DeprecatedTxInfo*,
) {
    alloc_locals;

    local signature_start: felt*;
    local signature_len: felt;
    %{
        ids.signature_start = segments.gen_arg(arg=tx.signature)
        ids.signature_len = len(tx.signature)
    %}
    assert_nn_le(signature_len, SIERRA_ARRAY_LEN_BOUND - 1);
    assert [tx_info_dst] = TxInfo(
        version=common_tx_fields.version,
        account_contract_address=common_tx_fields.sender_address,
        max_fee=0,
        signature_start=signature_start,
        signature_end=&signature_start[signature_len],
        transaction_hash=transaction_hash,
        chain_id=common_tx_fields.chain_id,
        nonce=common_tx_fields.nonce,
        resource_bounds_start=common_tx_fields.resource_bounds,
        resource_bounds_end=&common_tx_fields.resource_bounds[common_tx_fields.n_resource_bounds],
        tip=common_tx_fields.tip,
        paymaster_data_start=common_tx_fields.paymaster_data,
        paymaster_data_end=&common_tx_fields.paymaster_data[common_tx_fields.paymaster_data_length],
        nonce_data_availability_mode=common_tx_fields.nonce_data_availability_mode,
        fee_data_availability_mode=common_tx_fields.fee_data_availability_mode,
        account_deployment_data_start=account_deployment_data,
        account_deployment_data_end=&account_deployment_data[account_deployment_data_size],
    );
    fill_deprecated_tx_info(tx_info=tx_info_dst, dst=deprecated_tx_info_dst);
    assert_deprecated_tx_fields_consistency(tx_info=tx_info_dst);
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
    contract_state_changes: DictAccess*,
    contract_class_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*) {
    alloc_locals;

    let (local tx_execution_context: ExecutionContext*) = get_invoke_tx_execution_context(
        block_context=block_context,
        entry_point_type=ENTRY_POINT_TYPE_EXTERNAL,
        entry_point_selector=EXECUTE_ENTRY_POINT_SELECTOR,
    );
    local tx_execution_info: ExecutionInfo* = tx_execution_context.execution_info;

    // Guess transaction fields.
    // The version validation is done in `compute_invoke_transaction_hash()`.
    let common_tx_fields = get_account_tx_common_fields(
        block_context=block_context,
        tx_hash_prefix=INVOKE_HASH_PREFIX,
        sender_address=tx_execution_info.contract_address,
    );
    local account_deployment_data_size = nondet %{ len(tx.account_deployment_data) %};
    local account_deployment_data: felt* = cast(
        nondet %{ segments.gen_arg(tx.account_deployment_data) %}, felt*
    );
    let poseidon_ptr = builtin_ptrs.selectable.poseidon;
    with poseidon_ptr {
        let transaction_hash = compute_invoke_transaction_hash(
            common_fields=common_tx_fields,
            execution_context=tx_execution_context,
            account_deployment_data_size=account_deployment_data_size,
            account_deployment_data=account_deployment_data,
        );
    }
    update_poseidon_in_builtin_ptrs(poseidon_ptr=poseidon_ptr);

    %{
        assert ids.transaction_hash == tx.hash_value, (
            "Computed transaction_hash is inconsistent with the hash in the transaction. "
            f"Computed hash = {ids.transaction_hash}, Expected hash = {tx.hash_value}.")
    %}

    // Write the transaction info and complete the ExecutionInfo struct.
    tempvar tx_info = tx_execution_info.tx_info;
    fill_account_tx_info(
        transaction_hash=transaction_hash,
        common_tx_fields=common_tx_fields,
        account_deployment_data_size=account_deployment_data_size,
        account_deployment_data=account_deployment_data,
        tx_info_dst=tx_info,
        deprecated_tx_info_dst=tx_execution_context.deprecated_tx_info,
    );

    check_and_increment_nonce(tx_info=tx_info);

    %{ execution_helper.start_tx() %}

    let initial_user_gas_bound = get_initial_user_gas_bound(common_tx_fields=common_tx_fields);
    let remaining_gas = initial_user_gas_bound;

    // Validate.
    with remaining_gas {
        cap_remaining_gas(max_gas=VALIDATE_MAX_SIERRA_GAS);
        let pre_validate_gas = remaining_gas;
        run_validate(block_context=block_context, tx_execution_context=tx_execution_context);
    }
    let validate_gas_consumed = pre_validate_gas - remaining_gas;
    tempvar remaining_gas = initial_user_gas_bound - validate_gas_consumed;

    let updated_tx_execution_context = update_class_hash_in_execution_context(
        execution_context=tx_execution_context
    );

    if (nondet %{ execution_helper.tx_execution_info.is_reverted %} == 0) {
        // Execute only non-reverted transactions.
        with remaining_gas {
            cap_remaining_gas(max_gas=EXECUTE_MAX_SIERRA_GAS);
            non_reverting_select_execute_entry_point_func(
                block_context=block_context, execution_context=updated_tx_execution_context
            );
        }
    } else {
        // Align the stack with the `if` branch to avoid revoked references.
        tempvar range_check_ptr = range_check_ptr;
        tempvar remaining_gas = remaining_gas;
        tempvar builtin_ptrs = builtin_ptrs;
        tempvar contract_state_changes = contract_state_changes;
        tempvar contract_class_changes = contract_class_changes;
        tempvar outputs = outputs;
        tempvar _dummy_return_value: non_reverting_select_execute_entry_point_func.Return;
    }

    // Charge fee.
    charge_fee(block_context=block_context, tx_execution_context=updated_tx_execution_context);

    %{ execution_helper.end_tx() %}

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
    contract_state_changes: DictAccess*,
    contract_class_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*) {
    alloc_locals;

    let (local tx_execution_context: ExecutionContext*) = get_invoke_tx_execution_context(
        block_context=block_context,
        entry_point_type=ENTRY_POINT_TYPE_L1_HANDLER,
        entry_point_selector=nondet %{ tx.entry_point_selector %},
    );
    local tx_execution_info: ExecutionInfo* = tx_execution_context.execution_info;

    local nonce = nondet %{ tx.nonce %};
    local chain_id = block_context.starknet_os_config.chain_id;

    let pedersen_ptr = builtin_ptrs.selectable.pedersen;
    with pedersen_ptr {
        let transaction_hash = compute_l1_handler_transaction_hash(
            execution_context=tx_execution_context, chain_id=chain_id, nonce=nonce
        );
    }
    update_pedersen_in_builtin_ptrs(pedersen_ptr=pedersen_ptr);

    %{
        assert ids.transaction_hash == tx.hash_value, (
            "Computed transaction_hash is inconsistent with the hash in the transaction. "
            f"Computed hash = {ids.transaction_hash}, Expected hash = {tx.hash_value}.")
    %}

    // Write the transaction info and complete the ExecutionInfo struct.
    tempvar tx_info = tx_execution_info.tx_info;
    assert [tx_info] = TxInfo(
        version=L1_HANDLER_VERSION,
        account_contract_address=tx_execution_info.contract_address,
        max_fee=0,
        signature_start=cast(0, felt*),
        signature_end=cast(0, felt*),
        transaction_hash=transaction_hash,
        chain_id=chain_id,
        nonce=nonce,
        resource_bounds_start=cast(0, ResourceBounds*),
        resource_bounds_end=cast(0, ResourceBounds*),
        tip=0,
        paymaster_data_start=cast(0, felt*),
        paymaster_data_end=cast(0, felt*),
        nonce_data_availability_mode=0,
        fee_data_availability_mode=0,
        account_deployment_data_start=cast(0, felt*),
        account_deployment_data_end=cast(0, felt*),
    );
    fill_deprecated_tx_info(tx_info=tx_info, dst=tx_execution_context.deprecated_tx_info);
    assert_deprecated_tx_fields_consistency(tx_info=tx_info);

    // Consume L1-to-L2 message.
    consume_l1_to_l2_message(execution_context=tx_execution_context, nonce=nonce);
    %{ execution_helper.start_tx() %}
    let remaining_gas = L1_HANDLER_L2_GAS_MAX_AMOUNT;
    non_reverting_select_execute_entry_point_func{remaining_gas=remaining_gas}(
        block_context=block_context, execution_context=tx_execution_context
    );

    %{ execution_helper.end_tx() %}
    return ();
}

// Guess the execution context of an invoke transaction (either invoke function or L1 handler).
// Leaves 'execution_info.tx_info' and 'deprecated_tx_info' empty - should be
// filled later on.
func get_invoke_tx_execution_context{range_check_ptr, contract_state_changes: DictAccess*}(
    block_context: BlockContext*, entry_point_type: felt, entry_point_selector: felt
) -> (tx_execution_context: ExecutionContext*) {
    alloc_locals;
    local contract_address;
    %{
        from starkware.starknet.business_logic.transaction.deprecated_objects import (
            InternalL1Handler,
        )
        ids.contract_address = (
            tx.contract_address if isinstance(tx, InternalL1Handler) else tx.sender_address
        )
    %}
    let (state_entry: StateEntry*) = dict_read{dict_ptr=contract_state_changes}(
        key=contract_address
    );
    local tx_execution_context: ExecutionContext* = new ExecutionContext(
        entry_point_type=entry_point_type,
        class_hash=state_entry.class_hash,
        calldata_size=nondet %{ len(tx.calldata) %},
        calldata=cast(nondet %{ segments.gen_arg(tx.calldata) %}, felt*),
        execution_info=new ExecutionInfo(
            block_info=block_context.block_info_for_execute,
            tx_info=cast(nondet %{ segments.add() %}, TxInfo*),
            caller_address=ORIGIN_ADDRESS,
            contract_address=contract_address,
            selector=entry_point_selector,
        ),
        deprecated_tx_info=cast(nondet %{ segments.add() %}, DeprecatedTxInfo*),
    );
    assert_nn_le(tx_execution_context.calldata_size, SIERRA_ARRAY_LEN_BOUND - 1);

    return (tx_execution_context=tx_execution_context);
}

// Adds 'tx' with the given 'nonce' to 'outputs.messages_to_l2'.
func consume_l1_to_l2_message{outputs: OsCarriedOutputs*}(
    execution_context: ExecutionContext*, nonce: felt
) {
    assert_not_zero(execution_context.calldata_size);
    // The payload is the calldata without the from_address argument (which is the first).
    let payload: felt* = execution_context.calldata + 1;
    tempvar payload_size = execution_context.calldata_size - 1;

    tempvar execution_info = execution_context.execution_info;

    // Write the given transaction to the output.
    assert [outputs.messages_to_l2] = MessageToL2Header(
        from_address=[execution_context.calldata],
        to_address=execution_info.contract_address,
        nonce=nonce,
        selector=execution_info.selector,
        payload_size=payload_size,
    );

    let message_payload = cast(outputs.messages_to_l2 + MessageToL2Header.SIZE, felt*);
    memcpy(dst=message_payload, src=payload, len=payload_size);

    let (outputs) = os_carried_outputs_new(
        messages_to_l1=outputs.messages_to_l1,
        messages_to_l2=outputs.messages_to_l2 + MessageToL2Header.SIZE +
        outputs.messages_to_l2.payload_size,
    );
    return ();
}

// Prepares a constructor execution context based on the 'tx' hint variable.
// Leaves 'execution_info.tx_info' and 'deprecated_tx_info' empty - should be filled later on.
func prepare_constructor_execution_context{range_check_ptr, builtin_ptrs: BuiltinPointers*}(
    block_info: BlockInfo*
) -> (constructor_execution_context: ExecutionContext*, salt: felt) {
    alloc_locals;

    local contract_address_salt;
    local class_hash;
    local constructor_calldata_size;
    local constructor_calldata: felt*;
    %{
        ids.contract_address_salt = tx.contract_address_salt
        ids.class_hash = tx.class_hash
        ids.constructor_calldata_size = len(tx.constructor_calldata)
        ids.constructor_calldata = segments.gen_arg(arg=tx.constructor_calldata)
    %}
    assert_nn_le(constructor_calldata_size, SIERRA_ARRAY_LEN_BOUND - 1);

    let hash_ptr = builtin_ptrs.selectable.pedersen;
    with hash_ptr {
        let (contract_address) = get_contract_address(
            salt=contract_address_salt,
            class_hash=class_hash,
            constructor_calldata_size=constructor_calldata_size,
            constructor_calldata=constructor_calldata,
            deployer_address=0,
        );
    }
    update_pedersen_in_builtin_ptrs(pedersen_ptr=hash_ptr);

    tempvar constructor_execution_context = new ExecutionContext(
        entry_point_type=ENTRY_POINT_TYPE_CONSTRUCTOR,
        class_hash=class_hash,
        calldata_size=constructor_calldata_size,
        calldata=constructor_calldata,
        execution_info=new ExecutionInfo(
            block_info=block_info,
            tx_info=cast(nondet %{ segments.add() %}, TxInfo*),
            caller_address=ORIGIN_ADDRESS,
            contract_address=contract_address,
            selector=CONSTRUCTOR_ENTRY_POINT_SELECTOR,
        ),
        deprecated_tx_info=cast(nondet %{ segments.add() %}, DeprecatedTxInfo*),
    );

    return (
        constructor_execution_context=constructor_execution_context, salt=contract_address_salt
    );
}

func execute_deploy_account_transaction{
    range_check_ptr,
    builtin_ptrs: BuiltinPointers*,
    contract_state_changes: DictAccess*,
    contract_class_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*) {
    alloc_locals;

    // Calculate address and prepare constructor execution context.
    let (
        local constructor_execution_context: ExecutionContext*, local salt
    ) = prepare_constructor_execution_context(block_info=block_context.block_info_for_validate);
    local constructor_execution_info: ExecutionInfo* = constructor_execution_context.execution_info;
    local sender_address = constructor_execution_info.contract_address;

    // Prepare validate_deploy calldata.
    local validate_deploy_calldata_size = constructor_execution_context.calldata_size + 2;
    let (validate_deploy_calldata: felt*) = alloc();
    assert validate_deploy_calldata[0] = constructor_execution_context.class_hash;
    assert validate_deploy_calldata[1] = salt;
    memcpy(
        dst=&validate_deploy_calldata[2],
        src=constructor_execution_context.calldata,
        len=constructor_execution_context.calldata_size,
    );

    // Guess transaction fields.
    // Compute transaction hash and prepare transaction info.
    // The version validation is done in `compute_deploy_account_transaction_hash()`.
    let common_tx_fields = get_account_tx_common_fields(
        block_context=block_context,
        tx_hash_prefix=DEPLOY_ACCOUNT_HASH_PREFIX,
        sender_address=sender_address,
    );
    let poseidon_ptr = builtin_ptrs.selectable.poseidon;
    with poseidon_ptr {
        let transaction_hash = compute_deploy_account_transaction_hash(
            common_fields=common_tx_fields,
            calldata_size=validate_deploy_calldata_size,
            calldata=validate_deploy_calldata,
        );
    }
    update_poseidon_in_builtin_ptrs(poseidon_ptr=poseidon_ptr);

    %{
        assert ids.transaction_hash == tx.hash_value, (
            "Computed transaction_hash is inconsistent with the hash in the transaction. "
            f"Computed hash = {ids.transaction_hash}, Expected hash = {tx.hash_value}.")
    %}

    // Initialize and fill the transaction info structs.
    local tx_info: TxInfo* = constructor_execution_info.tx_info;
    local deprecated_tx_info: DeprecatedTxInfo* = constructor_execution_context.deprecated_tx_info;

    fill_account_tx_info(
        transaction_hash=transaction_hash,
        common_tx_fields=common_tx_fields,
        account_deployment_data_size=0,
        account_deployment_data=cast(0, felt*),
        tx_info_dst=tx_info,
        deprecated_tx_info_dst=deprecated_tx_info,
    );

    %{ execution_helper.start_tx() %}

    let initial_user_gas_bound = get_initial_user_gas_bound(common_tx_fields=common_tx_fields);
    let remaining_gas = initial_user_gas_bound;

    // Constructor.
    with remaining_gas {
        // The constructor entry point runs with a validate call context.
        cap_remaining_gas(max_gas=VALIDATE_MAX_SIERRA_GAS);
        let pre_constructor_gas = remaining_gas;
        let revert_log = init_revert_log();
        deploy_contract{revert_log=revert_log}(
            block_context=block_context, constructor_execution_context=constructor_execution_context
        );
    }
    let constructor_gas_consumed = pre_constructor_gas - remaining_gas;
    tempvar remaining_gas = initial_user_gas_bound - constructor_gas_consumed;

    // Handle nonce here since 'deploy_contract' verifies that the nonce is zeroed.
    check_and_increment_nonce(tx_info=tx_info);

    // Run the account contract's "__validate_deploy__" entry point.

    // Fetch the newest state entry, after constructor invocation.
    let (state_entry: StateEntry*) = dict_read{dict_ptr=contract_state_changes}(key=sender_address);
    // Prepare execution context.
    local validate_deploy_execution_context: ExecutionContext* = new ExecutionContext(
        entry_point_type=ENTRY_POINT_TYPE_EXTERNAL,
        class_hash=state_entry.class_hash,
        calldata_size=validate_deploy_calldata_size,
        calldata=validate_deploy_calldata,
        execution_info=new ExecutionInfo(
            block_info=block_context.block_info_for_validate,
            tx_info=tx_info,
            caller_address=constructor_execution_info.caller_address,
            contract_address=sender_address,
            selector=VALIDATE_DEPLOY_ENTRY_POINT_SELECTOR,
        ),
        deprecated_tx_info=deprecated_tx_info,
    );

    // Validate.
    with remaining_gas {
        cap_remaining_gas(max_gas=VALIDATE_MAX_SIERRA_GAS);
        // Run the entrypoint.
        let (retdata_size, retdata, is_deprecated) = non_reverting_select_execute_entry_point_func(
            block_context=block_context, execution_context=validate_deploy_execution_context
        );
    }
    if (is_deprecated == 0) {
        assert retdata_size = 1;
        assert retdata[0] = VALIDATED;
    }

    // Charge fee.
    charge_fee(block_context=block_context, tx_execution_context=validate_deploy_execution_context);

    %{ execution_helper.end_tx() %}
    return ();
}

func execute_declare_transaction{
    range_check_ptr,
    builtin_ptrs: BuiltinPointers*,
    contract_state_changes: DictAccess*,
    contract_class_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*) {
    alloc_locals;

    if (nondet %{ tx.version %} == 0) {
        %{ execution_helper.skip_tx() %}
        return ();
    }

    // Guess transaction fields.
    local sender_address;
    local class_hash_ptr: felt*;
    local compiled_class_hash;
    local account_deployment_data_size;
    local account_deployment_data: felt*;
    %{
        assert tx.version == 3, f"Unsupported declare version: {tx.version}."
        ids.sender_address = tx.sender_address
        ids.account_deployment_data_size = len(tx.account_deployment_data)
        ids.account_deployment_data = segments.gen_arg(tx.account_deployment_data)
        ids.class_hash_ptr = segments.gen_arg([tx.class_hash])
        ids.compiled_class_hash = tx.compiled_class_hash
    %}
    let common_tx_fields = get_account_tx_common_fields(
        block_context=block_context,
        tx_hash_prefix=DECLARE_HASH_PREFIX,
        sender_address=sender_address,
    );

    let poseidon_ptr = builtin_ptrs.selectable.poseidon;
    with poseidon_ptr {
        // Compute transaction hash.
        let transaction_hash = compute_declare_transaction_hash(
            common_fields=common_tx_fields,
            class_hash=[class_hash_ptr],
            compiled_class_hash=compiled_class_hash,
            account_deployment_data_size=account_deployment_data_size,
            account_deployment_data=account_deployment_data,
        );
        %{
            assert ids.transaction_hash == tx.hash_value, (
                "Computed transaction_hash is inconsistent with the hash in the transaction. "
                f"Computed hash = {ids.transaction_hash}, Expected hash = {tx.hash_value}.")
        %}

        // Ensure the given class hash is a result of a Sierra class hash calculation.
        local contract_class_component_hashes: ContractClassComponentHashes*;
        %{
            class_component_hashes = component_hashes[tx.class_hash]
            assert (
                len(class_component_hashes) == ids.ContractClassComponentHashes.SIZE
            ), "Wrong number of class component hashes."
            ids.contract_class_component_hashes = segments.gen_arg(class_component_hashes)
        %}

        let expected_class_hash = finalize_class_hash(
            contract_class_component_hashes=contract_class_component_hashes
        );
        with_attr error_message("Invalid class hash pre-image.") {
            assert [class_hash_ptr] = expected_class_hash;
        }
    }
    update_poseidon_in_builtin_ptrs(poseidon_ptr=poseidon_ptr);

    // Get the account transaction info.
    tempvar tx_info = cast(nondet %{ segments.add() %}, TxInfo*);
    tempvar deprecated_tx_info = cast(nondet %{ segments.add() %}, DeprecatedTxInfo*);
    fill_account_tx_info(
        transaction_hash=transaction_hash,
        common_tx_fields=common_tx_fields,
        account_deployment_data_size=account_deployment_data_size,
        account_deployment_data=account_deployment_data,
        tx_info_dst=tx_info,
        deprecated_tx_info_dst=deprecated_tx_info,
    );

    // Do not run validate or perform any account-related actions for declare transactions that
    // meet the following conditions.
    // This flow is used for the sequencer to bootstrap a new system.
    if (sender_address == 'BOOTSTRAP' and tx_info.nonce == 0 and tx_info.version == 3) {
        let max_possible_fee = compute_max_possible_fee(tx_info=tx_info);
        if (max_possible_fee == 0) {
            // Declare the class hash and skip the rest of the transaction.
            // Note that prev_value=0 enforces that a class may be declared only once.
            assert_not_zero(compiled_class_hash);
            dict_update{dict_ptr=contract_class_changes}(
                key=[class_hash_ptr], prev_value=0, new_value=compiled_class_hash
            );
            %{ execution_helper.skip_tx() %}
            return ();
        }
    }

    // Increment nonce.
    check_and_increment_nonce(tx_info=tx_info);

    // Prepare the validate execution context.
    let (state_entry: StateEntry*) = dict_read{dict_ptr=contract_state_changes}(key=sender_address);
    // The calldata for declare tx is the class hash.
    local validate_declare_execution_context: ExecutionContext* = new ExecutionContext(
        entry_point_type=ENTRY_POINT_TYPE_EXTERNAL,
        class_hash=state_entry.class_hash,
        calldata_size=1,
        calldata=class_hash_ptr,
        execution_info=new ExecutionInfo(
            block_info=block_context.block_info_for_validate,
            tx_info=tx_info,
            caller_address=ORIGIN_ADDRESS,
            contract_address=sender_address,
            selector=VALIDATE_DECLARE_ENTRY_POINT_SELECTOR,
        ),
        deprecated_tx_info=deprecated_tx_info,
    );

    let remaining_gas = get_initial_user_gas_bound(common_tx_fields=common_tx_fields);
    with remaining_gas {
        cap_remaining_gas(max_gas=VALIDATE_MAX_SIERRA_GAS);
        // Run the account contract's "__validate_declare__" entry point.
        %{ execution_helper.start_tx() %}
        let (retdata_size, retdata, is_deprecated) = non_reverting_select_execute_entry_point_func(
            block_context=block_context, execution_context=validate_declare_execution_context
        );
    }
    if (is_deprecated == 0) {
        assert retdata_size = 1;
        assert retdata[0] = VALIDATED;
    }

    // Declare the class hash.
    // Note that prev_value=0 enforces that a class may be declared only once.
    assert_not_zero(compiled_class_hash);
    dict_update{dict_ptr=contract_class_changes}(
        key=[class_hash_ptr], prev_value=0, new_value=compiled_class_hash
    );

    // Charge fee.
    charge_fee(
        block_context=block_context, tx_execution_context=validate_declare_execution_context
    );
    %{ execution_helper.end_tx() %}

    return ();
}
