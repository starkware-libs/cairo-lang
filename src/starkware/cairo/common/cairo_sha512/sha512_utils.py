from enum import Enum
from typing import List


class SHA512BATCHResources(Enum):
    STEPS = 13710
    RANGE_CHECKS = 192
    BITWISE = 9960


SHA512_IV = [
    0x6A09E667F3BCC908,
    0xBB67AE8584CAA73B,
    0x3C6EF372FE94F82B,
    0xA54FF53A5F1D36F1,
    0x510E527FADE682D1,
    0x9B05688C2B3E6C1F,
    0x1F83D9ABFB41BD6B,
    0x5BE0CD19137E2179,
]

SHA384_IV = [
    0xCBBB9D5DC1059ED8,
    0x629A292A367CD507,
    0x9159015A3070DD17,
    0x152FECD8F70E5939,
    0x67332667FFC00B31,
    0x8EB44A8768581511,
    0xDB0C2E0D64F98FA7,
    0x47B5481DBEFA4FA4,
]

ROUND_CONSTANTS = [
    0x428A2F98D728AE22,
    0x7137449123EF65CD,
    0xB5C0FBCFEC4D3B2F,
    0xE9B5DBA58189DBBC,
    0x3956C25BF348B538,
    0x59F111F1B605D019,
    0x923F82A4AF194F9B,
    0xAB1C5ED5DA6D8118,
    0xD807AA98A3030242,
    0x12835B0145706FBE,
    0x243185BE4EE4B28C,
    0x550C7DC3D5FFB4E2,
    0x72BE5D74F27B896F,
    0x80DEB1FE3B1696B1,
    0x9BDC06A725C71235,
    0xC19BF174CF692694,
    0xE49B69C19EF14AD2,
    0xEFBE4786384F25E3,
    0x0FC19DC68B8CD5B5,
    0x240CA1CC77AC9C65,
    0x2DE92C6F592B0275,
    0x4A7484AA6EA6E483,
    0x5CB0A9DCBD41FBD4,
    0x76F988DA831153B5,
    0x983E5152EE66DFAB,
    0xA831C66D2DB43210,
    0xB00327C898FB213F,
    0xBF597FC7BEEF0EE4,
    0xC6E00BF33DA88FC2,
    0xD5A79147930AA725,
    0x06CA6351E003826F,
    0x142929670A0E6E70,
    0x27B70A8546D22FFC,
    0x2E1B21385C26C926,
    0x4D2C6DFC5AC42AED,
    0x53380D139D95B3DF,
    0x650A73548BAF63DE,
    0x766A0ABB3C77B2A8,
    0x81C2C92E47EDAEE6,
    0x92722C851482353B,
    0xA2BFE8A14CF10364,
    0xA81A664BBC423001,
    0xC24B8B70D0F89791,
    0xC76C51A30654BE30,
    0xD192E819D6EF5218,
    0xD69906245565A910,
    0xF40E35855771202A,
    0x106AA07032BBD1B8,
    0x19A4C116B8D2D0C8,
    0x1E376C085141AB53,
    0x2748774CDF8EEB99,
    0x34B0BCB5E19B48A8,
    0x391C0CB3C5C95A63,
    0x4ED8AA4AE3418ACB,
    0x5B9CCA4F7763E373,
    0x682E6FF3D6B2B8A3,
    0x748F82EE5DEFB2FC,
    0x78A5636F43172F60,
    0x84C87814A1F0AB72,
    0x8CC702081A6439EC,
    0x90BEFFFA23631E28,
    0xA4506CEBDE82BDE9,
    0xBEF9A3F7B2C67915,
    0xC67178F2E372532B,
    0xCA273ECEEA26619C,
    0xD186B8C721C0C207,
    0xEADA7DD6CDE0EB1E,
    0xF57D4F7FEE6ED178,
    0x06F067AA72176FBA,
    0x0A637DC5A2C898A6,
    0x113F9804BEF90DAE,
    0x1B710B35131C471B,
    0x28DB77F523047D84,
    0x32CAAB7B40C72493,
    0x3C9EBE0A15C9BEBC,
    0x431D67C49C100D4C,
    0x4CC5D4BECB3E42B6,
    0x597F299CFC657E2A,
    0x5FCB6FAB3AD6FAEC,
    0x6C44198C4A475817,
]


def right_rot(value, n):
    return (value >> n) | ((value & (2**n - 1)) << (64 - n))


def compute_message_schedule(message: List[int]) -> List[int]:
    w = list(message)
    assert len(w) == 16

    for i in range(16, 80):
        s0 = right_rot(w[i - 15], 1) ^ right_rot(w[i - 15], 8) ^ (w[i - 15] >> 7)
        s1 = right_rot(w[i - 2], 19) ^ right_rot(w[i - 2], 61) ^ (w[i - 2] >> 6)
        w.append((w[i - 16] + s0 + w[i - 7] + s1) % 2**64)

    return w


def sha2_compress_function(state: List[int], w: List[int]) -> List[int]:
    a, b, c, d, e, f, g, h = state

    for i in range(80):
        s0 = right_rot(a, 28) ^ right_rot(a, 34) ^ right_rot(a, 39)
        s1 = right_rot(e, 14) ^ right_rot(e, 18) ^ right_rot(e, 41)
        ch = (e & f) ^ ((~e) & g)
        temp1 = (h + s1 + ch + ROUND_CONSTANTS[i] + w[i]) % 2**64
        maj = (a & b) ^ (a & c) ^ (b & c)
        temp2 = (s0 + maj) % 2**64

        h = g
        g = f
        f = e
        e = (d + temp1) % 2**64
        d = c
        c = b
        b = a
        a = (temp1 + temp2) % 2**64

    # Add the compression result to the original state.
    return [
        (state[0] + a) % 2**64,
        (state[1] + b) % 2**64,
        (state[2] + c) % 2**64,
        (state[3] + d) % 2**64,
        (state[4] + e) % 2**64,
        (state[5] + f) % 2**64,
        (state[6] + g) % 2**64,
        (state[7] + h) % 2**64,
    ]


def sha_512_update_state(
    state: list[int],
    message: list[int],
) -> List[int]:
    """
    Computes the SHA-512 block compression function.
    """
    w = compute_message_schedule(message)
    return sha2_compress_function(state, w)
