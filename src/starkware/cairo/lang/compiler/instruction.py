import dataclasses
from enum import Enum, auto
from typing import Optional

OFFSET_BITS = 16
N_FLAGS = 15


class Register(Enum):
    AP = 0
    FP = auto()


@dataclasses.dataclass
class Instruction:
    # Offsets. In the range [-2**15, 2*15) = [-2**(OFFSET_BITS-1), 2**(OFFSET_BITS-1)).
    off0: int
    off1: int
    off2: int

    # Immediate.
    imm: Optional[int]

    # Flags for operands.
    dst_register: Register
    op0_register: Register

    class Op1Addr(Enum):
        # op1 = [pc + 1].
        IMM = 0
        # op1 = [ap + off2].
        AP = auto()
        # op1 = [fp + off2].
        FP = auto()
        # op1 = [op0].
        OP0 = auto()
    op1_addr: Op1Addr

    class Res(Enum):
        # res = operand_1.
        OP1 = 0
        # res = operand_0 + operand_1.
        ADD = auto()
        # res = operand_0 * operand_1.
        MUL = auto()
        # res is not constrained.
        UNCONSTRAINED = auto()
    res: Res

    # Flags for register update.
    class PcUpdate(Enum):
        # Next pc: pc + op_size.
        REGULAR = 0
        # Next pc: res (jmp abs).
        JUMP = auto()
        # Next pc: pc + res (jmp rel).
        JUMP_REL = auto()
        # Next pc: jnz_addr (jnz), where jnz_addr is a complex expression, representing the jnz
        # logic.
        JNZ = auto()
    pc_update: PcUpdate

    class ApUpdate(Enum):
        # Next ap: ap.
        REGULAR = 0
        # Next ap: ap + [pc + 1].
        ADD = auto()
        # Next ap: ap + 1.
        ADD1 = auto()
        # Next ap: ap + 2.
        ADD2 = auto()
    ap_update: ApUpdate

    class FpUpdate(Enum):
        # Next fp: fp.
        REGULAR = 0
        # Next fp: ap + 2.
        AP_PLUS2 = auto()
        # Next fp: operand_dst.
        DST = auto()
    fp_update: FpUpdate

    # Flags for opcodes.
    class Opcode(Enum):
        NOP = 0
        ASSERT_EQ = auto()
        CALL = auto()
        RET = auto()
    opcode: Opcode

    @property
    def size(self):
        return 2 if self.imm is not None else 1


def decode_instruction_values(encoded_instruction):
    """
    Returns a tuple (flags, off0, off1, off2) according to the given encoded instruction.
    """
    assert 0 <= encoded_instruction < 2 ** (3 * OFFSET_BITS + N_FLAGS), 'Unsupported instruction.'
    off0 = encoded_instruction & (2 ** OFFSET_BITS - 1)
    off1 = (encoded_instruction >> OFFSET_BITS) & (2 ** OFFSET_BITS - 1)
    off2 = (encoded_instruction >> (2 * OFFSET_BITS)) & (2 ** OFFSET_BITS - 1)
    flags_val = encoded_instruction >> (3 * OFFSET_BITS)
    return flags_val, off0, off1, off2
