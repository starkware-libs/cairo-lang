import pytest

from starkware.cairo.lang.compiler.instruction import Instruction
from starkware.cairo.lang.compiler.instruction_builder import build_instruction
from starkware.cairo.lang.compiler.parser import parse_instruction
from starkware.cairo.lang.compiler.encode import encode_instruction
from starkware.cairo.lang.compiler.disassembler import disassemble_instruction
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME


def parse_loop(inst: str):
    """
    Parses the given instruction, builds the Instruction instance, then
    disassembles the Instruction instance.  Compares the original Instruction's
    encoding to the reconstructed Instruction's encoding and asserts that the
    two are identical.
    """
    i1 = build_instruction(parse_instruction(inst))
    e1 = encode_instruction(i1, DEFAULT_PRIME)
    i2 = build_instruction(parse_instruction(disassemble_instruction(i1)))
    e2 = encode_instruction(i2, DEFAULT_PRIME)
    assert e1[0] == e2[0]
    if len(e1) == 2:
        assert e1[1] == e2[1]


def test_assert_eq():
    parse_loop('[ap] = [fp]; ap++')
    parse_loop('[fp - 3] = [fp + 7]')
    parse_loop('[ap - 3] = [ap]')


def test_assert_eq_double_dereference():
    parse_loop('[ap + 2] = [[fp]]')
    parse_loop('[ap + 2] = [[ap - 4] + 7]; ap++')


def test_assert_eq_imm():
    parse_loop('[ap + 2] = 1234567890')


def test_assert_eq_operation():
    parse_loop('[ap + 1] = [ap - 7] * [fp + 3]')
    parse_loop('[ap + 10] = [fp] + 1234567890')
    parse_loop('[fp - 3] = [ap + 7] * [ap + 8]')


def test_jump_instruction():
    parse_loop('jmp rel [ap + 1] + [fp - 7]')
    parse_loop('jmp abs 123; ap++')
    parse_loop('jmp rel [ap + 1] + [ap - 7]')


def test_jnz_instruction():
    parse_loop('jmp rel [fp - 1] if [fp - 7] != 0')
    parse_loop('jmp rel [ap - 1] if [fp - 7] != 0')
    parse_loop('jmp rel 123 if [ap] != 0; ap++')


def test_call_instruction():
    parse_loop('call abs [fp + 4]')
    parse_loop('call rel [fp + 4]')
    parse_loop('call rel [ap + 4]')
    parse_loop('call rel 123')


def test_ret_instruction():
    parse_loop('ret')


def test_addap_instruction():
    parse_loop('ap += [fp + 4] + [fp]')
    parse_loop('ap += [ap + 4] + [ap]')
    parse_loop('ap += 123')
