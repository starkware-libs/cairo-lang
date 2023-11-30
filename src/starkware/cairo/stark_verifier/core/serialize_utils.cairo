from starkware.cairo.common.memcpy import memcpy
from starkware.cairo.common.uint256 import Uint256

// Appends the given felt to the array pointed by the `data` (implicit) argument.
func append_felt{data: felt*}(elem: felt) {
    assert data[0] = elem;
    let data = data + 1;
    return ();
}

// Concats the given array of felts to the array pointed by the `data` (implicit) argument.
// Note that the array len is not added to `data`.
func append_felts{data: felt*}(len: felt, arr: felt*) {
    memcpy(dst=data, src=arr, len=len);
    let data = data + len;
    return ();
}

// Appends the given Uint256 to the array pointed by the `data` (implicit) argument.
func append_uint256{data: felt*}(elem: Uint256) {
    assert data[0] = elem.high;
    assert data[1] = elem.low;
    let data = data + 2;
    return ();
}
