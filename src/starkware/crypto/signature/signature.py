###############################################################################
# Copyright 2019 StarkWare Industries Ltd.                                    #
#                                                                             #
# Licensed under the Apache License, Version 2.0 (the "License").             #
# You may not use this file except in compliance with the License.            #
# You may obtain a copy of the License at                                     #
#                                                                             #
# https://www.starkware.co/open-source-license/                               #
#                                                                             #
# Unless required by applicable law or agreed to in writing,                  #
# software distributed under the License is distributed on an "AS IS" BASIS,  #
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.    #
# See the License for the specific language governing permissions             #
# and limitations under the License.                                          #
###############################################################################

import hashlib
import itertools
import json
import math
import os
import secrets
from typing import Optional, Tuple, Union

from ecdsa.rfc6979 import generate_k

from starkware.crypto.signature.math_utils import (
    ECPoint,
    div_mod,
    ec_add,
    ec_double,
    ec_mult,
    is_quad_residue,
    sqrt_mod,
)
from starkware.python.math_utils import div_ceil

PEDERSEN_HASH_POINT_FILENAME = os.path.join(os.path.dirname(__file__), "pedersen_params.json")
PEDERSEN_PARAMS = json.load(open(PEDERSEN_HASH_POINT_FILENAME))

FIELD_PRIME = PEDERSEN_PARAMS["FIELD_PRIME"]
FIELD_GEN = PEDERSEN_PARAMS["FIELD_GEN"]
ALPHA = PEDERSEN_PARAMS["ALPHA"]
BETA = PEDERSEN_PARAMS["BETA"]
EC_ORDER = PEDERSEN_PARAMS["EC_ORDER"]
CONSTANT_POINTS = PEDERSEN_PARAMS["CONSTANT_POINTS"]

N_ELEMENT_BITS_ECDSA = math.floor(math.log(FIELD_PRIME, 2))
assert N_ELEMENT_BITS_ECDSA == 251

N_ELEMENT_BITS_HASH = FIELD_PRIME.bit_length()
assert N_ELEMENT_BITS_HASH == 252

# Elliptic curve parameters.
assert 2**N_ELEMENT_BITS_ECDSA < EC_ORDER < FIELD_PRIME

SHIFT_POINT = CONSTANT_POINTS[0]
MINUS_SHIFT_POINT = (SHIFT_POINT[0], FIELD_PRIME - SHIFT_POINT[1])
EC_GEN = CONSTANT_POINTS[1]

assert SHIFT_POINT == [
    0x49EE3EBA8C1600700EE1B87EB599F16716B0B1022947733551FDE4050CA6804,
    0x3CA0CFE4B3BC6DDF346D49D06EA0ED34E621062C0E056C1D0405D266E10268A,
]
assert EC_GEN == [
    0x1EF15C18599971B7BECED415A40F0C7DEACFD9B0D1819E03D723D8BC943CFCA,
    0x5668060AA49730B7BE4801DF46EC62DE53ECD11ABE43A32873000C36E8DC1F,
]


#########
# ECDSA #
#########

# A type for the digital signature.
ECSignature = Tuple[int, int]


class InvalidPublicKeyError(Exception):
    def __init__(self):
        super().__init__("Given x coordinate does not represent any point on the elliptic curve.")


def get_y_coordinate(stark_key_x_coordinate: int) -> int:
    """
    Given the x coordinate of a stark_key, returns a possible y coordinate such that together the
    point (x,y) is on the curve.
    Note that the real y coordinate is either y or -y.
    If x is invalid stark_key it throws an error.
    """

    x = stark_key_x_coordinate
    y_squared = (x * x * x + ALPHA * x + BETA) % FIELD_PRIME
    if not is_quad_residue(y_squared, FIELD_PRIME):
        raise InvalidPublicKeyError()
    return sqrt_mod(y_squared, FIELD_PRIME)


def get_random_private_key() -> int:
    # Returns a private key in the range [1, EC_ORDER).
    return secrets.randbelow(EC_ORDER - 1) + 1


def private_key_to_ec_point_on_stark_curve(priv_key: int) -> ECPoint:
    assert 0 < priv_key < EC_ORDER
    return ec_mult(priv_key, EC_GEN, ALPHA, FIELD_PRIME)


def private_to_stark_key(priv_key: int) -> int:
    return private_key_to_ec_point_on_stark_curve(priv_key)[0]


def inv_mod_curve_size(x: int) -> int:
    return div_mod(1, x, EC_ORDER)


def generate_k_rfc6979(msg_hash: int, priv_key: int, seed: Optional[int] = None) -> int:
    # Pad the message hash, for consistency with the elliptic.js library.
    if 1 <= msg_hash.bit_length() % 8 <= 4 and msg_hash.bit_length() >= 248:
        # Only if we are one-nibble short:
        msg_hash *= 16

    if seed is None:
        extra_entropy = b""
    else:
        extra_entropy = seed.to_bytes(math.ceil(seed.bit_length() / 8), "big")

    return generate_k(
        EC_ORDER,
        priv_key,
        hashlib.sha256,
        msg_hash.to_bytes(math.ceil(msg_hash.bit_length() / 8), "big"),
        extra_entropy=extra_entropy,
    )


def sign(msg_hash: int, priv_key: int, seed: Optional[int] = None) -> ECSignature:
    # Note: msg_hash must be smaller than 2**N_ELEMENT_BITS_ECDSA.
    # Message whose hash is >= 2**N_ELEMENT_BITS_ECDSA cannot be signed.
    # This happens with a very small probability.
    assert 0 <= msg_hash < 2**N_ELEMENT_BITS_ECDSA, "Message not signable."

    # Choose a valid k. In our version of ECDSA not every k value is valid,
    # and there is a negligible probability a drawn k cannot be used for signing.
    # This is why we have this loop.
    while True:
        k = generate_k_rfc6979(msg_hash, priv_key, seed)
        # Update seed for next iteration in case the value of k is bad.
        if seed is None:
            seed = 1
        else:
            seed += 1

        # Cannot fail because 0 < k < EC_ORDER and EC_ORDER is prime.
        x = ec_mult(k, EC_GEN, ALPHA, FIELD_PRIME)[0]

        # DIFF: in classic ECDSA, we take int(x) % n.
        r = int(x)
        if not (1 <= r < 2**N_ELEMENT_BITS_ECDSA):
            # Bad value. This fails with negligible probability.
            continue

        if (msg_hash + r * priv_key) % EC_ORDER == 0:
            # Bad value. This fails with negligible probability.
            continue

        w = div_mod(k, msg_hash + r * priv_key, EC_ORDER)
        if not (1 <= w < 2**N_ELEMENT_BITS_ECDSA):
            # Bad value. This fails with negligible probability.
            continue

        s = inv_mod_curve_size(w)
        return r, s


def mimic_ec_mult_air(m: int, point: ECPoint, shift_point: ECPoint) -> ECPoint:
    """
    Computes m * point + shift_point using the same steps like the AIR and throws an exception if
    and only if the AIR errors.
    """
    assert 0 < m < 2**N_ELEMENT_BITS_ECDSA
    partial_sum = shift_point
    for _ in range(N_ELEMENT_BITS_ECDSA):
        assert partial_sum[0] != point[0]
        if m & 1:
            partial_sum = ec_add(partial_sum, point, FIELD_PRIME)
        point = ec_double(point, ALPHA, FIELD_PRIME)
        m >>= 1
    assert m == 0
    return partial_sum


def is_point_on_curve(x: int, y: int) -> bool:
    return pow(y, 2, FIELD_PRIME) == (pow(x, 3, FIELD_PRIME) + ALPHA * x + BETA) % FIELD_PRIME


def is_valid_stark_key(stark_key: int) -> bool:
    """
    Returns whether the given input is a valid STARK key.
    """
    # Only the x coordinate of the point is given, get the y coordinate and make sure that the
    # point is on the curve.
    try:
        get_y_coordinate(stark_key_x_coordinate=stark_key)
    except InvalidPublicKeyError:
        return False
    return True


def verify(msg_hash: int, r: int, s: int, public_key: Union[int, ECPoint]) -> bool:
    # Compute w = s^-1 (mod EC_ORDER).
    assert 1 <= s < EC_ORDER, "s = %s" % s
    w = inv_mod_curve_size(s)

    # Preassumptions:
    # DIFF: in classic ECDSA, we assert 1 <= r, w <= EC_ORDER-1.
    # Since r, w < 2**N_ELEMENT_BITS_ECDSA < EC_ORDER, we only need to verify r, w != 0.
    assert 1 <= r < 2**N_ELEMENT_BITS_ECDSA, "r = %s" % r
    assert 1 <= w < 2**N_ELEMENT_BITS_ECDSA, "w = %s" % w
    assert 0 <= msg_hash < 2**N_ELEMENT_BITS_ECDSA, "msg_hash = %s" % msg_hash

    if isinstance(public_key, int):
        # Only the x coordinate of the point is given, check the two possibilities for the y
        # coordinate.
        try:
            y = get_y_coordinate(public_key)
        except InvalidPublicKeyError:
            return False
        return verify(msg_hash, r, s, (public_key, y)) or verify(
            msg_hash, r, s, (public_key, (-y) % FIELD_PRIME)
        )

    # The public key is provided as a point.
    assert is_point_on_curve(x=public_key[0], y=public_key[1])

    # Signature validation.
    # DIFF: original formula is:
    # x = (w*msg_hash)*EC_GEN + (w*r)*public_key
    # While what we implement is:
    # x = w*(msg_hash*EC_GEN + r*public_key).
    # While both mathematically equivalent, one might error while the other doesn't,
    # given the current implementation.
    # This formula ensures that if the verification errors in our AIR, it errors here as well.
    try:
        zG = mimic_ec_mult_air(msg_hash, EC_GEN, MINUS_SHIFT_POINT)
        rQ = mimic_ec_mult_air(r, public_key, SHIFT_POINT)
        wB = mimic_ec_mult_air(w, ec_add(zG, rQ, FIELD_PRIME), SHIFT_POINT)
        x = ec_add(wB, MINUS_SHIFT_POINT, FIELD_PRIME)[0]
    except AssertionError:
        return False

    # DIFF: Here we drop the mod n from classic ECDSA.
    return r == x


def grind_key(key_seed: int, key_value_limit: int) -> int:  # type: ignore[return]
    """
    Given a cryptographically-secure seed and a limit, deterministically generates a pseudorandom
    key in the range [0, limit).
    This is a reference implementation, and cryptographic security is not guaranteed (for example,
    it may be vulnerable to side-channel attacks); this function is not recommended for use with key
    generation on mainnet.
    """
    # Simply taking a uniform value in [0, 2**256) and returning the result modulo key_value_limit
    # is not necessarily uniform on [0, key_value_limit). We define max_allowed_value to be a
    # multiple of the limit, so that a uniform sample of [0, max_allowed_value) mod key_value_limit
    # is uniform on [0, key_value_limit).
    max_allowed_value = 2**256 - (2**256 % key_value_limit)

    def to_bytes_no_pad(x: int) -> bytes:
        # To conform with the JS implementation, convert integer to bytes using minimal amount of
        # bytes possible. We would like 0.to_bytes() to be b'\x00', so a minimal length of 1 is
        # enforced.
        return x.to_bytes(length=max(1, div_ceil(x.bit_length(), 8)), byteorder="big", signed=False)

    # Increment the index (salt) until the hash value falls in the range [0, max_allowed_value).
    for index in itertools.count():
        hash_input = to_bytes_no_pad(key_seed) + to_bytes_no_pad(index)
        key = int(hashlib.sha256(hash_input).hexdigest(), 16)
        if key < max_allowed_value:
            return key % key_value_limit


#################
# Pedersen hash #
#################


def pedersen_hash(*elements: int) -> int:
    return pedersen_hash_as_point(*elements)[0]


def pedersen_hash_as_point(*elements: int) -> ECPoint:
    """
    Similar to pedersen_hash but also returns the y coordinate of the resulting EC point.
    This function is used for testing.
    """
    point = SHIFT_POINT
    for i, x in enumerate(elements):
        assert 0 <= x < FIELD_PRIME
        point_list = CONSTANT_POINTS[
            2 + i * N_ELEMENT_BITS_HASH : 2 + (i + 1) * N_ELEMENT_BITS_HASH
        ]
        assert len(point_list) == N_ELEMENT_BITS_HASH
        for pt in point_list:
            assert point[0] != pt[0], "Unhashable input."
            if x & 1:
                point = ec_add(point, pt, FIELD_PRIME)
            x >>= 1
        assert x == 0
    return point
