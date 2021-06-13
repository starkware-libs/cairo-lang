import dataclasses
from typing import Optional, Tuple

from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt
from starkware.cairo.lang.compiler.ast.code_elements import (
    CodeElementEmptyLine, CodeElementFunction)
from starkware.cairo.lang.compiler.ast.formatting_utils import get_max_line_length
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.parser import parse
from starkware.cairo.lang.compiler.preprocessor.identifier_aware_visitor import (
    IdentifierAwareVisitor)
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.starknet.definitions.constants import STARKNET_LANG_DIRECTIVE
from starkware.starknet.public.abi import get_storage_var_address

STORAGE_VAR_DECORATOR = 'storage_var'
STORAGE_VAR_ATTR = 'storage_var'


def generate_storage_var_functions(
        elm: CodeElementFunction, addr_func_body: str,
        read_func_body: str, write_func_body: str) -> CodeElementFunction:
    var_name = elm.identifier.name
    autogen_filename = f'autogen/starknet/storage_var/{var_name}'

    code = f"""\
namespace {var_name}:
    from starkware.starknet.core.storage.storage import Storage, storage_read, storage_write
    from starkware.cairo.common.cairo_builtins import HashBuiltin
    from starkware.cairo.common.hash import hash2

    func addr{{pedersen_ptr : HashBuiltin*}}() -> (res : felt):
        {addr_func_body}
    end

    func read{{storage_ptr : Storage*, pedersen_ptr : HashBuiltin*}}():
        {read_func_body}
    end

    func write{{storage_ptr : Storage*, pedersen_ptr : HashBuiltin*}}(value : felt):
        {write_func_body}
    end
end\
"""

    res = parse(autogen_filename, code, 'code_element', CodeElementFunction)

    # Copy the arguments and return values.
    assert isinstance(res, CodeElementFunction) and res.element_type == 'namespace'
    addr_func = res.code_block.code_elements[4].code_elm
    assert isinstance(addr_func, CodeElementFunction) and addr_func.element_type == 'func' and \
        addr_func.identifier.name == 'addr'
    addr_func.arguments = elm.arguments

    read_func = res.code_block.code_elements[6].code_elm
    assert isinstance(read_func, CodeElementFunction) and read_func.element_type == 'func' and \
        read_func.identifier.name == 'read'
    read_func.arguments = elm.arguments
    read_func.returns = elm.returns

    write_func = res.code_block.code_elements[8].code_elm
    assert isinstance(write_func, CodeElementFunction) and write_func.element_type == 'func' and \
        write_func.identifier.name == 'write'
    # Append the value argument to the storage var arguments.
    write_func.arguments = dataclasses.replace(
        elm.arguments,
        identifiers=elm.arguments.identifiers + write_func.arguments.identifiers)

    # Format and re-parse to get locations to a well-formatted code.
    res = parse(
        autogen_filename, res.format(get_max_line_length()), 'code_element', CodeElementFunction)

    res.additional_attributes[STORAGE_VAR_ATTR] = elm

    return res


def process_storage_var(elm: CodeElementFunction):
    for commented_code_elm in elm.code_block.code_elements:
        code_elm = commented_code_elm.code_elm
        if not isinstance(code_elm, CodeElementEmptyLine):
            if hasattr(code_elm, 'location'):
                location = code_elm.location  # type: ignore
            else:
                location = elm.identifier.location
            raise PreprocessorError(
                'Storage variables must have an empty body.',
                location=location)

    if elm.implicit_arguments is not None:
        raise PreprocessorError(
            'Storage variables must have no implicit arguments.',
            location=elm.implicit_arguments.location)

    for decorator in elm.decorators:
        if decorator.name != STORAGE_VAR_DECORATOR:
            raise PreprocessorError(
                'Storage variables must have no decorators in addition to '
                f'@{STORAGE_VAR_DECORATOR}.',
                location=decorator.location)

    for arg in elm.arguments.identifiers:
        arg_type = arg.get_type()
        if not isinstance(arg_type, TypeFelt):
            raise PreprocessorError(
                'Only felt arguments are supported in storage variables.',
                location=arg_type.location)

    returns_felt = elm.returns is not None and len(elm.returns.identifiers) == 1 and \
        isinstance(elm.returns.identifiers[0].expr_type, TypeFelt)
    if not returns_felt:
        raise PreprocessorError(
            'Storage variables must return a single value of type felt.',
            location=elm.returns.location if elm.returns is not None else elm.identifier.location)

    var_name = elm.identifier.name
    addr = storage_var_name_to_base_addr(var_name)
    addr_func_body = f'let res = {addr}\n'
    for arg in elm.arguments.identifiers:
        addr_func_body += \
            f'let (res) = hash2{{hash_ptr=pedersen_ptr}}(res, {arg.identifier.name})\n'
    addr_func_body += 'return (res=res)\n'

    args = ', '.join(arg.identifier.name for arg in elm.arguments.identifiers)

    read_func_body = f"""\
let (storage_addr) = addr({args})
storage_read(address=storage_addr)
return ([ap - 1])
"""
    write_func_body = f"""\
let (storage_addr) = addr({args})
storage_write(address=storage_addr, value=value)
return ()
"""
    return generate_storage_var_functions(
        elm, addr_func_body=addr_func_body, read_func_body=read_func_body,
        write_func_body=write_func_body)


def storage_var_name_to_base_addr(var_name: str) -> int:
    """
    Returns the base address of a StarkNet Storage variable, ignoring the storage var arguments.
    """

    return get_storage_var_address(var_name=var_name)


def is_storage_var(elm: CodeElementFunction) -> Tuple[bool, Optional[Location]]:
    """
    Returns whether the given function has the storage var decorator. If it does, the location of
    the decorator is returned.
    """
    for decorator in elm.decorators:
        if decorator.name == STORAGE_VAR_DECORATOR:
            return True, decorator.location
    return False, None


class StorageVarDeclVisitor(IdentifierAwareVisitor):
    """
    Replaces @storage_var decorated functions with a namespace with empty functions.
    After the struct collection phase is completed, those functions will be replaced by
    functions will full implementation.
    """

    def _visit_default(self, obj):
        return obj

    def visit_CodeElementFunction(self, elm: CodeElementFunction):
        storage_var, storage_var_location = is_storage_var(elm)
        if storage_var:
            if self.file_lang != STARKNET_LANG_DIRECTIVE:
                raise PreprocessorError(
                    '@storage_var can only be used in source files that contain the '
                    '"%lang starknet" directive.',
                    location=storage_var_location)
            # Add dummy references and calls that will be visited by the identifier collector
            # and the dependency graph.
            # Those statements will later be replaced by the real implementation.
            addr_func_body = """
let res = 0
call hash2
"""
            read_func_body = """
let storage_addr = 0
call addr
call storage_read
"""
            write_func_body = """
let storage_addr = 0
call addr
call storage_write
"""
            return generate_storage_var_functions(
                elm, addr_func_body=addr_func_body, read_func_body=read_func_body,
                write_func_body=write_func_body)

        return elm


class StorageVarImplentationVisitor(IdentifierAwareVisitor):
    """
    Replaces @storage_var decorated functions (obtained from the additional attribute
    STORAGE_VAR_ATTR added by StorageVarDeclVisitor) with a namespace with read() and write()
    functions.
    """

    def _visit_default(self, obj):
        return obj

    def visit_CodeElementFunction(self, elm: CodeElementFunction):
        attr = elm.additional_attributes.get(STORAGE_VAR_ATTR)
        if attr is None:
            return elm

        assert isinstance(attr, CodeElementFunction)
        return process_storage_var(attr)
