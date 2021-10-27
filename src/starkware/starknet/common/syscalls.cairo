from starkware.cairo.common.dict_access import DictAccess

const SEND_MESSAGE_TO_L1_SELECTOR = 'SendMessageToL1'

# Describes the SendMessageToL1 system call format.
struct SendMessageToL1SysCall:
    member selector : felt
    member to_address : felt
    member payload_size : felt
    member payload_ptr : felt*
end

const CALL_CONTRACT_SELECTOR = 'CallContract'

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
end

struct CallContractResponse:
    member retdata_size : felt
    member retdata : felt*
end

struct CallContract:
    member request : CallContractRequest
    member response : CallContractResponse
end

func call_contract{syscall_ptr : felt*}(
        contract_address : felt, function_selector : felt, calldata_size : felt,
        calldata : felt*) -> (retdata_size : felt, retdata : felt*):
    let syscall = [cast(syscall_ptr, CallContract*)]
    assert syscall.request = CallContractRequest(
        selector=CALL_CONTRACT_SELECTOR,
        contract_address=contract_address,
        function_selector=function_selector,
        calldata_size=calldata_size,
        calldata=calldata)
    %{ syscall_handler.call_contract(segments=segments, syscall_ptr=ids.syscall_ptr) %}
    let response = syscall.response

    let syscall_ptr = syscall_ptr + CallContract.SIZE
    return (retdata_size=response.retdata_size, retdata=response.retdata)
end

const GET_CALLER_ADDRESS_SELECTOR = 'GetCallerAddress'

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

const GET_TX_SIGNATURE_SELECTOR = 'GetTxSignature'

struct GetTxSignatureRequest:
    # The system call selector (= GET_TX_SIGNATURE_SELECTOR).
    member selector : felt
end

struct GetTxSignatureResponse:
    member signature_len : felt
    member signature : felt*
end

struct GetTxSignature:
    member request : GetTxSignatureRequest
    member response : GetTxSignatureResponse
end

# Returns the signature information of the transaction.
#
# Note that currently a malicious sequencer may choose to return different values each time
# this function is called.
func get_tx_signature{syscall_ptr : felt*}() -> (signature_len : felt, signature : felt*):
    let syscall = [cast(syscall_ptr, GetTxSignature*)]
    assert syscall.request = GetTxSignatureRequest(selector=GET_TX_SIGNATURE_SELECTOR)
    %{ syscall_handler.get_tx_signature(segments=segments, syscall_ptr=ids.syscall_ptr) %}
    let syscall_ptr = syscall_ptr + GetTxSignature.SIZE
    return (signature_len=syscall.response.signature_len, signature=syscall.response.signature)
end

const STORAGE_READ_SELECTOR = 'StorageRead'

# Describes the StorageRead system call format.
struct StorageReadRequest:
    # The system call selector (= STORAGE_READ_SELECTOR).
    member selector : felt
    member address : felt
end

struct StorageReadResponse:
    member value : felt
end

struct StorageRead:
    member request : StorageReadRequest
    member response : StorageReadResponse
end

func storage_read{syscall_ptr : felt*}(address : felt) -> (value : felt):
    let syscall = [cast(syscall_ptr, StorageRead*)]
    assert syscall.request = StorageReadRequest(selector=STORAGE_READ_SELECTOR, address=address)
    %{ syscall_handler.storage_read(segments=segments, syscall_ptr=ids.syscall_ptr) %}
    let response = syscall.response
    let syscall_ptr = syscall_ptr + StorageRead.SIZE
    return (value=response.value)
end

const STORAGE_WRITE_SELECTOR = 'StorageWrite'

# Describes the StorageWrite system call format.
struct StorageWrite:
    member selector : felt
    member address : felt
    member value : felt
end

func storage_write{syscall_ptr : felt*}(address : felt, value : felt) -> ():
    assert [cast(syscall_ptr, StorageWrite*)] = StorageWrite(
        selector=STORAGE_WRITE_SELECTOR, address=address, value=value)
    %{ syscall_handler.storage_write(segments=segments, syscall_ptr=ids.syscall_ptr) %}
    let syscall_ptr = syscall_ptr + StorageWrite.SIZE
    return ()
end
