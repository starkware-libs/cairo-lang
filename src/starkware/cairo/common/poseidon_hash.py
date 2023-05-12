from typing import List, Optional

from starkware.cairo.common.poseidon_utils import PoseidonParams, hades_permutation
from starkware.python.utils import blockify, from_bytes, to_bytes


def poseidon_perm(*elements):
    """
    Returns the poseidon permutation of the inputs.
    """
    assert len(elements) == 3, f"Only the case of 3 elements is supported, got {elements}."
    return hades_permutation(list(elements), PoseidonParams.get_default_poseidon_params())


def poseidon_hash_func(x: bytes, y: bytes) -> bytes:
    """
    Returns the poseidon_hash of the inputs.
    """
    return to_bytes(poseidon_perm(from_bytes(x), from_bytes(y), 2)[0])


def poseidon_hash(x: int, y: int, poseidon_params: Optional[PoseidonParams] = None) -> int:
    """
    Hashes two elements and retrieves a single field element output.
    Equivalent to the function with the same name at
    src/starkware/cairo/common/builtin_poseidon/poseidon.cairo
    """
    if poseidon_params is None:
        poseidon_params = PoseidonParams.get_default_poseidon_params()

    return hades_permutation([x, y, 2], poseidon_params)[0]


def poseidon_hash_single(x: int, poseidon_params: Optional[PoseidonParams] = None) -> int:
    """
    Hashes single element and retrieves a single field element output.
    Equivalent to the function with the same name at
    src/starkware/cairo/common/builtin_poseidon/poseidon.cairo
    """
    if poseidon_params is None:
        poseidon_params = PoseidonParams.get_default_poseidon_params()

    return hades_permutation([x, 0, 1], poseidon_params)[0]


def poseidon_hash_many(array: List[int], poseidon_params: Optional[PoseidonParams] = None) -> int:
    """
    Hashes array of elements and retrieves a single field element output.
    Equivalent to the function with the same name at
    src/starkware/cairo/common/builtin_poseidon/poseidon.cairo
    """
    if poseidon_params is None:
        poseidon_params = PoseidonParams.get_default_poseidon_params()

    values = list(array)
    m = poseidon_params.m
    r = poseidon_params.r

    # Pad input with 1 followed by 0's (if necessary).
    values.append(1)
    values += [0] * (-len(values) % r)

    assert len(values) % r == 0
    state = [0] * m
    for block in blockify(data=values, chunk_size=r):
        state = list(
            hades_permutation(
                [state_val + block_val for state_val, block_val in zip(state, block)] + state[-1:],
                poseidon_params,
            )
        )

    return state[0]
