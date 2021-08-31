%lang starknet
%builtins range_check

from starkware.starknet.common.storage import Storage, storage_read, storage_write

@external
func increase_value{storage_ptr : Storage*}(address : felt, value : felt):
    let (res) = storage_read(address=address)
    return storage_write(address=address, value=res + value)
end

@external
func get_value{storage_ptr : Storage*}(address : felt) -> (res : felt):
    return storage_read(address=address)
end

@external
func takes_array{storage_ptr : Storage*}(a_len : felt, a : felt*) -> (res):
    let res = a_len + a[0] + a[1]
    return (res=res)
end
