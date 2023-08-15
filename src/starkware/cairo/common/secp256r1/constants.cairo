// Basic definitions for the secp25r1 elliptic curve.
// The curve is given by the equation:
//   y^2 = x^3 + ax + b
// over the field Z/p for
//   p = secp256r1_prime = 2 ** 256 - (2**224 - 2**192 - 2**96 + 1)
// The size of the curve is
//   n = 0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551 (prime).

const BASE = 2 ** 86;
// Using 84 bits for the most significant limb is enough to represent all 256 bit numbers.
const D2_BOUND = 2 ** 84;

// SECP_REM = SECP_REM2 || SECP_REM1 || SECP_REM0 is defined by the equation:
//  secp256r1_prime = 2 ** 256 - SECP_REM.
// SECP_REM = 2**224 - 2**192 - 2**96 + 1.
const SECP_REM0 = 1;
const SECP_REM1 = -(2 ** 10);
const SECP_REM2 = 0xffffffff00000;

// Constants for unreduced_mul/sqr.
// See unreduced_mul for more detail.

// BASE3_MOD_P2 || BASE3_MOD_P1 || BASE3_MOD_P0 =
// (2**(86*3)) mod p = 4 * 2**224 - 4 * 2**192 - 4 * 2**96 + 4 =
// (2**54 + 2**22) * 2**(86*2) - 2**12 * 2**86 + 4.
const BASE3_MOD_P2 = 2 ** 54 - 2 ** 22;
const BASE3_MOD_P1 = -(2 ** 12);
const BASE3_MOD_P0 = 4;

// BASE4_MOD_P2 || BASE4_MOD_P1 || BASE4_MOD_P0 =
// (2**(86*4)) mod p =
// 255 * 2**248 - 2 ** 224 + 2**184 + 254 * 2**184 - 2**152 + 2 ** 96 + 2**88 + 2**56 - 1 =
// (-2**76 - 2**12) * 2**(86*2) - (-2**66 + 4) * 2**86 + 2**56.
const BASE4_MOD_P2 = (-(2 ** 76)) - 2 ** 12;
const BASE4_MOD_P1 = (-(2 ** 66)) + 4;
const BASE4_MOD_P0 = 2 ** 56;
