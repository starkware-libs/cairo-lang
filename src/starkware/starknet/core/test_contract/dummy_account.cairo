# A dummy account contract without any validations.

%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import call_contract

@external
@raw_output
func __execute__{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        contract_address, selector : felt, calldata_len : felt, calldata : felt*) -> (
        retdata_size : felt, retdata : felt*):
    let (retdata_size : felt, retdata : felt*) = call_contract(
        contract_address=contract_address,
        function_selector=selector,
        calldata_size=calldata_len,
        calldata=calldata)
    return (retdata_size=retdata_size, retdata=retdata)
end
