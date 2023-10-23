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

// The following constants represent the size of the secp256r1 field:
//   p = P0 + BASE * P1 + BASE**2 * P2.
const P0 = 0x3fffffffffffffffffffff;
const P1 = 0x3ff;
const P2 = 0xffffffff0000000100000;

// Curve alpha and beta.
const ALPHA = -3;

// Beta = 0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b.
const BETA0 = 0x13b0f63bce3c3e27d2604b;
const BETA1 = 0x3555da621af194741ac331;
const BETA2 = 0x5ac635d8aa3a93e7b3ebb;

// Constants for unreduced_mul/sqr.
// See unreduced_mul for more detail.

// BASE3_MOD_P2 || BASE3_MOD_P1 || BASE3_MOD_P0 =
// (2**(86*3)) mod p = 4 * 2**224 - 4 * 2**192 - 4 * 2**96 + 4 =
// (2**54 + 2**22) * 2**(86*2) - 2**12 * 2**86 + 4.
const BASE3_MOD_P2 = 2 ** 54 - 2 ** 22;
const BASE3_MOD_P1 = -(2 ** 12);
const BASE3_MOD_P0 = 4;

// (BASE4_MOD_P2 || BASE4_MOD_P1 || BASE4_MOD_P0) + p =
// (2**(86*4)) mod p =
// (-2**76 - 2**12) * 2**(86*2) + (-2**66 + 4) * 2**86 + 2**56 + p.
const BASE4_MOD_P2 = (-(2 ** 76)) - 2 ** 12;
const BASE4_MOD_P1 = (-(2 ** 66)) + 4;
const BASE4_MOD_P0 = 2 ** 56;

// The high and low uint128 parts of SECP256r1_PRIME.
const SECP_PRIME_HIGH = 0xffffffff000000010000000000000000;
const SECP_PRIME_LOW = 0xffffffffffffffffffffffff;
