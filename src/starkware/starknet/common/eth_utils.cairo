from starkware.cairo.common.math import assert_lt_felt, assert_not_zero

const ETH_ADDRESS_BOUND = 2 ** 160

func assert_valid_eth_address{range_check_ptr}(address : felt):
    with_attr error_message("Invalid Ethereum address - value is more than 160 bits"):
        assert_lt_felt(address, ETH_ADDRESS_BOUND)
    end

    with_attr error_message("Invalid Ethereum address - value is zero"):
        assert_not_zero(address)
    end
    return ()
end
