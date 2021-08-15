import re
from typing import Dict

import pytest

from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt, TypePointer
from starkware.cairo.lang.compiler.ast.expr import ExprIdentifier
from starkware.cairo.lang.compiler.error_handling import InputFile, Location
from starkware.cairo.lang.compiler.identifier_definition import (
    IdentifierDefinition, MemberDefinition, StructDefinition)
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.identifier_utils import get_struct_definition
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.type_casts import FELT_STAR
from starkware.starknet.compiler.calldata_parser import process_calldata

scope = ScopedName.from_string
FELT_STAR_STAR = TypePointer(pointee=FELT_STAR)


def dummy_location():
    return Location(
        start_line=1, start_col=2, end_line=3, end_col=4,
        input_file=InputFile(filename=None, content=''))


def process_test_calldata(members: Dict[str, MemberDefinition], has_range_check_builtin=True):
    identifier_values: Dict[ScopedName, IdentifierDefinition] = {
        scope('MyStruct'): StructDefinition(
            full_name=scope('MyStruct'),
            members=members,
            size=0,
        ),
    }
    identifiers = IdentifierManager.from_dict(identifier_values)
    calldata_ptr = ExprIdentifier('calldata_ptr')
    calldata_size = ExprIdentifier('calldata_size')
    return process_calldata(
        calldata_ptr=calldata_ptr, calldata_size=calldata_size, identifiers=identifiers,
        struct_def=get_struct_definition(
            struct_name=scope('MyStruct'), identifier_manager=identifiers),
        has_range_check_builtin=has_range_check_builtin,
        location=dummy_location())


def test_process_calldata_flow():
    location = dummy_location()
    code_elements, expr = process_test_calldata(members={
        'a_len': MemberDefinition(offset=0, cairo_type=TypeFelt(), location=location),
        'a': MemberDefinition(offset=1, cairo_type=FELT_STAR, location=location),
        'b': MemberDefinition(offset=2, cairo_type=TypeFelt(), location=location),
    })

    assert ''.join(code_element.format(100) + '\n' for code_element in code_elements) == """\
let __calldata_ptr : felt* = cast(calldata_ptr, felt*)
let __calldata_arg_a_len = [__calldata_ptr]
let __calldata_ptr = __calldata_ptr + 1
assert [range_check_ptr] = __calldata_arg_a_len
let range_check_ptr = range_check_ptr + 1
let __calldata_arg_a : felt* = __calldata_ptr
tempvar __calldata_ptr = __calldata_ptr + __calldata_arg_a_len
let __calldata_arg_b = [__calldata_ptr]
let __calldata_ptr = __calldata_ptr + 1
let __calldata_actual_size = __calldata_ptr - cast(calldata_ptr, felt*)
assert calldata_size = __calldata_actual_size
"""

    assert expr.format() == 'a_len=__calldata_arg_a_len, a=__calldata_arg_a, b=__calldata_arg_b,'

    assert code_elements[0].expr.location.parent_location == (
        location, 'While handling calldata of')


def test_process_calldata_failure():
    location = dummy_location()
    with pytest.raises(PreprocessorError, match=re.escape('Unsupported argument type felt**.')):
        process_test_calldata(members={
            'arg_a': MemberDefinition(offset=0, cairo_type=FELT_STAR_STAR, location=location),
            'arg_b': MemberDefinition(offset=1, cairo_type=TypeFelt(), location=location),
        })
    with pytest.raises(
            PreprocessorError, match='Array argument "arg_a" must be preceded by a length '
            'argument named "arg_a_len" of type felt.'):
        process_test_calldata(members={
            'arg_a': MemberDefinition(offset=0, cairo_type=FELT_STAR, location=location),
            'arg_b': MemberDefinition(offset=1, cairo_type=TypeFelt(), location=location),
        })
    with pytest.raises(PreprocessorError, match=re.escape(
            "The 'range_check' builtin must be declared in the '%builtins' directive when using "
            'array arguments in external functions.')):
        process_test_calldata(members={
            'arg_len': MemberDefinition(offset=0, cairo_type=TypeFelt(), location=location),
            'arg': MemberDefinition(offset=1, cairo_type=FELT_STAR, location=location),
        }, has_range_check_builtin=False)
