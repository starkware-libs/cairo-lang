# Describes the SendMessageToL1 system call format.
struct SendMessageToL1SysCall:
    member selector : felt
    member to_address : felt
    member payload_size : felt
    member payload_ptr : felt*
end
