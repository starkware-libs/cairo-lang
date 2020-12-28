from typing import List, Optional

from starkware.cairo.lang.compiler.instruction import (
    OFFSET_BITS, Instruction, Register, decode_instruction_values)

DST_REG_BIT = 0
OP0_REG_BIT = 1
OP1_IMM_BIT = 2
OP1_FP_BIT = 3
OP1_AP_BIT = 4
RES_ADD_BIT = 5
RES_MUL_BIT = 6
PC_JUMP_ABS_BIT = 7
PC_JUMP_REL_BIT = 8
PC_JNZ_BIT = 9
AP_ADD_BIT = 10
AP_ADD1_BIT = 11
OPCODE_CALL_BIT = 12
OPCODE_RET_BIT = 13
OPCODE_ASSERT_EQ_BIT = 14
# RESERVED_BIT = 15.


def encode_instruction(inst: Instruction, prime: int) -> List[int]:
    """
    Given an Instruction, returns a list of 1 or 2 integers representing the instruction.
    """
    assert prime > 2 ** (3 * OFFSET_BITS + 16)
    assert -2 ** (OFFSET_BITS - 1) <= inst.off0 < 2 ** (OFFSET_BITS - 1), \
        f'off0 must be in range [-2**{OFFSET_BITS - 1}, 2**{OFFSET_BITS - 1})'
    assert -2 ** (OFFSET_BITS - 1) <= inst.off1 < 2 ** (OFFSET_BITS - 1), \
        f'off1 must be in range [-2**{OFFSET_BITS - 1}, 2**{OFFSET_BITS - 1})'
    assert -2 ** (OFFSET_BITS - 1) <= inst.off2 < 2 ** (OFFSET_BITS - 1), \
        f'off2 must be in range [-2**{OFFSET_BITS - 1}, 2**{OFFSET_BITS - 1})'
    off0_enc = inst.off0 + 2 ** (OFFSET_BITS - 1)
    off1_enc = inst.off1 + 2 ** (OFFSET_BITS - 1)
    off2_enc = inst.off2 + 2 ** (OFFSET_BITS - 1)

    # Flags.
    flags = 0

    # Set dst_register.
    flags |= (1 << DST_REG_BIT) if inst.dst_register is Register.FP else 0

    # Set op0_register.
    flags |= (1 << OP0_REG_BIT) if inst.op0_register is Register.FP else 0

    # Set op1_addr.
    assert (inst.imm is not None) == (inst.op1_addr is Instruction.Op1Addr.IMM), \
        'Immediate must appear iff op1_addr is Op1Addr.IMM'

    flags |= {
        Instruction.Op1Addr.IMM: 1 << OP1_IMM_BIT,
        Instruction.Op1Addr.AP: 1 << OP1_AP_BIT,
        Instruction.Op1Addr.FP: 1 << OP1_FP_BIT,
        Instruction.Op1Addr.OP0: 0
    }[inst.op1_addr]

    # Set res.
    flags |= {
        Instruction.Res.ADD: 1 << RES_ADD_BIT,
        Instruction.Res.MUL: 1 << RES_MUL_BIT,
        Instruction.Res.OP1: 0,
        Instruction.Res.UNCONSTRAINED: 0,
    }[inst.res]
    assert (inst.res is Instruction.Res.UNCONSTRAINED) == \
        (inst.pc_update == Instruction.PcUpdate.JNZ), \
        'res must be UNCONSTRAINED iff pc_update is JNZ'

    # Set pc_update.
    flags |= {
        Instruction.PcUpdate.JUMP: 1 << PC_JUMP_ABS_BIT,
        Instruction.PcUpdate.JUMP_REL: 1 << PC_JUMP_REL_BIT,
        Instruction.PcUpdate.JNZ: 1 << PC_JNZ_BIT,
        Instruction.PcUpdate.REGULAR: 0,
    }[inst.pc_update]

    # Set ap_update.
    assert (inst.ap_update is Instruction.ApUpdate.ADD2) == \
        (inst.opcode is Instruction.Opcode.CALL), \
        'ap_update is ADD2 iff opcode is CALL'
    flags |= {
        Instruction.ApUpdate.ADD: 1 << AP_ADD_BIT,
        Instruction.ApUpdate.ADD1: 1 << AP_ADD1_BIT,
        # ADD2 and REGULAR are differentiated by the CALL opcode flag.
        Instruction.ApUpdate.ADD2: 0,
        Instruction.ApUpdate.REGULAR: 0,
    }[inst.ap_update]

    # Set fp_update.
    assert inst.fp_update == {
        Instruction.Opcode.NOP: Instruction.FpUpdate.REGULAR,
        Instruction.Opcode.CALL: Instruction.FpUpdate.AP_PLUS2,
        Instruction.Opcode.RET: Instruction.FpUpdate.DST,
        Instruction.Opcode.ASSERT_EQ: Instruction.FpUpdate.REGULAR,
    }[inst.opcode], f'fp_update {inst.fp_update} does not match opcode f{inst.opcode}'

    # Set opcode.
    flags |= {
        Instruction.Opcode.CALL: 1 << OPCODE_CALL_BIT,
        Instruction.Opcode.RET: 1 << OPCODE_RET_BIT,
        Instruction.Opcode.ASSERT_EQ: 1 << OPCODE_ASSERT_EQ_BIT,
        Instruction.Opcode.NOP: 0,
    }[inst.opcode]

    encoding = flags << (3 * OFFSET_BITS)
    encoding |= off2_enc << (2 * OFFSET_BITS)
    encoding |= off1_enc << (OFFSET_BITS)
    encoding |= off0_enc

    assert 0 <= encoding < prime
    if inst.imm is not None:
        return [encoding, inst.imm % prime]
    return [encoding]


def decode_instruction(encoding: int, imm: Optional[int] = None) -> Instruction:
    """
    Given 1 or 2 integers representing an instruction, returns the Instruction.
    If imm is given for an instruction with no immediate, it will be ignored.
    """
    flags, off0_enc, off1_enc, off2_enc = decode_instruction_values(encoding)

    # Get dst_register.
    dst_register = Register.FP if (flags >> DST_REG_BIT) & 1 else Register.AP

    # Get op0_register.
    op0_register = Register.FP if (flags >> OP0_REG_BIT) & 1 else Register.AP

    # Get op1.
    op1_addr = {
        (1, 0, 0): Instruction.Op1Addr.IMM,
        (0, 1, 0): Instruction.Op1Addr.AP,
        (0, 0, 1): Instruction.Op1Addr.FP,
        (0, 0, 0): Instruction.Op1Addr.OP0
    }[(flags >> OP1_IMM_BIT) & 1, (flags >> OP1_AP_BIT) & 1, (flags >> OP1_FP_BIT) & 1]

    if op1_addr is Instruction.Op1Addr.IMM:
        assert imm is not None, 'op1_addr is Op1Addr.IMM, but no immediate given'
    else:
        imm = None

    # Get pc_update.
    pc_update = {
        (1, 0, 0): Instruction.PcUpdate.JUMP,
        (0, 1, 0): Instruction.PcUpdate.JUMP_REL,
        (0, 0, 1): Instruction.PcUpdate.JNZ,
        (0, 0, 0): Instruction.PcUpdate.REGULAR
    }[(flags >> PC_JUMP_ABS_BIT) & 1, (flags >> PC_JUMP_REL_BIT) & 1, (flags >> PC_JNZ_BIT) & 1]

    # Get res.
    res = {
        (1, 0): Instruction.Res.ADD,
        (0, 1): Instruction.Res.MUL,
        (0, 0):
            Instruction.Res.UNCONSTRAINED if pc_update is Instruction.PcUpdate.JNZ
            else Instruction.Res.OP1,
    }[(flags >> RES_ADD_BIT) & 1, (flags >> RES_MUL_BIT) & 1]

    # JNZ opcode means res must be UNCONSTRAINED.
    if pc_update is Instruction.PcUpdate.JNZ:
        assert res is Instruction.Res.UNCONSTRAINED

    # Get ap_update.
    ap_update = {
        (1, 0): Instruction.ApUpdate.ADD,
        (0, 1): Instruction.ApUpdate.ADD1,
        (0, 0): Instruction.ApUpdate.REGULAR,  # OR ADD2, depending if we have CALL opcode.
    }[(flags >> AP_ADD_BIT) & 1, (flags >> AP_ADD1_BIT) & 1]

    # Get opcode.
    opcode = {
        (1, 0, 0): Instruction.Opcode.CALL,
        (0, 1, 0): Instruction.Opcode.RET,
        (0, 0, 1): Instruction.Opcode.ASSERT_EQ,
        (0, 0, 0): Instruction.Opcode.NOP
    }[
        (flags >> OPCODE_CALL_BIT) & 1, (flags >> OPCODE_RET_BIT) & 1,
        (flags >> OPCODE_ASSERT_EQ_BIT) & 1]

    # CALL opcode means ap_update must be ADD2.
    if opcode is Instruction.Opcode.CALL:
        assert ap_update is Instruction.ApUpdate.REGULAR, 'CALL must have update_ap is ADD2'
        ap_update = Instruction.ApUpdate.ADD2

    # Get fp_update.
    if opcode is Instruction.Opcode.CALL:
        fp_update = Instruction.FpUpdate.AP_PLUS2
    elif opcode is Instruction.Opcode.RET:
        fp_update = Instruction.FpUpdate.DST
    else:
        fp_update = Instruction.FpUpdate.REGULAR

    return Instruction(
        off0=off0_enc - 2 ** (OFFSET_BITS - 1),
        off1=off1_enc - 2 ** (OFFSET_BITS - 1),
        off2=off2_enc - 2**(OFFSET_BITS - 1),
        imm=imm,
        dst_register=dst_register,
        op0_register=op0_register,
        op1_addr=op1_addr,
        res=res,
        pc_update=pc_update,
        ap_update=ap_update,
        fp_update=fp_update,
        opcode=opcode,
    )


def is_call_instruction(encoded_instruction: int, imm: Optional[int]):
    """
    Returns True if the given instruction looks like a call instruction.
    """
    try:
        instruction = decode_instruction(encoding=encoded_instruction, imm=imm)
    except Exception:
        return False
    return (
        instruction.res is Instruction.Res.OP1 and
        instruction.pc_update in [Instruction.PcUpdate.JUMP, Instruction.PcUpdate.JUMP_REL] and
        instruction.ap_update is Instruction.ApUpdate.ADD2 and
        instruction.fp_update is Instruction.FpUpdate.AP_PLUS2 and
        instruction.opcode is Instruction.Opcode.CALL
    )
