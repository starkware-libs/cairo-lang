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
const DELEGATE_CALL_SELECTOR = 'DelegateCall'
const DELEGATE_L1_HANDLER_SELECTOR = 'DelegateL1Handler'

# Describes the CallContract system call format.
struct CallContractRequest:
    # The system call selector
    # (= CALL_CONTRACT_SELECTOR, DELEGATE_CALL_SELECTOR or DELEGATE_L1_HANDLER_SELECTOR).
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
    contract_address : felt, function_selector : felt, calldata_size : felt, calldata : felt*
) -> (retdata_size : felt, retdata : felt*):
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

const LIBRARY_CALL_SELECTOR = 'LibraryCall'
const LIBRARY_CALL_L1_HANDLER_SELECTOR = 'LibraryCallL1Handler'

# Describes the LibraryCall system call format.
struct LibraryCallRequest:
    # The system library call selector
    # (= LIBRARY_CALL_SELECTOR or LIBRARY_CALL_L1_HANDLER_SELECTOR).
    member selector : felt
    # The hash of the class to run.
    member class_hash : felt
    # The selector of the function to call.
    member function_selector : felt
    # The size of the calldata.
    member calldata_size : felt
    # The calldata.
    member calldata : felt*
end

struct LibraryCall:
    member request : LibraryCallRequest
    member response : CallContractResponse
end

# Performs a library call: Runs an entry point of another contract class
# on the current contract state.
func library_call{syscall_ptr : felt*}(
    class_hash : felt, function_selector : felt, calldata_size : felt, calldata : felt*
) -> (retdata_size : felt, retdata : felt*):
    let syscall = [cast(syscall_ptr, LibraryCall*)]
    assert syscall.request = LibraryCallRequest(
        selector=LIBRARY_CALL_SELECTOR,
        class_hash=class_hash,
        function_selector=function_selector,
        calldata_size=calldata_size,
        calldata=calldata)
    %{ syscall_handler.library_call(segments=segments, syscall_ptr=ids.syscall_ptr) %}
    let response = syscall.response

    let syscall_ptr = syscall_ptr + LibraryCall.SIZE
    return (retdata_size=response.retdata_size, retdata=response.retdata)
end

# Simialr to library_call(), except that the entry point is an L1 handler,
# rather than an external function.
# Note that this function does not consume an L1 message,
# and thus it should only be called from a corresponding L1 handler.
func library_call_l1_handler{syscall_ptr : felt*}(
    class_hash : felt, function_selector : felt, calldata_size : felt, calldata : felt*
) -> (retdata_size : felt, retdata : felt*):
    let syscall = [cast(syscall_ptr, LibraryCall*)]
    assert syscall.request = LibraryCallRequest(
        selector=LIBRARY_CALL_L1_HANDLER_SELECTOR,
        class_hash=class_hash,
        function_selector=function_selector,
        calldata_size=calldata_size,
        calldata=calldata)
    %{ syscall_handler.library_call_l1_handler(segments=segments, syscall_ptr=ids.syscall_ptr) %}
    let response = syscall.response

    let syscall_ptr = syscall_ptr + LibraryCall.SIZE
    return (retdata_size=response.retdata_size, retdata=response.retdata)
end

const DEPLOY_SELECTOR = 'Deploy'

# Describes the Deploy system call format.
struct DeployRequest:
    # The system call selector (= DEPLOY_SELECTOR).
    member selector : felt
    # The hash of the class to deploy.
    member class_hash : felt
    # A salt for the new contract address calculation.
    member contract_address_salt : felt
    # The size of the calldata for the constructor.
    member constructor_calldata_size : felt
    # The calldata for the constructor.
    member constructor_calldata : felt*
    # Used for deterministic contract address deployment.
    member deploy_from_zero : felt
end

struct DeployResponse:
    member contract_address : felt
    member constructor_retdata_size : felt
    member constructor_retdata : felt*
end

struct Deploy:
    member request : DeployRequest
    member response : DeployResponse
end

# Deploys a contract with the given class, and returns its address.
# Fails if a contract with the same parameters was already deployed.
# If 'deploy_from_zero' is 1, the contract address is not affected by the deployer's address.
func deploy{syscall_ptr : felt*}(
    class_hash : felt,
    contract_address_salt : felt,
    constructor_calldata_size : felt,
    constructor_calldata : felt*,
    deploy_from_zero : felt,
) -> (contract_address : felt):
    let syscall = [cast(syscall_ptr, Deploy*)]
    assert syscall.request = DeployRequest(
        selector=DEPLOY_SELECTOR,
        class_hash=class_hash,
        contract_address_salt=contract_address_salt,
        constructor_calldata_size=constructor_calldata_size,
        constructor_calldata=constructor_calldata,
        deploy_from_zero=deploy_from_zero)

    %{ syscall_handler.deploy(segments=segments, syscall_ptr=ids.syscall_ptr) %}
    let response = syscall.response
    let syscall_ptr = syscall_ptr + Deploy.SIZE

    return (contract_address=response.contract_address)
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

const GET_SEQUENCER_ADDRESS_SELECTOR = 'GetSequencerAddress'

# Describes the GetSequencerAddress system call format.
struct GetSequencerAddressRequest:
    # The system call selector (= GET_SEQUENCER_ADDRESS_SELECTOR).
    member selector : felt
end

struct GetSequencerAddressResponse:
    member sequencer_address : felt
end

struct GetSequencerAddress:
    member request : GetSequencerAddressRequest
    member response : GetSequencerAddressResponse
end

# Returns the address of the sequencer contract.
func get_sequencer_address{syscall_ptr : felt*}() -> (sequencer_address : felt):
    let syscall = [cast(syscall_ptr, GetSequencerAddress*)]
    assert syscall.request = GetSequencerAddressRequest(selector=GET_SEQUENCER_ADDRESS_SELECTOR)
    %{ syscall_handler.get_sequencer_address(segments=segments, syscall_ptr=ids.syscall_ptr) %}
    let syscall_ptr = syscall_ptr + GetSequencerAddress.SIZE
    return (sequencer_address=syscall.response.sequencer_address)
end

const GET_BLOCK_NUMBER_SELECTOR = 'GetBlockNumber'

struct GetBlockNumberRequest:
    member selector : felt
end

struct GetBlockNumberResponse:
    member block_number : felt
end

struct GetBlockNumber:
    member request : GetBlockNumberRequest
    member response : GetBlockNumberResponse
end

func get_block_number{syscall_ptr : felt*}() -> (block_number : felt):
    let syscall = [cast(syscall_ptr, GetBlockNumber*)]
    assert syscall.request = GetBlockNumberRequest(selector=GET_BLOCK_NUMBER_SELECTOR)
    %{ syscall_handler.get_block_number(segments=segments, syscall_ptr=ids.syscall_ptr) %}
    let syscall_ptr = syscall_ptr + GetBlockNumber.SIZE
    return (block_number=syscall.response.block_number)
end

const GET_CONTRACT_ADDRESS_SELECTOR = 'GetContractAddress'

# Describes the GetContractAddress system call format.
struct GetContractAddressRequest:
    # The system call selector (= GET_CONTRACT_ADDRESS_SELECTOR).
    member selector : felt
end

struct GetContractAddressResponse:
    member contract_address : felt
end

struct GetContractAddress:
    member request : GetContractAddressRequest
    member response : GetContractAddressResponse
end

func get_contract_address{syscall_ptr : felt*}() -> (contract_address : felt):
    let syscall = [cast(syscall_ptr, GetContractAddress*)]
    assert syscall.request = GetContractAddressRequest(selector=GET_CONTRACT_ADDRESS_SELECTOR)
    %{ syscall_handler.get_contract_address(segments=segments, syscall_ptr=ids.syscall_ptr) %}
    let syscall_ptr = syscall_ptr + GetContractAddress.SIZE
    return (contract_address=syscall.response.contract_address)
end

const GET_BLOCK_TIMESTAMP_SELECTOR = 'GetBlockTimestamp'

struct GetBlockTimestampRequest:
    # The system call selector (= GET_BLOCK_TIMESTAMP_SELECTOR).
    member selector : felt
end

struct GetBlockTimestampResponse:
    member block_timestamp : felt
end

struct GetBlockTimestamp:
    member request : GetBlockTimestampRequest
    member response : GetBlockTimestampResponse
end

func get_block_timestamp{syscall_ptr : felt*}() -> (block_timestamp : felt):
    let syscall = [cast(syscall_ptr, GetBlockTimestamp*)]
    assert syscall.request = GetBlockTimestampRequest(selector=GET_BLOCK_TIMESTAMP_SELECTOR)
    %{ syscall_handler.get_block_timestamp(segments=segments, syscall_ptr=ids.syscall_ptr) %}
    let syscall_ptr = syscall_ptr + GetBlockTimestamp.SIZE
    return (block_timestamp=syscall.response.block_timestamp)
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
# NOTE: This function is deprecated. Use get_tx_info() instead.
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

func storage_write{syscall_ptr : felt*}(address : felt, value : felt):
    assert [cast(syscall_ptr, StorageWrite*)] = StorageWrite(
        selector=STORAGE_WRITE_SELECTOR, address=address, value=value)
    %{ syscall_handler.storage_write(segments=segments, syscall_ptr=ids.syscall_ptr) %}
    let syscall_ptr = syscall_ptr + StorageWrite.SIZE
    return ()
end

const EMIT_EVENT_SELECTOR = 'EmitEvent'

# Describes the EmitEvent system call format.
struct EmitEvent:
    member selector : felt
    member keys_len : felt
    member keys : felt*
    member data_len : felt
    member data : felt*
end

func emit_event{syscall_ptr : felt*}(keys_len : felt, keys : felt*, data_len : felt, data : felt*):
    assert [cast(syscall_ptr, EmitEvent*)] = EmitEvent(
        selector=EMIT_EVENT_SELECTOR, keys_len=keys_len, keys=keys, data_len=data_len, data=data)
    %{ syscall_handler.emit_event(segments=segments, syscall_ptr=ids.syscall_ptr) %}
    let syscall_ptr = syscall_ptr + EmitEvent.SIZE
    return ()
end

struct TxInfo:
    # The version of the transaction. It is fixed (currently, 0) in the OS, and should be
    # signed by the account contract.
    # This field allows invalidating old transactions, whenever the meaning of the other
    # transaction fields is changed (in the OS).
    member version : felt

    # The account contract from which this transaction originates.
    member account_contract_address : felt

    # The max_fee field of the transaction.
    member max_fee : felt

    # The signature of the transaction.
    member signature_len : felt
    member signature : felt*

    # The hash of the transaction.
    member transaction_hash : felt

    # The identifier of the chain.
    # This field can be used to prevent replay of testnet transactions on mainnet.
    member chain_id : felt
end

const GET_TX_INFO_SELECTOR = 'GetTxInfo'

# Describes the GetTxInfo system call format.
struct GetTxInfoRequest:
    # The system call selector (= GET_TX_INFO_SELECTOR).
    member selector : felt
end

struct GetTxInfoResponse:
    member tx_info : TxInfo*
end

struct GetTxInfo:
    member request : GetTxInfoRequest
    member response : GetTxInfoResponse
end

func get_tx_info{syscall_ptr : felt*}() -> (tx_info : TxInfo*):
    let syscall = [cast(syscall_ptr, GetTxInfo*)]
    assert syscall.request = GetTxInfoRequest(selector=GET_TX_INFO_SELECTOR)
    %{ syscall_handler.get_tx_info(segments=segments, syscall_ptr=ids.syscall_ptr) %}
    let response = syscall.response
    let syscall_ptr = syscall_ptr + GetTxInfo.SIZE
    return (tx_info=response.tx_info)
end
