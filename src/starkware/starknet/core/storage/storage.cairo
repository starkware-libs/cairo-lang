from starkware.cairo.common.dict_access import DictAccess

struct Storage:
end

# Reads a value from a given address in the storage.
func storage_read{storage_ptr : Storage*}(address : felt) -> (value : felt):
    let dict_ptr = cast(storage_ptr, DictAccess*)

    dict_ptr.key = address

    # Put storage in the right place for return value optimization.
    tempvar storage_ptr = storage_ptr + DictAccess.SIZE
    %{ ids.dict_ptr.prev_value = __storage.read(address=ids.dict_ptr.key) %}
    # Make sure prev_value == new_value.
    tempvar value = dict_ptr.prev_value
    dict_ptr.new_value = value

    return (value=value)
end

# Writes the given value to the given address in the storage.
func storage_write{storage_ptr : Storage*}(address : felt, value : felt):
    let dict_ptr = cast(storage_ptr, DictAccess*)

    # Note that soundness-wise it is ok to set prev_value in the hint.
    dict_ptr.key = address
    dict_ptr.new_value = value
    %{
        ids.dict_ptr.prev_value = __storage.read(address=ids.dict_ptr.key)
        __storage.write(address=ids.dict_ptr.key, value=ids.dict_ptr.new_value)
    %}

    let storage_ptr = storage_ptr + DictAccess.SIZE
    return ()
end
