# Note that this is a dummy contract to be used in tests.

%lang starknet
%builtins pedersen range_check bitwise

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import delegate_call, delegate_l1_handler

# The address of the implementation contract.
@storage_var
func impl_address() -> (address : felt):
end

@external
func set_implementation_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        impl_address_ : felt):
    impl_address.write(value=impl_address_)
    return ()
end

@external
@raw_input
@raw_output
func __default__{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        selector : felt, calldata_size : felt, calldata : felt*) -> (
        retdata_size : felt, retdata : felt*):
    let (address) = impl_address.read()

    let (retdata_size : felt, retdata : felt*) = delegate_call(
        contract_address=address,
        function_selector=selector,
        calldata_size=calldata_size,
        calldata=calldata)
    return (retdata_size=retdata_size, retdata=retdata)
end

@l1_handler
@raw_input
func __l1_default__{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        selector : felt, calldata_size : felt, calldata : felt*):
    let (address) = impl_address.read()

    delegate_l1_handler(
        contract_address=address,
        function_selector=selector,
        calldata_size=calldata_size,
        calldata=calldata)
    return ()
end
