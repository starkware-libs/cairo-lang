from typing import List

IV = [
    0x6A09E667,
    0xBB67AE85,
    0x3C6EF372,
    0xA54FF53A,
    0x510E527F,
    0x9B05688C,
    0x1F83D9AB,
    0x5BE0CD19,
]

ROUND_CONSTANTS = [
    0x428A2F98,
    0x71374491,
    0xB5C0FBCF,
    0xE9B5DBA5,
    0x3956C25B,
    0x59F111F1,
    0x923F82A4,
    0xAB1C5ED5,
    0xD807AA98,
    0x12835B01,
    0x243185BE,
    0x550C7DC3,
    0x72BE5D74,
    0x80DEB1FE,
    0x9BDC06A7,
    0xC19BF174,
    0xE49B69C1,
    0xEFBE4786,
    0x0FC19DC6,
    0x240CA1CC,
    0x2DE92C6F,
    0x4A7484AA,
    0x5CB0A9DC,
    0x76F988DA,
    0x983E5152,
    0xA831C66D,
    0xB00327C8,
    0xBF597FC7,
    0xC6E00BF3,
    0xD5A79147,
    0x06CA6351,
    0x14292967,
    0x27B70A85,
    0x2E1B2138,
    0x4D2C6DFC,
    0x53380D13,
    0x650A7354,
    0x766A0ABB,
    0x81C2C92E,
    0x92722C85,
    0xA2BFE8A1,
    0xA81A664B,
    0xC24B8B70,
    0xC76C51A3,
    0xD192E819,
    0xD6990624,
    0xF40E3585,
    0x106AA070,
    0x19A4C116,
    0x1E376C08,
    0x2748774C,
    0x34B0BCB5,
    0x391C0CB3,
    0x4ED8AA4A,
    0x5B9CCA4F,
    0x682E6FF3,
    0x748F82EE,
    0x78A5636F,
    0x84C87814,
    0x8CC70208,
    0x90BEFFFA,
    0xA4506CEB,
    0xBEF9A3F7,
    0xC67178F2,
]


def right_rot(value, n):
    return (value >> n) | ((value & (2 ** n - 1)) << (32 - n))


def compute_message_schedule(message: List[int]) -> List[int]:
    w = list(message)
    assert len(w) == 16

    for i in range(16, 64):
        s0 = right_rot(w[i - 15], 7) ^ right_rot(w[i - 15], 18) ^ (w[i - 15] >> 3)
        s1 = right_rot(w[i - 2], 17) ^ right_rot(w[i - 2], 19) ^ (w[i - 2] >> 10)
        w.append((w[i - 16] + s0 + w[i - 7] + s1) % 2 ** 32)

    return w


def sha2_compress_function(state: List[int], w: List[int]) -> List[int]:
    a, b, c, d, e, f, g, h = state

    for i in range(64):
        s0 = right_rot(a, 2) ^ right_rot(a, 13) ^ right_rot(a, 22)
        s1 = right_rot(e, 6) ^ right_rot(e, 11) ^ right_rot(e, 25)
        ch = (e & f) ^ ((~e) & g)
        temp1 = (h + s1 + ch + ROUND_CONSTANTS[i] + w[i]) % 2 ** 32
        maj = (a & b) ^ (a & c) ^ (b & c)
        temp2 = (s0 + maj) % 2 ** 32

        h = g
        g = f
        f = e
        e = (d + temp1) % 2 ** 32
        d = c
        c = b
        b = a
        a = (temp1 + temp2) % 2 ** 32

    # Add the compression result to the original state.
    return [
        (state[0] + a) % 2 ** 32,
        (state[1] + b) % 2 ** 32,
        (state[2] + c) % 2 ** 32,
        (state[3] + d) % 2 ** 32,
        (state[4] + e) % 2 ** 32,
        (state[5] + f) % 2 ** 32,
        (state[6] + g) % 2 ** 32,
        (state[7] + h) % 2 ** 32,
    ]
