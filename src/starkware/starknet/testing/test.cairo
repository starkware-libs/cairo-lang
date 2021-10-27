%lang starknet
%builtins range_check

from starkware.starknet.common.messages import send_message_to_l1
from starkware.starknet.common.syscalls import (
    get_caller_address, get_tx_signature, storage_read, storage_write)

@external
func increase_value{syscall_ptr : felt*}(address : felt, value : felt):
    let (res) = storage_read(address=address)
    return storage_write(address=address, value=res + value)
end

@external
func get_value{syscall_ptr : felt*}(address : felt) -> (res : felt):
    return storage_read(address=address)
end

@external
func get_caller{syscall_ptr : felt*}() -> (res : felt):
    let (caller_address) = get_caller_address()
    return (res=caller_address)
end

@external
func takes_array{syscall_ptr : felt*}(a_len : felt, a : felt*) -> (res):
    let res = a_len + a[0] + a[1]
    return (res=res)
end

@external
func get_signature{syscall_ptr : felt*}() -> (res_len : felt, res : felt*):
    let (sig_len, sig) = get_tx_signature()
    return (res_len=sig_len, res=sig)
end

@external
func send_message{syscall_ptr : felt*}(to_address : felt, payload_len : felt, payload : felt*):
    send_message_to_l1(to_address=to_address, payload_size=payload_len, payload=payload)
    return ()
end

@l1_handler
func deposit{syscall_ptr : felt*}(from_address : felt, user : felt, amount : felt):
    increase_value(address=user, value=amount)
    return ()
end

struct Point:
    member x : felt
    member y : felt
end

@view
func sum_points(points : (Point, Point)) -> (res : Point):
    let res : Point = Point(x=points[0].x + points[1].x, y=points[0].y + points[1].y)
    return (res=res)
end

@view
func sum_and_mult_points(points : (Point, Point)) -> (sum_res : Point, mult_res : felt):
    let sum_res : Point = sum_points(points=points)
    let mult_res : felt = (points[0].x * points[1].x) + (points[0].y * points[1].y)
    return (sum_res=sum_res, mult_res=mult_res)
end
