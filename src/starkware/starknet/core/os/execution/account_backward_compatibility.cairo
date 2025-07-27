from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.math_cmp import is_le
from starkware.starknet.common.new_syscalls import ResourceBounds
from starkware.starknet.core.os.constants import (
    DATA_GAS_ACCOUNTS_0,
    DATA_GAS_ACCOUNTS_1,
    DATA_GAS_ACCOUNTS_2,
    DATA_GAS_ACCOUNTS_3,
    DATA_GAS_ACCOUNTS_LEN,
    L1_DATA_GAS,
    L1_DATA_GAS_INDEX,
    V1_BOUND_ACCOUNTS_CAIRO0_0,
    V1_BOUND_ACCOUNTS_CAIRO0_1,
    V1_BOUND_ACCOUNTS_CAIRO0_2,
    V1_BOUND_ACCOUNTS_CAIRO0_3,
    V1_BOUND_ACCOUNTS_CAIRO0_4,
    V1_BOUND_ACCOUNTS_CAIRO0_5,
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
    static_assert V1_BOUND_ACCOUNTS_CAIRO0_LEN == 6;
    if ((class_hash - V1_BOUND_ACCOUNTS_CAIRO0_0) *
        (class_hash - V1_BOUND_ACCOUNTS_CAIRO0_1) *
        (class_hash - V1_BOUND_ACCOUNTS_CAIRO0_2) *
        (class_hash - V1_BOUND_ACCOUNTS_CAIRO0_3) *
        (class_hash - V1_BOUND_ACCOUNTS_CAIRO0_4) *
        (class_hash - V1_BOUND_ACCOUNTS_CAIRO0_5) == 0) {
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

// Returns TRUE for the hard-coded list of class hashes for which data gas is excluded from
// their resource bounds when the `get_execution_info` syscall is called (only `L1_GAS` and
// `L2_GAS` are returned).
func should_exclude_l1_data_gas(class_hash: felt) -> felt {
    static_assert DATA_GAS_ACCOUNTS_LEN == 4;
    if ((class_hash - DATA_GAS_ACCOUNTS_0) *
        (class_hash - DATA_GAS_ACCOUNTS_1) *
        (class_hash - DATA_GAS_ACCOUNTS_2) *
        (class_hash - DATA_GAS_ACCOUNTS_3) == 0) {
        return TRUE;
    }
    return FALSE;
}

// Excludes L1 data gas of the given resource bounds list.
func exclude_data_gas_of_resource_bounds(
    resource_bounds_start: ResourceBounds*, resource_bounds_end: ResourceBounds*
) -> (resource_bounds_end: ResourceBounds*) {
    tempvar n_resource_bounds = (resource_bounds_end - resource_bounds_start) / ResourceBounds.SIZE;
    // Only the L1 handler and meta tx v0 could have a different number of resource bounds.
    // But this function is called only with tx_version == 3.
    assert n_resource_bounds = 3;
    // Sanity check - the data gas should be the last resource.
    static_assert L1_DATA_GAS_INDEX == 2;
    assert resource_bounds_start[L1_DATA_GAS_INDEX].resource = L1_DATA_GAS;
    return (resource_bounds_end=&resource_bounds_end[-1]);
}
