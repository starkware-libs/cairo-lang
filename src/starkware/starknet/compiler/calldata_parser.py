import hashlib
from typing import List, Optional, Tuple

from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt, TypePointer
from starkware.cairo.lang.compiler.ast.code_elements import CodeElement
from starkware.cairo.lang.compiler.ast.expr import (
    ArgList, ExprAssignment, Expression, ExprIdentifier)
from starkware.cairo.lang.compiler.ast.notes import Notes
from starkware.cairo.lang.compiler.error_handling import Location, ParentLocation
from starkware.cairo.lang.compiler.identifier_definition import MemberDefinition, StructDefinition
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.parser import ParserContext, parse
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError


def process_calldata(
        calldata_ptr: Expression, calldata_size: Expression, identifiers: IdentifierManager,
        struct_def: StructDefinition, has_range_check_builtin: bool,
        location: Location) -> Tuple[List[CodeElement], ArgList]:
    """
    Processes the calldata.

    Returns the expected size of the calldata and an ArgList that corresponds to 'struct_def'.

    Currently only the trivial case where struct consists only of felts is supported.
    """

    def parse_code_element(code: str, parent_location: ParentLocation):
        filename = f'autogen/starknet/arg_parser/{hashlib.sha256(code.encode()).hexdigest()}.cairo'
        return parse(
            filename=filename, code=code, code_type='code_element', expected_type=CodeElement,
            parser_context=ParserContext(parent_location=parent_location))

    struct_parent_location = (location, 'While handling calldata of')
    code_elements = [parse_code_element(
        f'let __calldata_ptr : felt* = cast({calldata_ptr.format()}, felt*)',
        parent_location=struct_parent_location)]
    args = []
    prev_member: Optional[Tuple[str, MemberDefinition]] = None
    for member_name, member_def in struct_def.members.items():
        member_location = member_def.location
        assert member_location is not None
        member_parent_location = (
            member_location, f"While handling calldata argument '{member_name}'")
        cairo_type = member_def.cairo_type
        if isinstance(cairo_type, TypePointer) and isinstance(cairo_type.pointee, TypeFelt):
            has_len = prev_member is not None and prev_member[0] == f'{member_name}_len' and \
                isinstance(prev_member[1].cairo_type, TypeFelt)
            if not has_len:
                raise PreprocessorError(
                    f'Array argument "{member_name}" must be preceeded by a length argument '
                    f'named "{member_name}_len" of type felt.',
                    location=member_location)
            if not has_range_check_builtin:
                raise PreprocessorError(
                    "The 'range_check' builtin must be declared in the '%builtins' directive "
                    'when using array arguments in external functions.',
                    location=member_location)

            code_element_strs = [
                # Check that the length is positive.
                f'assert [range_check_ptr] = __calldata_arg_{member_name}_len',
                f'let range_check_ptr = range_check_ptr + 1',
                # Create the reference.
                f'let __calldata_arg_{member_name} : felt* = __calldata_ptr',
                # Use 'tempvar' instead of 'let' to avoid repeating this computation for the
                # following arguments.
                f'tempvar __calldata_ptr = __calldata_ptr + __calldata_arg_{member_name}_len',
            ]
            for code_element_str in code_element_strs:
                code_elements.append(parse_code_element(
                    code_element_str,
                    parent_location=member_parent_location))
        elif isinstance(cairo_type, TypeFelt):
            code_elements.append(parse_code_element(
                f'let __calldata_arg_{member_name} = [__calldata_ptr]',
                parent_location=member_parent_location))
            code_elements.append(parse_code_element(
                f'let __calldata_ptr = __calldata_ptr + 1',
                parent_location=member_parent_location))
        else:
            raise PreprocessorError(
                f'Unsupported argument type {cairo_type.format()}.',
                location=cairo_type.location)

        args.append(ExprAssignment(
            identifier=ExprIdentifier(name=member_name, location=member_location),
            expr=ExprIdentifier(name=f'__calldata_arg_{member_name}', location=member_location),
            location=member_location))

        prev_member = member_name, member_def

    code_elements.append(parse_code_element(
        f'let __calldata_actual_size =  __calldata_ptr - cast({calldata_ptr.format()}, felt*)',
        parent_location=struct_parent_location))
    code_elements.append(parse_code_element(
        f'assert {calldata_size.format()} = __calldata_actual_size',
        parent_location=struct_parent_location))

    return code_elements, ArgList(
        args=args, notes=[Notes()] * (len(args) + 1), has_trailing_comma=True,
        location=location)
