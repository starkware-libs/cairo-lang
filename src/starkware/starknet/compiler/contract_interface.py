import dataclasses
from typing import Callable, List, Optional, Tuple

from starkware.cairo.lang.compiler.ast.code_elements import (
    CodeBlock,
    CodeElementEmptyLine,
    CodeElementFunction,
    CommentedCodeElement,
)
from starkware.cairo.lang.compiler.error_handling import Location, ParentLocation
from starkware.cairo.lang.compiler.parser import ParserContext
from starkware.cairo.lang.compiler.preprocessor.identifier_aware_visitor import (
    IdentifierAwareVisitor,
)
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.preprocessor.preprocessor_utils import (
    autogen_parse_code_block,
    verify_empty_code_block,
)
from starkware.starknet.compiler.data_encoder import (
    ArgumentInfo,
    EncodingType,
    decode_data,
    encode_data,
)
from starkware.starknet.definitions.constants import STARKNET_LANG_DIRECTIVE
from starkware.starknet.public.abi import get_selector_from_name

CONTRACT_INTERFACE_DECORATOR = "contract_interface"
CONTRACT_INTERFACE_ATTR = "contract_interface"
AUTOGEN_PREFIX = "autogen/starknet/contract_interface/"


@dataclasses.dataclass
class ContractFunctionInfo:
    """
    Represents information about a function in a @contract_interface decorated namespace
    that can be collected before the struct collection phase.
    """

    # The original code element.
    elm: CodeElementFunction
    # A parent location to be used in case of errors concerning the function.
    parent_location: ParentLocation
    # The name of the selector constant of the function.
    selector: str
    # The name of the auto-generated file for code segments related to this function.
    autogen_code_name: str

    @property
    def name(self):
        """
        Returns the name of the function.
        """
        return self.elm.name

    @staticmethod
    def from_code_element(contract_name: str, elm: CodeElementFunction) -> "ContractFunctionInfo":
        name = elm.identifier.name
        func_location = elm.identifier.location
        assert func_location is not None

        if len(elm.decorators) != 0:
            raise PreprocessorError(
                "Unexpected decorator for a contract interface function.",
                location=elm.decorators[0].location,
            )

        verify_empty_code_block(
            code_block=elm.code_block,
            error_message="Contract interface functions must have an empty body.",
            default_location=elm.identifier.location,
        )

        if elm.implicit_arguments is not None and len(elm.implicit_arguments.identifiers) != 0:
            raise PreprocessorError(
                "Contract interface functions must have no implicit arguments.",
                location=elm.implicit_arguments.location,
            )

        return ContractFunctionInfo(
            elm=elm,
            parent_location=(func_location, "While handling contract interface function:"),
            selector=f"{name.upper()}_SELECTOR",
            autogen_code_name=AUTOGEN_PREFIX + f"{contract_name}/{name}",
        )


@dataclasses.dataclass
class ContractInterfaceInfo:
    """
    Represents information about a @contract_interface decorated namespace that can be collected
    before the struct collection phase.
    """

    name: str
    # A parent location to be used in case of errors concerning the contract.
    parent_location: ParentLocation
    functions: List[ContractFunctionInfo]

    @staticmethod
    def from_code_element(elm: CodeElementFunction) -> "ContractInterfaceInfo":
        # Ensure it's a namespace.
        if elm.element_type != "namespace":
            raise PreprocessorError(
                f"@{CONTRACT_INTERFACE_DECORATOR} can only be used with namespaces.",
                location=elm.identifier.location,
            )

        # Make sure there are no decorators other than CONTRACT_INTERFACE_DECORATOR.
        for decorator in elm.decorators:
            if decorator.name != CONTRACT_INTERFACE_DECORATOR:
                raise PreprocessorError(
                    f"Unexpected decorator for a contract interface.",
                    location=decorator.location,
                )

        contract_name = elm.identifier.name
        contract_name_location = elm.identifier.location
        assert contract_name_location is not None

        functions: List[ContractFunctionInfo] = []
        for commented_func_code_elm in elm.code_block.code_elements:
            func_code_elm = commented_func_code_elm.code_elm
            if isinstance(func_code_elm, CodeElementEmptyLine):
                continue
            is_func = (
                isinstance(func_code_elm, CodeElementFunction)
                and func_code_elm.element_type == "func"
            )
            if not is_func:
                error_location = (
                    elm.identifier.location
                    if commented_func_code_elm.location is None
                    else commented_func_code_elm.location
                )
                raise PreprocessorError(
                    "Only functions are supported within a contract interface.",
                    location=error_location,
                )

            assert isinstance(func_code_elm, CodeElementFunction)
            functions.append(ContractFunctionInfo.from_code_element(contract_name, func_code_elm))

        return ContractInterfaceInfo(
            name=contract_name,
            parent_location=(contract_name_location, "While handling contract interface:"),
            functions=functions,
        )


def process_contract_function(
    function_info: ContractFunctionInfo, func_body: CodeBlock
) -> List[CommentedCodeElement]:
    func_code_elm = function_info.elm
    selector_value = get_selector_from_name(function_info.name)
    code = f"""\
const {function_info.selector} = {selector_value}
func {function_info.name}{{syscall_ptr : felt*, storage_ptr : Storage*, range_check_ptr}}(
    contract_address : felt):
end
"""

    code_block = autogen_parse_code_block(
        path=function_info.autogen_code_name,
        code=code,
        parser_context=ParserContext(
            parent_location=function_info.parent_location,
        ),
    )

    call_func = code_block.code_elements[1].code_elm
    assert isinstance(call_func, CodeElementFunction)
    call_func.arguments = dataclasses.replace(
        func_code_elm.arguments,
        identifiers=call_func.arguments.identifiers + func_code_elm.arguments.identifiers,
    )
    call_func.returns = func_code_elm.returns
    call_func.code_block = func_body

    return code_block.code_elements


def generate_contract_interface_namespace(
    contract_info: ContractInterfaceInfo,
    func_body_callback: Callable[[ContractFunctionInfo], CodeBlock],
) -> CodeElementFunction:
    contract_name = contract_info.name

    code = f"""\
namespace {contract_name}:
    from starkware.cairo.common.alloc import alloc
    from starkware.cairo.common.memcpy import memcpy
    from starkware.starknet.common.storage import Storage
    from starkware.starknet.common.syscalls import call_contract
end
"""

    code_block = autogen_parse_code_block(
        path=AUTOGEN_PREFIX + contract_name,
        code=code,
        parser_context=ParserContext(
            parent_location=contract_info.parent_location,
        ),
    )
    assert len(code_block.code_elements) == 1
    res = code_block.code_elements[0].code_elm
    assert isinstance(res, CodeElementFunction) and res.element_type == "namespace"

    for function_info in contract_info.functions:
        res.code_block.code_elements += process_contract_function(
            function_info=function_info,
            func_body=func_body_callback(function_info),
        )

    res.additional_attributes[CONTRACT_INTERFACE_ATTR] = contract_info

    return res


def is_contract_interface(elm: CodeElementFunction) -> Tuple[bool, Optional[Location]]:
    """
    Returns whether the given namespace has the contract_interface decorator.
    If it does, the location of the decorator is returned.
    """
    for decorator in elm.decorators:
        if decorator.name == CONTRACT_INTERFACE_DECORATOR:
            return True, decorator.location
    return False, None


class ContractInterfaceDeclVisitor(IdentifierAwareVisitor):
    """
    Replaces @contract_interface decorated namespaces with a namespace with dummy functions.
    After the struct collection phase is completed, those functions will be replaced by
    functions will full implementation.
    """

    def _visit_default(self, obj):
        return obj

    def visit_CodeElementFunction(self, elm: CodeElementFunction):
        contract_interface, contract_interface_location = is_contract_interface(elm)
        if contract_interface:
            if self.file_lang != STARKNET_LANG_DIRECTIVE:
                raise PreprocessorError(
                    "@contract_interface can only be used in source files that contain the "
                    '"%lang starknet" directive.',
                    location=contract_interface_location,
                )
            return generate_contract_interface_namespace(
                ContractInterfaceInfo.from_code_element(elm),
                func_body_callback=self.generate_contract_function_body,
            )

        return elm

    def generate_contract_function_body(self, function_info: ContractFunctionInfo):
        # Add dummy references and calls that will be visited by the identifier collector
        # and the dependency graph.
        # Those statements will later be replaced by the real implementation.
        code = """
let calldata_ptr_start = 0
let retdata_size = 0
let retdata = 0
call alloc
call memcpy
call call_contract
"""
        return autogen_parse_code_block(
            path=function_info.autogen_code_name,
            code=code,
            parser_context=ParserContext(
                parent_location=function_info.parent_location,
            ),
        )


def non_optional_location(location: Optional[Location]) -> Location:
    assert location is not None
    return location


class ContractInterfaceImplentationVisitor(IdentifierAwareVisitor):
    """
    Replaces @contract_interface decorated namespaces (obtained from the additional attribute
    CONTRACT_INTERFACE_ATTR added by ContractInterfaceDeclVisitor) with a namespace with
    generated code that calls the call_contract() system call.
    """

    def _visit_default(self, obj):
        return obj

    def visit_CodeElementFunction(self, elm: CodeElementFunction):
        attr = elm.additional_attributes.get(CONTRACT_INTERFACE_ATTR)
        if attr is None:
            return elm

        assert isinstance(attr, ContractInterfaceInfo)

        return generate_contract_interface_namespace(
            attr,
            func_body_callback=self.generate_contract_function_body,
        )

    def generate_contract_function_body(self, function_info: ContractFunctionInfo):
        def get_code_elements(code: str) -> List[CommentedCodeElement]:
            return autogen_parse_code_block(
                path=function_info.autogen_code_name,
                code=code,
                parser_context=ParserContext(
                    parent_location=function_info.parent_location,
                ),
            ).code_elements

        code_elements: List[CommentedCodeElement] = []
        code_elements += get_code_elements(
            code=f"""
alloc_locals
let (local calldata_ptr_start : felt*) = alloc()
let __calldata_ptr = calldata_ptr_start
"""
        )

        # Handle inputs.
        args = [
            ArgumentInfo(
                name=typed_identifier.identifier.name,
                cairo_type=self.resolve_type(typed_identifier.get_type()),
                location=non_optional_location(typed_identifier.identifier.location),
            )
            for typed_identifier in function_info.elm.arguments.identifiers
        ]
        code_elements += encode_data(
            arguments=args,
            encoding_type=EncodingType.CALLDATA,
            has_range_check_builtin=True,
            identifiers=self.identifiers,
        )

        code_elements += get_code_elements(
            code=f"""
let (retdata_size, retdata) = call_contract(
    contract_address=contract_address,
    function_selector={function_info.selector},
    calldata_size=__calldata_ptr - calldata_ptr_start,
    calldata=calldata_ptr_start)
"""
        )

        # Handle outputs.

        return_str = ""
        if function_info.elm.returns is not None:
            rets = [
                ArgumentInfo(
                    name=typed_identifier.identifier.name,
                    cairo_type=typed_identifier.get_type(),
                    location=non_optional_location(typed_identifier.identifier.location),
                )
                for typed_identifier in function_info.elm.returns.identifiers
            ]
            ret_elements, ret_arg_list = decode_data(
                data_ptr="retdata",
                data_size="retdata_size",
                arguments=rets,
                encoding_type=EncodingType.RETURN,
                has_range_check_builtin=True,
                location=function_info.parent_location[0],
                identifiers=self.identifiers,
            )
            # Update the return values.
            return_str = ret_arg_list.format()
            code_elements += [code_elm for code_elm in ret_elements]

        code_elements += get_code_elements(
            code=f"""
return ({return_str})
"""
        )

        return CodeBlock(code_elements=code_elements)
