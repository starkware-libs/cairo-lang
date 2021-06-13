import pytest

from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt
from starkware.cairo.lang.compiler.ast.expr import ExprIdentifier
from starkware.cairo.lang.compiler.identifier_definition import MemberDefinition, StructDefinition
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.identifier_utils import get_struct_definition
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.type_casts import FELT_STAR
from starkware.starknet.compiler.calldata_parser import process_calldata

scope = ScopedName.from_string


def test_process_calldata_flow():
    identifier_values = {
        scope('MyStruct'): StructDefinition(
            full_name=scope('MyStruct'),
            members={
                'arg_a': MemberDefinition(offset=0, cairo_type=TypeFelt()),
                'arg_b': MemberDefinition(offset=1, cairo_type=TypeFelt()),
            },
            size=11,
        ),
    }
    identifiers = IdentifierManager.from_dict(identifier_values)

    calldata_ptr = ExprIdentifier('calldata_ptr')

    expr = process_calldata(
        calldata_ptr=calldata_ptr, identifiers=identifiers,
        struct_def=get_struct_definition(
            struct_name=scope('MyStruct'), identifier_manager=identifiers))

    assert expr.format() == """\
arg_a=cast([calldata_ptr + 0], felt), arg_b=cast([calldata_ptr + 1], felt),"""


def test_process_calldata_failure():
    identifier_values = {
        scope('MyStruct'): StructDefinition(
            full_name=scope('MyStruct'),
            members={
                'arg_a': MemberDefinition(offset=0, cairo_type=FELT_STAR),
                'arg_b': MemberDefinition(offset=1, cairo_type=TypeFelt()),
            },
            size=11,
        ),
    }
    identifiers = IdentifierManager.from_dict(identifier_values)

    calldata_ptr = ExprIdentifier('calldata_ptr')

    with pytest.raises(PreprocessorError, match='Unsupported argument type felt*.'):
        process_calldata(
            calldata_ptr=calldata_ptr, identifiers=identifiers,
            struct_def=get_struct_definition(
                struct_name=scope('MyStruct'), identifier_manager=identifiers))
