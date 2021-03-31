# ***********************************************************************
# * This code is licensed under the Cairo Program License.              *
# * The license can be found in: licenses/CairoProgramLicense.txt       *
# ***********************************************************************

from starkware.cairo.apps.starkex2_0.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.apps.starkex2_0.dex_constants import PackedOrderMsg
from starkware.cairo.apps.starkex2_0.verify_order_id import verify_order_id

# Computes partial_msg_hash for the signed message of transfer and conditional transfer.
#
# If the order is a transfer (condition == 0), returns temp_partial_msg_hash. If the order is a
# conditional transfer (condition != 0), returns hash(temp_partial_msg_hash, condition).
# The returnd value is the first argument to the hash function that computes the signed message,
# i.e. - partial_msg_hash in hash(partial_msg_hash, packed_msg).
# See the documentation of verify_order_signature for more details.
func add_optional_condition_hash(temp_partial_msg_hash, condition, hash_ptr : HashBuiltin*) -> (
        partial_msg_hash, hash_ptr : HashBuiltin*):
    if condition == 0:
        return (partial_msg_hash=temp_partial_msg_hash, hash_ptr=hash_ptr)
    end

    let partial_msg_hash : HashBuiltin* = hash_ptr
    partial_msg_hash.x = temp_partial_msg_hash
    partial_msg_hash.y = condition
    return (partial_msg_hash=partial_msg_hash.result, hash_ptr=hash_ptr + HashBuiltin.SIZE)
end

# Verifies that the order was signed and that the order_id complies with the order data.
#
# The format of the signed message is as follows: hash(partial_msg_hash, packed_msg).
# packed_msg is a packed field which consists of the part of the order data that is not included in
# the partial_msg_hash, with the following structure:
# +-MSB-------------+--------------+--------------+---------------+---------------+
# | order_type (4b) | vault0 (31b) | vault1 (31b) | amount0 (63b) | amount1 (63b) |  ....
# +-----------------+--------------+--------------+---------------+---------------+
#
# +-------------+------------------------LSB-+
# | nonce (31b) | expiration_timestamp (22b) |
# +-------------+----------------------------+
#
# In case of a settlement (order_type = 0):
# partial_msg_hash := hash(token0, token1), and parameter names with '0' suffix represent sell data,
# while the ones with '1' suffix represent buy data.
#
# In case of a transfer (order_type = 1):
# partial_msg_hash := hash(token0, receiver_public_key), and parameter names with '0' suffix
# represent sender data, while the ones with '1' suffix represent receiver data (and amount1 = 0).
#
# In case of a conditional transfer (order_type = 2):
# partial_msg_hash := hash(hash(token0, receiver_public_key), condition).
#
# Assumptions:
# * order_type = 0, 1 or 2.
# * 0 <= vault0, vault1 < VAULT_SHIFT.
# * 0 <= amount0, amount1 < AMOUNT_SHIFT.
# * 0 <= nonce < NONCE_SHIFT.
# * 0 <= expiration_timestamp < EXPIRATION_TIMESTAMP_SHIFT.
func verify_order_signature(
        hash_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr : SignatureBuiltin*, public_key,
        order_type, vault0, vault1, amount0, amount1, token0, token1_or_pub_key, nonce,
        expiration_timestamp, order_id, condition) -> (
        range_check_ptr, hash_ptr : HashBuiltin*, ecdsa_ptr : SignatureBuiltin*):
    alloc_locals
    local packed_msg

    # Compute packed order message.
    assert packed_msg = ((((((order_type *
        PackedOrderMsg.VAULT_SHIFT + vault0) *
        PackedOrderMsg.VAULT_SHIFT + vault1) *
        PackedOrderMsg.AMOUNT_SHIFT + amount0) *
        PackedOrderMsg.AMOUNT_SHIFT + amount1) *
        PackedOrderMsg.NONCE_SHIFT + nonce) *
        PackedOrderMsg.EXPIRATION_TIMESTAMP_SHIFT + expiration_timestamp)

    # Compute partial_msg_hash.
    let temp_partial_msg_hash : HashBuiltin* = hash_ptr
    temp_partial_msg_hash.x = token0
    temp_partial_msg_hash.y = token1_or_pub_key

    # Call add_optional_condition_hash.
    let (partial_msg_hash, hash_ptr) = add_optional_condition_hash(
        temp_partial_msg_hash=temp_partial_msg_hash.result,
        condition=condition,
        hash_ptr=hash_ptr + HashBuiltin.SIZE)

    # Compute the message to sign on.
    local full_msg_hash : HashBuiltin* = hash_ptr
    full_msg_hash.x = partial_msg_hash
    full_msg_hash.y = packed_msg

    # Verify signature.
    let signature : SignatureBuiltin* = ecdsa_ptr
    signature.pub_key = public_key
    tempvar full_msg_hash_result = full_msg_hash.result
    signature.message = full_msg_hash_result

    # Call verify_order_id.
    let (range_check_ptr) = verify_order_id(
        range_check_ptr=range_check_ptr, message_hash=full_msg_hash_result, order_id=order_id)

    return (
        range_check_ptr=range_check_ptr,
        hash_ptr=full_msg_hash + HashBuiltin.SIZE,
        ecdsa_ptr=ecdsa_ptr + SignatureBuiltin.SIZE)
end
