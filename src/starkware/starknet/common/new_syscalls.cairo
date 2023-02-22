// Syscall selectors.

const GET_CALLER_ADDRESS_SELECTOR = 'GetCallerAddress';
const EMIT_EVENT_SELECTOR = 'EmitEvent';
const STORAGE_READ_SELECTOR = 'StorageRead';
const STORAGE_WRITE_SELECTOR = 'StorageWrite';

// Shared attributes.

struct RequestHeader {
    // The syscall selector.
    selector: felt,
    // The amount of gas left before the syscall execution.
    gas: felt,
}

struct ResponseHeader {
    // The amount of gas left after the syscall execution.
    gas: felt,
    // 0 if the syscall succeeded; 1 otherwise.
    failure_flag: felt,
}

struct FailureReason {
    start: felt*,
    end: felt*,
}

// Syscall requests.

struct EmptyRequest {
}

struct StorageReadRequest {
    reserved: felt,
    key: felt,
}

struct StorageWriteRequest {
    reserved: felt,
    key: felt,
    value: felt,
}

struct EmitEventRequest {
    keys_start: felt*,
    keys_end: felt*,
    data_start: felt*,
    data_end: felt*,
}

// Syscall responses.

struct StorageReadResponse {
    value: felt,
}

struct GetCallerAddressResponse {
    caller_address: felt,
}
