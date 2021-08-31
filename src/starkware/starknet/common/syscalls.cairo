from starkware.starknet.common.storage import Storage

const SEND_MESSAGE_TO_L1_SELECTOR = %[int.from_bytes(b'SendMessageToL1', 'big')%]

# Describes the SendMessageToL1 system call format.
struct SendMessageToL1SysCall:
    member selector : felt
    member to_address : felt
    member payload_size : felt
    member payload_ptr : felt*
end

const CALL_CONTRACT_SELECTOR = %[int.from_bytes(b'CallContract', 'big')%]

# Describes the CallContract system call format.
struct CallContractRequest:
    # The system call selector (= CALL_CONTRACT_SELECTOR).
    member selector : felt
    # The address of the L2 contract to call.
    member contract_address : felt
    # The selector of the function to call.
    member function_selector : felt
    # The size of the calldata.
    member calldata_size : felt
    # The calldata.
    member calldata : felt*

    # The storage pointer before the syscall.
    member storage_ptr : felt*
end

struct CallContractResponse:
    member retdata_size : felt
    member retdata : felt*
    # The storage pointer after the syscall.
    member storage_ptr : felt*
end

struct CallContract:
    member request : CallContractRequest
    member response : CallContractResponse
end

func call_contract{syscall_ptr : felt*, storage_ptr : Storage*}(
        contract_address : felt, function_selector : felt, calldata_size : felt,
        calldata : felt*) -> (retdata_size : felt, retdata : felt*):
    let syscall = [cast(syscall_ptr, CallContract*)]
    assert syscall.request = CallContractRequest(
        selector=CALL_CONTRACT_SELECTOR,
        contract_address=contract_address,
        function_selector=function_selector,
        calldata_size=calldata_size,
        calldata=calldata,
        storage_ptr=storage_ptr)
    %{ syscall_handler.call_contract(segments=segments, syscall_ptr=ids.syscall_ptr) %}
    let response = syscall.response

    let syscall_ptr = syscall_ptr + CallContract.SIZE
    let storage_ptr = cast(response.storage_ptr, Storage*)
    return (retdata_size=response.retdata_size, retdata=response.retdata)
end

const GET_CALLER_ADDRESS_SELECTOR = %[int.from_bytes(b'GetCallerAddress', 'big')%]

# Describes the GetCallerAddress system call format.
struct GetCallerAddressRequest:
    # The system call selector (= GET_CALLER_ADDRESS_SELECTOR).
    member selector : felt
end

struct GetCallerAddressResponse:
    member caller_address : felt
end

struct GetCallerAddress:
    member request : GetCallerAddressRequest
    member response : GetCallerAddressResponse
end

# Returns the address of the calling contract or 0 if this transaction was not initiated by another
# contract.
func get_caller_address{syscall_ptr : felt*}() -> (caller_address : felt):
    let syscall = [cast(syscall_ptr, GetCallerAddress*)]
    assert syscall.request = GetCallerAddressRequest(selector=GET_CALLER_ADDRESS_SELECTOR)
    %{ syscall_handler.get_caller_address(segments=segments, syscall_ptr=ids.syscall_ptr) %}
    let syscall_ptr = syscall_ptr + GetCallerAddress.SIZE
    return (caller_address=syscall.response.caller_address)
end
