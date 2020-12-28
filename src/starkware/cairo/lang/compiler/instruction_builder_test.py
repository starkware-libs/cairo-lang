import pytest

from starkware.cairo.lang.compiler.error_handling import get_location_marks
from starkware.cairo.lang.compiler.instruction import Instruction, Register
from starkware.cairo.lang.compiler.instruction_builder import (
    InstructionBuilderError, build_instruction)
from starkware.cairo.lang.compiler.parser import parse_instruction


def parse_and_build(inst: str) -> Instruction:
    """
    Parses the given instruction and builds the Instruction instance.
    """
    return build_instruction(parse_instruction(inst))


def test_assert_eq():
    assert parse_and_build('[ap] = [fp]; ap++') == \
        Instruction(
            off0=0,
            off1=-1,
            off2=0,
            imm=None,
            dst_register=Register.AP,
            op0_register=Register.FP,
            op1_addr=Instruction.Op1Addr.FP,
            res=Instruction.Res.OP1,
            pc_update=Instruction.PcUpdate.REGULAR,
            ap_update=Instruction.ApUpdate.ADD1,
            fp_update=Instruction.FpUpdate.REGULAR,
            opcode=Instruction.Opcode.ASSERT_EQ)
    assert parse_and_build('[fp - 3] = [fp + 7]') == \
        Instruction(
            off0=-3,
            off1=-1,
            off2=7,
            imm=None,
            dst_register=Register.FP,
            op0_register=Register.FP,
            op1_addr=Instruction.Op1Addr.FP,
            res=Instruction.Res.OP1,
            pc_update=Instruction.PcUpdate.REGULAR,
            ap_update=Instruction.ApUpdate.REGULAR,
            fp_update=Instruction.FpUpdate.REGULAR,
            opcode=Instruction.Opcode.ASSERT_EQ)
    assert parse_and_build('[ap - 3] = [ap]') == \
        Instruction(
            off0=-3,
            off1=-1,
            off2=0,
            imm=None,
            dst_register=Register.AP,
            op0_register=Register.FP,
            op1_addr=Instruction.Op1Addr.AP,
            res=Instruction.Res.OP1,
            pc_update=Instruction.PcUpdate.REGULAR,
            ap_update=Instruction.ApUpdate.REGULAR,
            fp_update=Instruction.FpUpdate.REGULAR,
            opcode=Instruction.Opcode.ASSERT_EQ)


def test_assert_eq_reversed():
    assert parse_and_build('5 = [fp + 1]') == parse_and_build('[fp + 1] = 5')
    assert parse_and_build('[[ap + 2] + 3] = [fp + 1]; ap++') == \
        parse_and_build('[fp + 1] = [[ap + 2] + 3]; ap++')
    assert parse_and_build('[ap] + [fp] = [fp + 1]') == parse_and_build('[fp + 1] = [ap] + [fp]')


def test_assert_eq_instruction_failures():
    verify_exception("""\
fp - 3 = [fp]
^****^
Expected a dereference expression.
""")
    verify_exception("""\
ap = [fp]
^^
Expected a dereference expression.
""")
    verify_exception("""\
[ap] = [fp * 3]
        ^****^
Expected '+' or '-', found: '*'.
""")
    verify_exception("""\
[ap] = [fp + 32768]
             ^***^
Expected a constant offset in the range [-2^15, 2^15).
""")
    verify_exception("""\
[ap] = [fp - 32769]
             ^***^
Expected a constant offset in the range [-2^15, 2^15).
""")
    verify_exception("""\
[5] = [fp]
 ^
Expected a register. Found: 5.
""")
    verify_exception("""\
[x + 7] = [15]
 ^
Expected a register. Found: x.
""")
    # Make sure that if the instruction is invalid, the error is given for its original form,
    # rather than the reversed form.
    verify_exception("""\
[[ap + 1]] = [[ap + 1]]
 ^******^
Expected a register. Found: [ap + 1].
""")


def test_assert_eq_double_dereference():
    assert parse_and_build('[ap + 2] = [[fp]]') == \
        Instruction(
            off0=2,
            off1=0,
            off2=0,
            imm=None,
            dst_register=Register.AP,
            op0_register=Register.FP,
            op1_addr=Instruction.Op1Addr.OP0,
            res=Instruction.Res.OP1,
            pc_update=Instruction.PcUpdate.REGULAR,
            ap_update=Instruction.ApUpdate.REGULAR,
            fp_update=Instruction.FpUpdate.REGULAR,
            opcode=Instruction.Opcode.ASSERT_EQ)
    assert parse_and_build('[ap + 2] = [[ap - 4] + 7]; ap++') == \
        Instruction(
            off0=2,
            off1=-4,
            off2=7,
            imm=None,
            dst_register=Register.AP,
            op0_register=Register.AP,
            op1_addr=Instruction.Op1Addr.OP0,
            res=Instruction.Res.OP1,
            pc_update=Instruction.PcUpdate.REGULAR,
            ap_update=Instruction.ApUpdate.ADD1,
            fp_update=Instruction.FpUpdate.REGULAR,
            opcode=Instruction.Opcode.ASSERT_EQ)


def test_assert_eq_double_dereference_failures():
    verify_exception("""\
[ap + 2] = [[fp + 32768] + 17]
                  ^***^
Expected a constant offset in the range [-2^15, 2^15).
""")
    verify_exception("""\
[ap + 2] = [[fp * 32768] + 17]
             ^********^
Expected '+' or '-', found: '*'.
""")


def test_assert_eq_imm():
    assert parse_and_build('[ap + 2] = 1234567890') == \
        Instruction(
            off0=2,
            off1=-1,
            off2=1,
            imm=1234567890,
            dst_register=Register.AP,
            op0_register=Register.FP,
            op1_addr=Instruction.Op1Addr.IMM,
            res=Instruction.Res.OP1,
            pc_update=Instruction.PcUpdate.REGULAR,
            ap_update=Instruction.ApUpdate.REGULAR,
            fp_update=Instruction.FpUpdate.REGULAR,
            opcode=Instruction.Opcode.ASSERT_EQ)


def test_assert_eq_operation():
    assert parse_and_build('[ap + 1] = [ap - 7] * [fp + 3]') == \
        Instruction(
            off0=1,
            off1=-7,
            off2=3,
            imm=None,
            dst_register=Register.AP,
            op0_register=Register.AP,
            op1_addr=Instruction.Op1Addr.FP,
            res=Instruction.Res.MUL,
            pc_update=Instruction.PcUpdate.REGULAR,
            ap_update=Instruction.ApUpdate.REGULAR,
            fp_update=Instruction.FpUpdate.REGULAR,
            opcode=Instruction.Opcode.ASSERT_EQ)
    assert parse_and_build('[ap + 10] = [fp] + 1234567890') == \
        Instruction(
            off0=10,
            off1=0,
            off2=1,
            imm=1234567890,
            dst_register=Register.AP,
            op0_register=Register.FP,
            op1_addr=Instruction.Op1Addr.IMM,
            res=Instruction.Res.ADD,
            pc_update=Instruction.PcUpdate.REGULAR,
            ap_update=Instruction.ApUpdate.REGULAR,
            fp_update=Instruction.FpUpdate.REGULAR,
            opcode=Instruction.Opcode.ASSERT_EQ)
    assert parse_and_build('[fp - 3] = [ap + 7] * [ap + 8]') == \
        Instruction(
            off0=-3,
            off1=7,
            off2=8,
            imm=None,
            dst_register=Register.FP,
            op0_register=Register.AP,
            op1_addr=Instruction.Op1Addr.AP,
            res=Instruction.Res.MUL,
            pc_update=Instruction.PcUpdate.REGULAR,
            ap_update=Instruction.ApUpdate.REGULAR,
            fp_update=Instruction.FpUpdate.REGULAR,
            opcode=Instruction.Opcode.ASSERT_EQ)


def test_inverse_syntactic_sugar():
    assert parse_and_build('[fp] = [ap + 10] - [fp - 1]') == \
        parse_and_build('[ap + 10] = [fp] + [fp - 1]')
    assert parse_and_build('[fp] = [ap + 10] / [fp - 1]') == \
        parse_and_build('[ap + 10] = [fp] * [fp - 1]')


def test_inverse_syntactic_sugar_failures():
    # The syntactic sugar for sub is op0 = dst - op1.
    verify_exception("""\
[fp] = [ap + 10] - 1234567890
                   ^********^
Subtraction and division are not supported for immediates.
""")
    verify_exception("""\
[fp] = [ap + 10] / 1234567890
                   ^********^
Subtraction and division are not supported for immediates.
""")
    verify_exception("""\
1234567890 = [ap + 10] - [fp]
^********^
Expected a dereference expression.
""")
    verify_exception("""\
[ap] = [[fp]] - [ap]
        ^**^
Expected a register. Found: [fp].
""")
    verify_exception("""\
[ap] = 5 - [ap]
       ^
Expected a dereference expression.
""")


def test_assert_eq_operation_failures():
    verify_exception("""\
[ap + 1] = 1234 * [fp]
           ^**^
Expected a dereference expression.
""")
    verify_exception("""\
[ap + 1] = [fp] + [fp] * [fp]
                  ^*********^
Expected a constant expression or a dereference expression.
""")


def test_jump_instruction():
    assert parse_and_build('jmp rel [ap + 1] + [fp - 7]') == \
        Instruction(
            off0=-1,
            off1=1,
            off2=-7,
            imm=None,
            dst_register=Register.FP,
            op0_register=Register.AP,
            op1_addr=Instruction.Op1Addr.FP,
            res=Instruction.Res.ADD,
            pc_update=Instruction.PcUpdate.JUMP_REL,
            ap_update=Instruction.ApUpdate.REGULAR,
            fp_update=Instruction.FpUpdate.REGULAR,
            opcode=Instruction.Opcode.NOP)
    assert parse_and_build('jmp abs 123; ap++') == \
        Instruction(
            off0=-1,
            off1=-1,
            off2=1,
            imm=123,
            dst_register=Register.FP,
            op0_register=Register.FP,
            op1_addr=Instruction.Op1Addr.IMM,
            res=Instruction.Res.OP1,
            pc_update=Instruction.PcUpdate.JUMP,
            ap_update=Instruction.ApUpdate.ADD1,
            fp_update=Instruction.FpUpdate.REGULAR,
            opcode=Instruction.Opcode.NOP)
    assert parse_and_build('jmp rel [ap + 1] + [ap - 7]') == \
        Instruction(
            off0=-1,
            off1=1,
            off2=-7,
            imm=None,
            dst_register=Register.FP,
            op0_register=Register.AP,
            op1_addr=Instruction.Op1Addr.AP,
            res=Instruction.Res.ADD,
            pc_update=Instruction.PcUpdate.JUMP_REL,
            ap_update=Instruction.ApUpdate.REGULAR,
            fp_update=Instruction.FpUpdate.REGULAR,
            opcode=Instruction.Opcode.NOP)


def test_jnz_instruction():
    assert parse_and_build('jmp rel [fp - 1] if [fp - 7] != 0') == \
        Instruction(
            off0=-7,
            off1=-1,
            off2=-1,
            imm=None,
            dst_register=Register.FP,
            op0_register=Register.FP,
            op1_addr=Instruction.Op1Addr.FP,
            res=Instruction.Res.UNCONSTRAINED,
            pc_update=Instruction.PcUpdate.JNZ,
            ap_update=Instruction.ApUpdate.REGULAR,
            fp_update=Instruction.FpUpdate.REGULAR,
            opcode=Instruction.Opcode.NOP)
    assert parse_and_build('jmp rel [ap - 1] if [fp - 7] != 0') == \
        Instruction(
            off0=-7,
            off1=-1,
            off2=-1,
            imm=None,
            dst_register=Register.FP,
            op0_register=Register.FP,
            op1_addr=Instruction.Op1Addr.AP,
            res=Instruction.Res.UNCONSTRAINED,
            pc_update=Instruction.PcUpdate.JNZ,
            ap_update=Instruction.ApUpdate.REGULAR,
            fp_update=Instruction.FpUpdate.REGULAR,
            opcode=Instruction.Opcode.NOP)
    assert parse_and_build('jmp rel 123 if [ap] != 0; ap++') == \
        Instruction(
            off0=0,
            off1=-1,
            off2=1,
            imm=123,
            dst_register=Register.AP,
            op0_register=Register.FP,
            op1_addr=Instruction.Op1Addr.IMM,
            res=Instruction.Res.UNCONSTRAINED,
            pc_update=Instruction.PcUpdate.JNZ,
            ap_update=Instruction.ApUpdate.ADD1,
            fp_update=Instruction.FpUpdate.REGULAR,
            opcode=Instruction.Opcode.NOP)


def test_jnz_instruction_failures():
    verify_exception("""\
jmp rel [fp] if 5 != 0
                ^
Expected a dereference expression.
""")
    verify_exception("""\
jmp rel [ap] if [fp] + 3 != 0
                ^******^
Expected a dereference expression.
""")
    verify_exception("""\
jmp rel [ap] if [fp * 3] != 0
                 ^****^
Expected '+' or '-', found: '*'.
""")
    verify_exception("""\
jmp rel [ap] + [fp] if [fp] != 0
        ^*********^
Invalid expression for jmp offset.
""")


def test_call_instruction():
    assert parse_and_build('call abs [fp + 4]') == \
        Instruction(
            off0=0,
            off1=1,
            off2=4,
            imm=None,
            dst_register=Register.AP,
            op0_register=Register.AP,
            op1_addr=Instruction.Op1Addr.FP,
            res=Instruction.Res.OP1,
            pc_update=Instruction.PcUpdate.JUMP,
            ap_update=Instruction.ApUpdate.ADD2,
            fp_update=Instruction.FpUpdate.AP_PLUS2,
            opcode=Instruction.Opcode.CALL)

    assert parse_and_build('call rel [fp + 4]') == \
        Instruction(
            off0=0,
            off1=1,
            off2=4,
            imm=None,
            dst_register=Register.AP,
            op0_register=Register.AP,
            op1_addr=Instruction.Op1Addr.FP,
            res=Instruction.Res.OP1,
            pc_update=Instruction.PcUpdate.JUMP_REL,
            ap_update=Instruction.ApUpdate.ADD2,
            fp_update=Instruction.FpUpdate.AP_PLUS2,
            opcode=Instruction.Opcode.CALL)
    assert parse_and_build('call rel [ap + 4]') == \
        Instruction(
            off0=0,
            off1=1,
            off2=4,
            imm=None,
            dst_register=Register.AP,
            op0_register=Register.AP,
            op1_addr=Instruction.Op1Addr.AP,
            res=Instruction.Res.OP1,
            pc_update=Instruction.PcUpdate.JUMP_REL,
            ap_update=Instruction.ApUpdate.ADD2,
            fp_update=Instruction.FpUpdate.AP_PLUS2,
            opcode=Instruction.Opcode.CALL)
    assert parse_and_build('call rel 123') == \
        Instruction(
            off0=0,
            off1=1,
            off2=1,
            imm=123,
            dst_register=Register.AP,
            op0_register=Register.AP,
            op1_addr=Instruction.Op1Addr.IMM,
            res=Instruction.Res.OP1,
            pc_update=Instruction.PcUpdate.JUMP_REL,
            ap_update=Instruction.ApUpdate.ADD2,
            fp_update=Instruction.FpUpdate.AP_PLUS2,
            opcode=Instruction.Opcode.CALL)


def test_call_instruction_failures():
    verify_exception("""\
call rel [ap] + 5
         ^******^
Invalid offset for call.
""")
    verify_exception("""\
call rel 5; ap++
^**************^
ap++ may not be used with the call opcode.
""")


def test_ret_instruction():
    assert parse_and_build('ret') == \
        Instruction(
            off0=-2,
            off1=-1,
            off2=-1,
            imm=None,
            dst_register=Register.FP,
            op0_register=Register.FP,
            op1_addr=Instruction.Op1Addr.FP,
            res=Instruction.Res.OP1,
            pc_update=Instruction.PcUpdate.JUMP,
            ap_update=Instruction.ApUpdate.REGULAR,
            fp_update=Instruction.FpUpdate.DST,
            opcode=Instruction.Opcode.RET)


def test_ret_instruction_failures():
    verify_exception("""\
ret; ap++
^*******^
ap++ may not be used with the ret opcode.
""")


def test_addap_instruction():
    assert parse_and_build('ap += [fp + 4] + [fp]') == \
        Instruction(
            off0=-1,
            off1=4,
            off2=0,
            imm=None,
            dst_register=Register.FP,
            op0_register=Register.FP,
            op1_addr=Instruction.Op1Addr.FP,
            res=Instruction.Res.ADD,
            pc_update=Instruction.PcUpdate.REGULAR,
            ap_update=Instruction.ApUpdate.ADD,
            fp_update=Instruction.FpUpdate.REGULAR,
            opcode=Instruction.Opcode.NOP)
    assert parse_and_build('ap += [ap + 4] + [ap]') == \
        Instruction(
            off0=-1,
            off1=4,
            off2=0,
            imm=None,
            dst_register=Register.FP,
            op0_register=Register.AP,
            op1_addr=Instruction.Op1Addr.AP,
            res=Instruction.Res.ADD,
            pc_update=Instruction.PcUpdate.REGULAR,
            ap_update=Instruction.ApUpdate.ADD,
            fp_update=Instruction.FpUpdate.REGULAR,
            opcode=Instruction.Opcode.NOP)
    assert parse_and_build('ap += 123') == \
        Instruction(
            off0=-1,
            off1=-1,
            off2=1,
            imm=123,
            dst_register=Register.FP,
            op0_register=Register.FP,
            op1_addr=Instruction.Op1Addr.IMM,
            res=Instruction.Res.OP1,
            pc_update=Instruction.PcUpdate.REGULAR,
            ap_update=Instruction.ApUpdate.ADD,
            fp_update=Instruction.FpUpdate.REGULAR,
            opcode=Instruction.Opcode.NOP)


def test_addap_instruction_failures():
    verify_exception("""\
ap += 5; ap++
^***********^
ap++ may not be used with the addap opcode.
""")


def verify_exception(code_with_err):
    """
    Gets a string with three lines:
        code
        location marks
        error message
    Verifies that parsing the code results in the given error.
    """
    code = code_with_err.splitlines()[0]
    with pytest.raises(InstructionBuilderError) as e:
        parse_and_build(code)
    assert get_location_marks(code, e.value.location) + '\n' + str(e.value.message) == \
        code_with_err.rstrip()
