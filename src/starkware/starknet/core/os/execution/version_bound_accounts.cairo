from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.math_cmp import is_le
from starkware.starknet.core.os.constants import (
    V1_BOUND_ACCOUNTS_CAIRO0_0,
    V1_BOUND_ACCOUNTS_CAIRO0_1,
    V1_BOUND_ACCOUNTS_CAIRO0_2,
    V1_BOUND_ACCOUNTS_CAIRO0_3,
    V1_BOUND_ACCOUNTS_CAIRO0_LEN,
    V1_BOUND_ACCOUNTS_CAIRO1_0,
    V1_BOUND_ACCOUNTS_CAIRO1_1,
    V1_BOUND_ACCOUNTS_CAIRO1_2,
    V1_BOUND_ACCOUNTS_CAIRO1_3,
    V1_BOUND_ACCOUNTS_CAIRO1_4,
    V1_BOUND_ACCOUNTS_CAIRO1_5,
    V1_BOUND_ACCOUNTS_CAIRO1_6,
    V1_BOUND_ACCOUNTS_CAIRO1_LEN,
    V1_BOUND_ACCOUNTS_MAX_TIP,
)

// Returns TRUE for the hard-coded list of CairoZero class hashes that are version-bound to v1
// transactions.
func is_v1_bound_account_cairo0(class_hash: felt) -> felt {
    static_assert V1_BOUND_ACCOUNTS_CAIRO0_LEN == 4;
    if ((class_hash - V1_BOUND_ACCOUNTS_CAIRO0_0) *
        (class_hash - V1_BOUND_ACCOUNTS_CAIRO0_1) *
        (class_hash - V1_BOUND_ACCOUNTS_CAIRO0_2) *
        (class_hash - V1_BOUND_ACCOUNTS_CAIRO0_3) == 0) {
        return TRUE;
    }
    return FALSE;
}

// Returns TRUE for the hard-coded list of Cairo1 class hashes that are version-bound to v1
// transactions.
func is_v1_bound_account_cairo1(class_hash: felt) -> felt {
    static_assert V1_BOUND_ACCOUNTS_CAIRO1_LEN == 7;
    if ((class_hash - V1_BOUND_ACCOUNTS_CAIRO1_0) *
        (class_hash - V1_BOUND_ACCOUNTS_CAIRO1_1) *
        (class_hash - V1_BOUND_ACCOUNTS_CAIRO1_2) *
        (class_hash - V1_BOUND_ACCOUNTS_CAIRO1_3) *
        (class_hash - V1_BOUND_ACCOUNTS_CAIRO1_4) *
        (class_hash - V1_BOUND_ACCOUNTS_CAIRO1_5) *
        (class_hash - V1_BOUND_ACCOUNTS_CAIRO1_6) == 0) {
        return TRUE;
    }
    return FALSE;
}

func check_tip_for_v1_bound_accounts{range_check_ptr}(tip: felt) -> felt {
    return is_le(tip, V1_BOUND_ACCOUNTS_MAX_TIP);
}
