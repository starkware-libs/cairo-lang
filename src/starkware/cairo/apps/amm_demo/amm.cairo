%builtins output pedersen range_check

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.dict import dict_new, dict_squash, dict_update
from starkware.cairo.common.dict_access import DictAccess
from starkware.cairo.common.hash import pedersen_hash
from starkware.cairo.common.math import assert_nn_le, unsigned_div_rem
from starkware.cairo.common.registers import get_fp_and_pc
from starkware.cairo.common.small_merkle_tree import small_merkle_tree

struct Account:
    member public_key : felt = 0
    member token_a_balance : felt = 1
    member token_b_balance : felt = 2
    const SIZE = 3
end

# The maximum amount of each token that belongs to the AMM.
const MAX_BALANCE = %[ 2**64 - 1 %]

struct AmmState:
    # A dictionary that tracks the accounts' state.
    member account_dict_start : DictAccess* = 0
    member account_dict_end : DictAccess* = 1
    # The amount of the tokens currently in the AMM.
    # Must be in the range [0, MAX_BALANCE].
    member token_a_balance : felt = 2
    member token_b_balance : felt = 3
    const SIZE = 4
end

func modify_account(range_check_ptr, state : AmmState, account_id, diff_a, diff_b) -> (
        range_check_ptr, state : AmmState, key):
    alloc_locals
    local old_account : Account*
    %{
        # Retrieve the pointer to the current state of the
        # account using the dict manager (see dict.cairo).
        ids.old_account = __dict_manager.get_dict(
            ids.state.account_dict_end)[ids.account_id]
    %}

    # Compute the new account values.
    tempvar new_token_a_balance = (
        old_account.token_a_balance + diff_a)
    tempvar new_token_b_balance = (
        old_account.token_b_balance + diff_b)

    # Verify that the new balances are positive.
    let (range_check_ptr) = assert_nn_le(range_check_ptr, new_token_a_balance, MAX_BALANCE)
    let (range_check_ptr) = assert_nn_le(range_check_ptr, new_token_b_balance, MAX_BALANCE)

    # Create a new Account instance.
    local new_account : Account
    assert new_account.public_key = old_account.public_key
    assert new_account.token_a_balance = new_token_a_balance
    assert new_account.token_b_balance = new_token_b_balance

    # Perform the account update.
    let (__fp__, _) = get_fp_and_pc()
    let (dict_ptr) = dict_update(
        dict_ptr=state.account_dict_end,
        key=account_id,
        prev_value=cast(old_account, felt),
        new_value=cast(&new_account, felt))

    # Construct and return the new state.
    local new_state : AmmState
    assert new_state.account_dict_start = (
        state.account_dict_start)
    assert new_state.account_dict_end = dict_ptr
    assert new_state.token_a_balance = state.token_a_balance
    assert new_state.token_b_balance = state.token_b_balance

    return (range_check_ptr=range_check_ptr, state=new_state, key=old_account.public_key)
end

# Represents a swap transaction between a user and the AMM.
struct SwapTransaction:
    member account_id = 0
    member token_a_amount = 1
    const SIZE = 2
end

func swap(range_check_ptr, state : AmmState, transaction : SwapTransaction*) -> (
        range_check_ptr, state : AmmState):
    alloc_locals

    tempvar a = transaction.token_a_amount
    tempvar x = state.token_a_balance
    tempvar y = state.token_b_balance

    # Check that a is in range.
    let (range_check_ptr) = assert_nn_le(range_check_ptr, a, MAX_BALANCE)

    # Compute the amount of token_b the user will get:
    #   b = (y * a) / (x + a).
    let (range_check_ptr, b, _) = unsigned_div_rem(range_check_ptr, y * a, x + a)
    # Make sure that b is also in range.
    let (range_check_ptr) = assert_nn_le(range_check_ptr, b, MAX_BALANCE)

    # Update the user's account.
    let (range_check_ptr, state, key) = modify_account(
        range_check_ptr=range_check_ptr,
        state=state,
        account_id=transaction.account_id,
        diff_a=-a,
        diff_b=b)

    # Here you should verify the user has signed on a message
    # specifying that they would like to sell 'a' tokens of
    # type token_a. You should use the public key returned by
    # modify_account().

    # Compute the new balances of the AMM and make sure they
    # are in range.
    tempvar new_x = x + a
    tempvar new_y = y - b
    let (range_check_ptr) = assert_nn_le(range_check_ptr, new_x, MAX_BALANCE)
    let (range_check_ptr) = assert_nn_le(range_check_ptr, new_y, MAX_BALANCE)

    # Update the state.
    local new_state : AmmState
    assert new_state.account_dict_start = (
        state.account_dict_start)
    assert new_state.account_dict_end = state.account_dict_end
    assert new_state.token_a_balance = new_x
    assert new_state.token_b_balance = new_y

    %{
        # Print the transaction values using a hint, for
        # debugging purposes.
        print(
            f'Swap: Account {ids.transaction.account_id} '
            f'gave {ids.a} tokens of type token_a and '
            f'received {ids.b} tokens of type token_b.')
    %}

    return (range_check_ptr=range_check_ptr, state=new_state)
end

func transaction_loop(
        range_check_ptr, state : AmmState, transactions : SwapTransaction**, n_transactions) -> (
        range_check_ptr, state : AmmState):
    if n_transactions == 0:
        return (range_check_ptr=range_check_ptr, state=state)
    end

    let first_transaction : SwapTransaction* = [transactions]
    let (range_check_ptr, state) = swap(
        range_check_ptr=range_check_ptr, state=state, transaction=first_transaction)

    transaction_loop(
        range_check_ptr=range_check_ptr,
        state=state,
        transactions=transactions + 1,
        n_transactions=n_transactions - 1)
    return (...)
end

# Returns a hash committing to the account's state using the
# following formula:
#   H(H(public_key, token_a_balance), token_b_balance).
# where H is the Pedersen hash function.
func hash_account(pedersen_ptr : HashBuiltin*, account : Account*) -> (
        pedersen_ptr : HashBuiltin*, res : felt):
    let res = account.public_key
    let (pedersen_ptr, res) = pedersen_hash(pedersen_ptr, res, account.token_a_balance)
    let (pedersen_ptr, res) = pedersen_hash(pedersen_ptr, res, account.token_b_balance)
    return (pedersen_ptr=pedersen_ptr, res=res)
end

# For each entry in the input dict (represented by dict_start
# and dict_end) write an entry to the output dict (represented by
# hash_dict_start and hash_dict_end) after applying hash_account
# on prev_value and new_value and keeping the same key.
func hash_dict_values(
        pedersen_ptr : HashBuiltin*, dict_start : DictAccess*, dict_end : DictAccess*,
        hash_dict_start : DictAccess*) -> (
        pedersen_ptr : HashBuiltin*, hash_dict_end : DictAccess*):
    if dict_start == dict_end:
        return (pedersen_ptr=pedersen_ptr, hash_dict_end=hash_dict_start)
    end

    # Compute the hash of the account before and after the
    # change.
    let (pedersen_ptr, prev_hash) = hash_account(
        pedersen_ptr, account=cast(dict_start.prev_value, Account*))
    let (pedersen_ptr, new_hash) = hash_account(
        pedersen_ptr, account=cast(dict_start.new_value, Account*))

    # Add an entry to the output dict.
    let (hash_dict_start) = dict_update(
        dict_ptr=hash_dict_start, key=dict_start.key, prev_value=prev_hash, new_value=new_hash)
    hash_dict_values(
        pedersen_ptr=pedersen_ptr,
        dict_start=dict_start + DictAccess.SIZE,
        dict_end=dict_end,
        hash_dict_start=hash_dict_start)
    return (...)
end

const LOG_N_ACCOUNTS = 10

# Computes the Merkle roots before and after the batch.
# Hint argument: initial_account_dict should be a dictionary
# from account_id to an address in memory of the Account struct.
func compute_merkle_roots(pedersen_ptr : HashBuiltin*, range_check_ptr, state : AmmState) -> (
        pedersen_ptr : HashBuiltin*, range_check_ptr, root_before, root_after):
    alloc_locals

    # Squash the account dictionary.
    let (local range_check_ptr, squashed_dict_start, squashed_dict_end) = dict_squash(
        range_check_ptr=range_check_ptr,
        dict_accesses_start=state.account_dict_start,
        dict_accesses_end=state.account_dict_end)

    # Hash the dict values.
    %{
        from starkware.crypto.signature.signature import pedersen_hash

        initial_dict = {}
        for account_id, account in initial_account_dict.items():
            public_key = memory[
                account + ids.Account.public_key]
            token_a_balance = memory[
                account + ids.Account.token_a_balance]
            token_b_balance = memory[
                account + ids.Account.token_b_balance]
            initial_dict[account_id] = pedersen_hash(
                pedersen_hash(public_key, token_a_balance),
                token_b_balance)
    %}
    let (local hash_dict_start : DictAccess*) = dict_new()
    let (pedersen_ptr, hash_dict_end) = hash_dict_values(
        pedersen_ptr=pedersen_ptr,
        dict_start=squashed_dict_start,
        dict_end=squashed_dict_end,
        hash_dict_start=hash_dict_start)

    # Compute the two Merkle roots.
    let (pedersen_ptr, root_before, root_after) = small_merkle_tree(
        hash_ptr=pedersen_ptr,
        squashed_dict_start=hash_dict_start,
        squashed_dict_end=hash_dict_end,
        height=LOG_N_ACCOUNTS)

    return (
        pedersen_ptr=pedersen_ptr,
        range_check_ptr=range_check_ptr,
        root_before=root_before,
        root_after=root_after)
end

func get_transactions() -> (transactions : SwapTransaction**, n_transactions : felt):
    alloc_locals
    local transactions : SwapTransaction**
    local n_transactions : felt
    %{
        transactions = [
            [
                transaction['account_id'],
                transaction['token_a_amount'],
            ]
            for transaction in program_input['transactions']
        ]
        ids.transactions = segments.gen_arg(transactions)
        ids.n_transactions = len(transactions)
    %}
    return (transactions=transactions, n_transactions=n_transactions)
end

func get_account_dict() -> (account_dict : DictAccess*):
    alloc_locals
    %{
        account = program_input['accounts']
        initial_dict = {
            int(account_id_str): segments.gen_arg([
                int(info['public_key'], 16),
                info['token_a_balance'],
                info['token_b_balance'],
            ])
            for account_id_str, info in account.items()
        }

        # Save a copy initial account dict for
        # compute_merkle_roots.
        initial_account_dict = dict(initial_dict)
    %}

    # Initialize the account dictionary.
    let (account_dict) = dict_new()
    return (account_dict=account_dict)
end

# The output of the AMM program.
struct AmmBatchOutput:
    # The balances of the AMM before applying the batch.
    member token_a_before : felt = 0
    member token_b_before : felt = 1
    # The balances of the AMM after applying the batch.
    member token_a_after : felt = 2
    member token_b_after : felt = 3
    # The account Merkle roots before and after applying
    # the batch.
    member account_root_before : felt = 4
    member account_root_after : felt = 5
    const SIZE = 6
end

func main(output_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr) -> (
        output_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr):
    alloc_locals

    # Create the initial state.
    local state : AmmState
    %{
        # Initialize the balances using a hint.
        # Later we will output them to the output struct,
        # which will allow the verifier to check that they
        # are indeed valid.
        ids.state.token_a_balance = \
            program_input['token_a_balance']
        ids.state.token_b_balance = \
            program_input['token_b_balance']
    %}

    let (account_dict) = get_account_dict()
    assert state.account_dict_start = account_dict
    assert state.account_dict_end = account_dict

    # Output the AMM's balances before applying the batch.
    let output = cast(output_ptr, AmmBatchOutput*)
    let output_ptr = output_ptr + AmmBatchOutput.SIZE

    assert output.token_a_before = state.token_a_balance
    assert output.token_b_before = state.token_b_balance

    # Execute the transactions.
    let (transactions, n_transactions) = get_transactions()
    let (range_check_ptr, state : AmmState) = transaction_loop(
        range_check_ptr=range_check_ptr,
        state=state,
        transactions=transactions,
        n_transactions=n_transactions)

    # Output the AMM's balances after applying the batch.
    assert output.token_a_after = state.token_a_balance
    assert output.token_b_after = state.token_b_balance

    # Write the Merkle roots to the output.
    let (pedersen_ptr, range_check_ptr, root_before, root_after) = compute_merkle_roots(
        pedersen_ptr=pedersen_ptr, range_check_ptr=range_check_ptr, state=state)
    assert output.account_root_before = root_before
    assert output.account_root_after = root_after

    return (output_ptr=output_ptr, pedersen_ptr=pedersen_ptr, range_check_ptr=range_check_ptr)
end
