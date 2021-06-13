from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt
from starkware.cairo.lang.compiler.ast.expr import (
    ArgList, ExprAssignment, ExprCast, ExprConst, ExprDeref, Expression, ExprIdentifier,
    ExprOperator)
from starkware.cairo.lang.compiler.ast.notes import Notes
from starkware.cairo.lang.compiler.identifier_definition import StructDefinition
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError


def process_calldata(
        calldata_ptr: Expression, identifiers: IdentifierManager,
        struct_def: StructDefinition) -> ArgList:
    """
    Processes the calldata and produces an ArgList that corresponds to 'struct_def'.

    Currently only the trivial case where struct consists only of felts is supported.
    """
    args = []
    for member_name, member_def in struct_def.members.items():
        location = member_def.location
        cairo_type = member_def.cairo_type
        if not isinstance(cairo_type, TypeFelt):
            raise PreprocessorError(
                f'Unsupported argument type {cairo_type.format()}.',
                location=cairo_type.location)

        args.append(ExprAssignment(
            identifier=ExprIdentifier(name=member_name, location=member_def.location),
            expr=ExprCast(
                expr=ExprDeref(
                    addr=ExprOperator(
                        calldata_ptr, '+', ExprConst(member_def.offset, location=location),
                        location=location),
                    location=location),
                dest_type=cairo_type,
                location=cairo_type.location),
            location=struct_def.location))

    return ArgList(
        args=args, notes=[Notes()] * (len(args) + 1), has_trailing_comma=True,
        location=struct_def.location)
