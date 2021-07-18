from starkware.starknet.common.syscalls import SendMessageToL1SysCall

# Sends a message to an L1 contract at 'l1_address' with given payload.
func send_message_to_l1{syscall_ptr : felt*}(
        to_address : felt, payload_size : felt, payload : felt*):
    assert [cast(syscall_ptr, SendMessageToL1SysCall*)] = SendMessageToL1SysCall(
        selector=%[int.from_bytes(b'SendMessageToL1', 'big')%],
        to_address=to_address,
        payload_size=payload_size,
        payload_ptr=payload)
    let syscall_ptr = syscall_ptr + SendMessageToL1SysCall.SIZE
    return ()
end
