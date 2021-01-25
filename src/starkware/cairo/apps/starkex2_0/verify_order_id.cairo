# ***********************************************************************
# * This code is licensed under the Cairo Program License.              *
# * The license can be found in: licenses/CairoProgramLicense.txt       *
# ***********************************************************************

from starkware.cairo.apps.starkex2_0.dex_constants import (
    HASH_MESSAGE_BOUND as DEX_HASH_MESSAGE_BOUND)
from starkware.cairo.apps.starkex2_0.dex_constants import ORDER_ID_BOUND as DEX_ORDER_ID_BOUND
from starkware.cairo.apps.starkex2_0.dex_constants import RANGE_CHECK_BOUND as DEX_RANGE_CHECK_BOUND

# Verifies that the given order_id complies with the order data, encoded in the message_hash.
# The order_id is represented by the 63 most significant bits of the message_hash.
#
# Assumptions:
# * 0 <= order_id < ORDER_ID_BOUND.
func verify_order_id(range_check_ptr, message_hash, order_id) -> (range_check_ptr):
    # Copy constants to allow overriding them in the tests.
    const HASH_MESSAGE_BOUND = DEX_HASH_MESSAGE_BOUND
    const ORDER_ID_BOUND = DEX_ORDER_ID_BOUND
    const RANGE_CHECK_BOUND = DEX_RANGE_CHECK_BOUND

    # The 251-bit message_hash can be viewed as a packing of three fields:
    # +----------------+--------------------+----------------LSB-+
    # | order_id (63b) | middle_field (60b) | right_field (128b) |
    # +----------------+--------------------+--------------------+
    # .
    const ORDER_ID_SHIFT = HASH_MESSAGE_BOUND / ORDER_ID_BOUND
    const MIDDLE_FIELD_BOUND = ORDER_ID_SHIFT / RANGE_CHECK_BOUND

    # Local variables.
    alloc_locals
    local middle_field
    local right_field

    # Verify that the message_hash definition holds, i.e., that:
    # message_hash = ORDER_ID_SHIFT * order_id + RANGE_CHECK_BOUND * middle_field + right_field.
    tempvar shifted_middle_field = middle_field * RANGE_CHECK_BOUND
    tempvar packed_right_fields = shifted_middle_field + right_field
    tempvar shifted_order_id = order_id * ORDER_ID_SHIFT
    message_hash = shifted_order_id + packed_right_fields

    # Verify the message_hash structure (i.e., the size of each field), to ensure unique unpacking.
    # Note that the size of order_id is verified by performing merkle_update on the order tree.
    # Check that 0 <= right_field < RANGE_CHECK_BOUND.
    assert [range_check_ptr] = right_field
    # Check that 0 <= middle_field < MIDDLE_FIELD_BOUND.
    assert [range_check_ptr + 1] = middle_field
    assert [range_check_ptr + 2] = (MIDDLE_FIELD_BOUND - 1) - middle_field

    return (range_check_ptr=range_check_ptr + 3)
end
