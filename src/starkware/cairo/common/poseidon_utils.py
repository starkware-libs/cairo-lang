"""
Implementation of Poseidon hades_permutation, as defined in
https://starkware.co/hash-challenge/hash-challenge-implementation-reference-code/.
"""

import hashlib
from typing import List, Optional, Type

from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.python.math_utils import safe_div


def generate_round_constant(fn_name: str, field_prime: int, idx: int) -> int:
    """
    Returns a field element based on the result of sha256.
    The input to sha256 is the concatenation of the name of the hash function and an index.
    For example, the first element for Poseidon will be computed using the value of
    sha256('Poseidon0').
    """
    val = int(hashlib.sha256(f"{fn_name}{idx}".encode("utf-8")).hexdigest(), 16)
    return val % field_prime


class PoseidonParams:
    """
    Poseidon is a family of cryptographic primitives, a special case of Hades when the field is a
    prime field. It is a sponge construction over hades_permutation, as defined in
       https://starkware.co/hash-challenge/hash-challenge-implementation-reference-code/
    where:
    1. field_prime is a prime number that defines the field.
    2. r is the rate.
    3. c is the capacity.
    4. m = r + c, the state size, is the number of field elements in input_state and output_state.
    5. r_f is the number of full rounds.
    6. r_p is the number of partial rounds.
    """

    poseidon_small_params: Optional["PoseidonParams"] = None

    def __init__(
        self, field_prime: int, r: int, c: int, r_f: int, r_p: int
    ):
        self.field_prime = field_prime
        self.r = r
        self.c = c
        self.m = m = r + c
        assert r_f % 2 == 0
        self.r_f = r_f
        self.r_p = r_p
        self.n_rounds = n_rounds = r_f + r_p
        self.output_size = c
        assert self.output_size <= r
        # A list of r_f + r_p vectors for the Add-Round Key phase.
        self.ark =  [
                [generate_round_constant("Hades", field_prime, m * i + j) for j in range(m)]
                for i in range(n_rounds)
            ]

    @classmethod
    def get_default_poseidon_params(cls: Type["PoseidonParams"]):
        if cls.poseidon_small_params is None:
            cls.poseidon_small_params = cls(
                field_prime=DEFAULT_PRIME, r=2, c=1, r_f=8, r_p=83
            )

        return cls.poseidon_small_params


def hades_round(values, params: PoseidonParams, is_full_round: bool, round_idx: int):
    # Add-Round Key.
    values = [
        (val + ark) % params.field_prime
        for val, ark in zip(values, params.ark[round_idx])
    ]
    # SubWords.
    if is_full_round:
        values =  [pow(val, 3, params.field_prime) for val in values]
    else:
        values[-1] = pow(values[-1], 3, params.field_prime)

    # MixLayer.
    values = mds_mul(values, params.field_prime)
    return values


def hades_permutation(values: List[int], params: PoseidonParams) -> List[int]:
    assert len(values) == params.m

    round_idx = 0
    # Apply r_f/2 full rounds.
    for _ in range(safe_div(params.r_f, 2)):
        values = hades_round(values, params, True, round_idx)
        round_idx += 1
    # Apply r_p partial rounds.
    for _ in range(params.r_p):
        values = hades_round(values, params, False, round_idx)
        round_idx += 1
    # Apply r_f/2 full rounds.
    for _ in range(safe_div(params.r_f, 2)):
        values = hades_round(values, params, True, round_idx)
        round_idx += 1
    assert round_idx == params.n_rounds
    return values


def mds_mul(vector, field):
    """
    Multiplies a vector by the SmallMds matrix.
	[3, 1, 1]    [r0]    [3* r0 + r1 + r2 ]
	[1, -1, 1] * [r1]  = [r0 - r1 + r2    ]
	[1, 1, -2]   [r2]    [r0 + r1 - 2 * r2]
    """
    return [
        (3 * vector[0] + vector[1] + vector[2]) % field,
        (vector[0] - vector[1] + vector[2]) % field,
        (vector[0] + vector[1] - 2 * vector[2]) % field,
    ]

# The actual config to be in use, with extremely small MDS coefficients.
# SmallMds = [[3, 1, 1], [1, -1, 1], [1, 1, -2]]
