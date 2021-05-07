from starkware.cairo.lang.compiler.instruction import (
    Instruction, Register, decode_instruction_values)
from starkware.cairo.lang.compiler.instruction_builder import (
    InstructionBuilderError, build_instruction)
from starkware.cairo.lang.compiler.parser import parse_instruction


def parse_build_disassemble(inst: str) -> str:
    """
    Parses the given instruction and builds the Instruction instance.
    """
    return disassemble_instruction(build_instruction(parse_instruction(inst)))


def disassemble_off(off) -> str:
    """
    Append the string "+<off>" or "-<off>" if <off> is nonzero.
    """
    instr: str = ""
    if off < 0:
        instr += str(off)
    elif off > 0:
        instr += "+" + str(off)
    return instr


def disassemble_source_operand(instruction: Instruction) -> str:
    """
    For asserts, jumps, and increment-ap instructions, disassemble the
    right-hand side of the assert, the target of the jump, and the value of the
    ap-register increment respectively.
    """
    instr: str = " "
    # parse the source
    if instruction.res is Instruction.Res.OP1:
        # either immediate or dereference
        if instruction.op1_addr is Instruction.Op1Addr.IMM:
            # Immediate operand
            instr += str(instruction.imm)
        elif instruction.op1_addr is Instruction.Op1Addr.OP0:
            # Double dereference
            instr += "[["
            instr += 'ap' if instruction.op0_register is Register.AP else 'fp'
            instr += disassemble_off(instruction.off1)
            instr += "]"
            instr += disassemble_off(instruction.off2)
            instr += "]"
        else:
            # Single derefernce
            instr += "["
            instr += 'ap' if instruction.op1_addr is Instruction.Op1Addr.AP else 'fp'
            instr += disassemble_off(instruction.off2)
            instr += "]"
    else:
        # [reg + off] */+ [reg + off] or [reg + off] */+ imm
        instr += "["
        instr += 'fp' if instruction.op0_register is Register.FP else 'ap'
        instr += disassemble_off(instruction.off1)
        instr += "]"
        instr += ' * ' if instruction.res is Instruction.Res.MUL else ' + '
        if instruction.op1_addr is Instruction.Op1Addr.IMM:
            instr += str(instruction.imm)
        else:
            instr += "["
            instr += 'fp' if instruction.op1_addr is Instruction.Op1Addr.FP else 'ap'
            instr += disassemble_off(instruction.off2)
            instr += "]"
    return instr


def disassemble_assert_eq_instruction(instruction: Instruction) -> str:
    """
    Disassemble A = B instructions.  Note that the disassembly may not be
    identical to what was provided in the source code, due to syntactic sugar,
    though the instruction encoding will be.
    """
    instr: str = ""
    # parse the destination
    if instruction.dst_register is Register.AP:
        instr += "[ap"
    elif instruction.dst_register is Register.FP:
        instr += "[fp"
    instr += disassemble_off(instruction.off0)
    instr += "] = "

    instr += disassemble_source_operand(instruction)
    return instr


def disassemble_jump_instruction(instruction: Instruction) -> str:
    """
    Disassemble all jmp-instruction variants.
    """
    instr: str = "jmp"
    if instruction.pc_update is Instruction.PcUpdate.JUMP:
        instr += " abs"
    else:
        instr += " rel"

    if instruction.res is Instruction.Res.UNCONSTRAINED:
        # jnz
        if instruction.op1_addr is Instruction.Op1Addr.IMM:
            instr += " " + str(instruction.imm)
        else:
            if instruction.op1_addr is Instruction.Op1Addr.FP:
                instr += " [fp"
            else:
                instr += " [ap"
            instr += disassemble_off(instruction.off2)
            instr += "]"
    else:
        # jmp
        instr += disassemble_source_operand(instruction)

    if instruction.off0 != -1:
        # conditional jump
        instr += " if ["
        instr += "ap" if instruction.dst_register is Register.AP else "fp"
        instr += disassemble_off(instruction.off0)
        instr += "] != 0"

    return instr


def disassemble_call_instruction(instruction: Instruction) -> str:
    """
    Disassemble the call instruction.
    """
    instr: str = "call"
    if instruction.pc_update is Instruction.PcUpdate.JUMP_REL:
        instr += " rel"
    else:
        instr += " abs"
    if instruction.op1_addr is Instruction.Op1Addr.IMM:
        instr += " " + str(instruction.imm)
    else:
        instr += " ["
        instr += "ap" if instruction.op1_addr is Instruction.Op1Addr.AP else "fp"
        instr += disassemble_off(instruction.off2)
        instr += "]"

    return instr


def disassemble_ap_add_instruction(instruction: Instruction) -> str:
    """
    Disassemble the ap-increment instruction.
    """
    instr: str = "ap +="
    instr += disassemble_source_operand(instruction)
    return instr


def disassemble_instruction(instruction: Instruction) -> str:
    """
    Returns a disssassembly of an Instruction.  The encoding of the
    disassembled instruction string will equal encoding of the input
    instruction.  The input Instruction object is assumed to be well-formed.
    """
    instr: str = ""
    if instruction.opcode is Instruction.Opcode.RET:
        return "ret"
    elif instruction.opcode is Instruction.Opcode.NOP:
        if instruction.ap_update is Instruction.ApUpdate.ADD:
            instr = disassemble_ap_add_instruction(instruction)
        else:
            instr = disassemble_jump_instruction(instruction)
    elif instruction.opcode is Instruction.Opcode.CALL:
        instr = disassemble_call_instruction(instruction)
    elif instruction.opcode is Instruction.Opcode.ASSERT_EQ:
        instr = disassemble_assert_eq_instruction(instruction)

    # parse the AP update
    if instruction.ap_update is Instruction.ApUpdate.ADD1:
        instr += "; ap++"

    return instr
