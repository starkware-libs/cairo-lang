from starkware.starknet.public.abi import starknet_keccak


def test_starknet_keccak():
    value = starknet_keccak(b'hello')
    assert value == 0x8aff950685c2ed4bc3174f3472287b56d9517b9c948127319a09a7a36deac8
    assert value < 2**250
