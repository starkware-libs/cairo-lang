import dataclasses
from typing import Dict, List, Optional, Tuple

from starkware.cairo.lang.compiler.ast.cairo_types import CairoType, TypeFelt
from starkware.cairo.lang.compiler.ast.code_elements import (
    CodeElementFunction,
    CodeElementReturnValueReference,
    CodeElementScoped,
    CodeElementWith,
    CommentedCodeElement,
)
from starkware.cairo.lang.compiler.ast.expr import (
    ExprConst,
    ExprDeref,
    ExprIdentifier,
    ExprOperator,
    ExprReg,
)
from starkware.cairo.lang.compiler.ast.types import TypedIdentifier
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.identifier_definition import AliasDefinition, StructDefinition
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.instruction import Register
from starkware.cairo.lang.compiler.parser import ParserContext
from starkware.cairo.lang.compiler.preprocessor.identifier_aware_visitor import (
    IdentifierAwareVisitor,
)
from starkware.cairo.lang.compiler.preprocessor.identifier_collector import IdentifierCollector
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.preprocessor.preprocessor_utils import autogen_parse_code_block
from starkware.cairo.lang.compiler.preprocessor.struct_collector import StructCollector
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.starknet.compiler.data_encoder import (
    DataEncoder,
    EncodingType,
    decode_data,
    struct_to_argument_info_list,
)
from starkware.starknet.definitions.constants import STARKNET_LANG_DIRECTIVE

EXTERNAL_DECORATOR = "external"
L1_HANDLER_DECORATOR = "l1_handler"
VIEW_DECORATOR = "view"
CONSTRUCTOR_DECORATOR = "constructor"

ENTRY_POINT_DECORATORS = {
    EXTERNAL_DECORATOR,
    L1_HANDLER_DECORATOR,
    VIEW_DECORATOR,
    CONSTRUCTOR_DECORATOR,
}

WRAPPER_SCOPE = ScopedName.from_string("__wrappers__")


def get_external_decorator(elm: CodeElementFunction) -> Optional[ExprIdentifier]:
    """
    If the function has one of the external decorators, returns it.
    Otherwise, returns None.
    """
    for decorator in elm.decorators:
        if decorator.name in ENTRY_POINT_DECORATORS:
            return decorator

    return None


def get_abi_entry_type(external_decorator_name: str) -> str:
    if external_decorator_name == L1_HANDLER_DECORATOR:
        return "l1_handler"
    elif external_decorator_name in [EXTERNAL_DECORATOR, VIEW_DECORATOR]:
        return "function"
    elif external_decorator_name == CONSTRUCTOR_DECORATOR:
        return "constructor"
    else:
        raise NotImplementedError(f"Unsupported decorator {external_decorator_name}")


class ExternalWrapperVisitor(IdentifierAwareVisitor):
    """
    Adds function wrappers for external functions (@external, @view, @l1_handler, ...)
    that converts between the StarkNet contract ABI and the Cairo calling convention.
    """

    def __init__(self, builtins: List[str], identifiers: Optional[IdentifierManager] = None):
        super().__init__(identifiers=identifiers)

        self.builtins = builtins

        # The constructor definition. Only one constructor is allowed.
        self.constructor: Optional[CodeElementFunction] = None

        # A mapping from name to offset in the os_context that is passed to the contract.
        self.os_context: Dict[str, int] = self.get_os_context(builtins=builtins)

    def _visit_default(self, obj):
        return obj

    @staticmethod
    def get_os_context(builtins) -> Dict[str, int]:
        os_context = {"syscall_ptr": 0}
        for index, builtin_name in enumerate(builtins, len(os_context)):
            ptr_name = f"{builtin_name}_ptr"
            assert (
                os_context.setdefault(ptr_name, index) == index
            ), f"os_context.{ptr_name} was redefined."

        return os_context

    def create_func_wrapper(
        self, elm: CodeElementFunction, func_alias_name: str
    ) -> List[CodeElementFunction]:
        """
        Generates a wrapper that converts between the StarkNet contract ABI and the
        Cairo calling convention.

        Arguments:
        elm - the CodeElementFunction of the wrapped function.
        func_alias_name - an alias for the FunctionDefinition in the current scope.
        """

        code_elements = []

        os_context = self.os_context

        # True if the generated function is using local variables.
        using_locals = False

        func_location = elm.identifier.location
        assert func_location is not None

        # We expect the call stack to look as follows:
        # pointer to os_context struct.
        # calldata size.
        # pointer to the call data array.
        # ret_fp.
        # ret_pc.
        os_context_ptr = ExprDeref(
            addr=ExprOperator(
                ExprReg(reg=Register.FP, location=func_location),
                "+",
                ExprConst(-5, location=func_location),
                location=func_location,
            ),
            location=func_location,
        )

        calldata_size = ExprDeref(
            addr=ExprOperator(
                ExprReg(reg=Register.FP, location=func_location),
                "+",
                ExprConst(-4, location=func_location),
                location=func_location,
            ),
            location=func_location,
        )

        calldata_ptr = ExprDeref(
            addr=ExprOperator(
                ExprReg(reg=Register.FP, location=func_location),
                "+",
                ExprConst(-3, location=func_location),
                location=func_location,
            ),
            location=func_location,
        )

        implicit_arguments = ""

        implicit_arguments_identifiers: Dict[str, TypedIdentifier] = {}
        if elm.implicit_arguments is not None:
            args = []
            for typed_identifier in elm.implicit_arguments.identifiers:
                ptr_name = typed_identifier.name
                if ptr_name not in os_context:
                    raise PreprocessorError(
                        f"Unexpected implicit argument '{ptr_name}' in an external function.",
                        location=typed_identifier.identifier.location,
                    )

                implicit_arguments_identifiers[ptr_name] = typed_identifier

                # Add the assignment expression 'ptr_name = ptr_name' to the implicit arg list.
                args.append(f"{ptr_name}={ptr_name}")

            implicit_arguments = ", ".join(args)

        return_args_decl: List[str] = []
        return_args_exprs: List[str] = []

        # Create references.
        for ptr_name, index in os_context.items():
            arg_identifier = implicit_arguments_identifiers.get(ptr_name)
            if arg_identifier is None:
                location: Location = func_location
                cairo_type: CairoType = TypeFelt(location=location)
            else:
                location = (
                    arg_identifier.location
                    if arg_identifier.location is not None
                    else func_location
                )
                cairo_type = self.resolve_type(arg_identifier.get_type())

            code_elements += autogen_parse_code_block(
                path=f"autogen/starknet/external/{elm.name}",
                code=(
                    f"let {ptr_name} = [cast({os_context_ptr.format()} + {index}, "
                    f"{cairo_type.format()}*)]\n"
                ),
                parser_context=ParserContext(
                    parent_location=(
                        location,
                        "While constructing the external wrapper for:",
                    ),
                    resolved_types=True,
                ),
            ).code_elements

            assert index == len(return_args_exprs), "Unexpected index."

            return_args_decl.append(f"{ptr_name} : {cairo_type.format()}")
            return_args_exprs.append(ptr_name)

        arg_struct_def = self.get_struct_definition(
            name=ScopedName.from_string(f"{elm.name}.{func_alias_name}")
            + CodeElementFunction.ARGUMENT_SCOPE,
            location=func_location,
        )

        # Prepare code for handling the arguments.
        decode_code_elements, call_args = decode_data(
            data_ptr=calldata_ptr.format(),
            data_size=calldata_size.format(),
            arguments=struct_to_argument_info_list(arg_struct_def),
            encoding_type=EncodingType.CALLDATA,
            has_range_check_builtin="range_check_ptr" in os_context,
            location=func_location,
            identifiers=self.identifiers,
        )

        # Prepare code for handling the return values.
        ret_struct_name = (
            ScopedName.from_string(f"{elm.name}.{func_alias_name}")
            + CodeElementFunction.RETURN_SCOPE
        )
        ret_struct_def = self.get_struct_definition(name=ret_struct_name, location=func_location)

        encode_return_func, known_ap_change = self.process_retdata(
            func_name=elm.name,
            struct_def=ret_struct_def,
            location=func_location,
        )

        # Prepare code for calling the original function.
        call_code = f"""\
let ret_struct = {func_alias_name}{{{implicit_arguments}}}({call_args.format()})
"""
        if not known_ap_change:
            # If the return value handling is expected to revoke ap tracking, copy the builtins into
            # local variables.
            for decl, name in zip(return_args_decl, return_args_exprs):
                if name in implicit_arguments_identifiers:
                    using_locals = True
                    call_code += f"local {decl} = {name}\n"
        if encode_return_func is not None:
            if "range_check_ptr" not in os_context:
                raise PreprocessorError(
                    "In order to use external functions, the '%builtins' directive must include "
                    "the 'range_check' builtin.",
                    location=func_location,
                )
            call_code += f"""\
let (range_check_ptr, retdata_size, retdata) = {elm.name}_encode_return(ret_struct, range_check_ptr)
"""
        else:
            call_code += """\
%{ memory[ap] = segments.add() %}        # Allocate memory for return value.
tempvar retdata : felt*
let retdata_size = 0
"""

        call_code_elements = autogen_parse_code_block(
            path=f"autogen/starknet/external/{elm.name}",
            code=call_code,
            parser_context=ParserContext(
                parent_location=(func_location, "While constructing the external wrapper for:"),
                resolved_types=False,
            ),
        ).code_elements
        # Override the location of call to the wrapped function, to simplify the error message
        # in case of printing the traceback.
        assert isinstance(call_code_elements[0].code_elm, CodeElementReturnValueReference)
        call_code_elements[0].code_elm.func_call = dataclasses.replace(
            call_code_elements[0].code_elm.func_call, location=func_location
        )

        code_elements += decode_code_elements
        code_elements += call_code_elements

        return_args_decl += ["size", "retdata : felt*"]
        return_args_exprs += ["retdata_size", "retdata"]

        code = f"""\
return ({",".join(return_args_exprs)})
"""

        code_elements += autogen_parse_code_block(
            path=f"autogen/starknet/external/{elm.name}",
            code=code,
            parser_context=ParserContext(
                parent_location=(func_location, "While constructing the external wrapper for:"),
                resolved_types=True,
            ),
        ).code_elements

        # Generate the function skeleton code.
        return_str = ", ".join(return_args_decl)
        code = f"""\
func {elm.name}() -> ({return_str}):
    {"alloc_locals" if using_locals else ""}
end
"""

        func_code_block = autogen_parse_code_block(
            path=f"autogen/starknet/external/{elm.name}",
            code=code,
            parser_context=ParserContext(
                parent_location=(func_location, "While constructing the external wrapper for:"),
                resolved_types=True,
            ),
        )

        # Use the collected code_elements as the function's body and copy the decorators.
        func_elm = func_code_block.code_elements[0].code_elm
        assert isinstance(func_elm, CodeElementFunction)
        func_elm.code_block.code_elements += code_elements
        func_elm.decorators = elm.decorators

        # Run identifier collector on the function.
        identifier_collector = IdentifierCollector(identifiers=self.identifiers)
        identifier_collector.accessible_scopes = list(self.accessible_scopes)
        if encode_return_func is not None:
            identifier_collector.visit(encode_return_func)
        identifier_collector.visit(func_code_block)

        # Run struct collector on the function.
        struct_collector = StructCollector(identifiers=self.identifiers)
        struct_collector.accessible_scopes = list(self.accessible_scopes)
        if encode_return_func is not None:
            struct_collector.visit(encode_return_func)
        struct_collector.visit(func_code_block)

        return ([] if encode_return_func is None else [encode_return_func]) + [func_elm]

    def process_retdata(
        self,
        func_name: str,
        struct_def: StructDefinition,
        location: Location,
    ) -> Tuple[Optional[CodeElementFunction], bool]:
        """
        Generates a function that processes the return values. Returns:
        1. The auto-generated function. None if there are no return values.
        2. Whether the ap change is known.
        """

        if len(struct_def.members) == 0:
            return None, True

        data_encoder = DataEncoder(
            arg_name_func=lambda arg_info: f"ret_struct.{arg_info.name}",
            encoding_type=EncodingType.RETURN,
            has_range_check_builtin="range_check_ptr" in self.os_context,
            identifiers=self.identifiers,
        )
        data_encoder.run(arguments=struct_to_argument_info_list(struct_def))

        func_elm = self.prepare_return_function(
            func_name=func_name,
            struct_def=struct_def,
            encoding_code_elements=data_encoder.code_elements,
            location=location,
        )

        return (
            func_elm,
            data_encoder.known_ap_change,
        )

    def prepare_return_function(
        self,
        func_name: str,
        struct_def: StructDefinition,
        encoding_code_elements: List[CommentedCodeElement],
        location: Location,
    ) -> CodeElementFunction:
        code = f"""\
func {func_name}_encode_return(ret_struct : {struct_def.full_name}, range_check_ptr) -> (
        range_check_ptr, data_len : felt, data : felt*):
    %{{ memory[ap] = segments.add() %}}
    alloc_locals
    local __return_value_ptr_start : felt*
    let __return_value_ptr = __return_value_ptr_start
    with range_check_ptr:
    end
    return (
        range_check_ptr=range_check_ptr,
        data_len=__return_value_ptr - __return_value_ptr_start,
        data=__return_value_ptr_start)
end
"""

        code_elements = autogen_parse_code_block(
            path=f"autogen/starknet/external/return/{func_name}",
            code=code,
            parser_context=ParserContext(
                parent_location=(location, "While handling return value of"),
                resolved_types=True,
            ),
        ).code_elements
        func_elm = code_elements[0].code_elm
        assert isinstance(func_elm, CodeElementFunction)

        # Insert the data encoding code in the with statement.
        with_elm = func_elm.code_block.code_elements[-2].code_elm
        assert isinstance(with_elm, CodeElementWith)
        with_elm.code_block.code_elements += encoding_code_elements

        return func_elm

    def validate_constructor_signature(self, elm: CodeElementFunction):
        """
        Validates the signature of the constructor.
        """

        if self.constructor is not None:
            previous_def_loc = self.constructor.identifier.location
            notes = (
                []
                if previous_def_loc is None
                else [
                    previous_def_loc.to_string_with_content(
                        "The constructor was previously defined here:"
                    )
                ]
            )

            raise PreprocessorError(
                "Multiple constructors definitions are not supported.",
                location=elm.identifier.location,
                notes=notes,
            )

        self.constructor = elm

        if elm.name != "constructor":
            raise PreprocessorError(
                "The constructor name must be 'constructor'.",
                location=elm.identifier.location,
            )

        if elm.returns is not None:
            raise PreprocessorError(
                "A constructor can not have a return value.", location=elm.returns.location
            )

    def validate_l1_handler_signature(self, elm: CodeElementFunction):
        """
        Validates the signature of an l1_handler.
        """

        args = elm.arguments.identifiers
        if len(args) == 0 or args[0].name != "from_address":
            # An empty argument list has no location so we point to the identifier.
            location = elm.identifier.location if len(args) == 0 else args[0].location
            raise PreprocessorError(
                "The first argument of an L1 handler must be named 'from_address'.",
                location=location,
            )

        from_address_type = args[0].get_type()
        if not isinstance(from_address_type, TypeFelt):
            raise PreprocessorError(
                "The type of 'from_address' must be felt.", location=from_address_type.location
            )

        if elm.returns is not None:
            raise PreprocessorError(
                "An L1 handler can not have a return value.", location=elm.returns.location
            )

    def visit_CodeElementFunction(self, elm: CodeElementFunction):
        external_decorator = get_external_decorator(elm)
        if external_decorator is None:
            return super().visit_CodeElementFunction(elm=elm)

        if self.file_lang != STARKNET_LANG_DIRECTIVE:
            raise PreprocessorError(
                "External decorators can only be used in source files that contain the "
                '"%lang starknet" directive.',
                location=external_decorator.location,
            )

        location = elm.identifier.location

        # Retrieve the canonical name of the function before switching scopes.
        func_canonical_name = self.current_scope + elm.name

        if external_decorator.name == L1_HANDLER_DECORATOR:
            self.validate_l1_handler_signature(elm)
        elif external_decorator.name == CONSTRUCTOR_DECORATOR:
            self.validate_constructor_signature(elm)

        # Generate an alias that will allow us to call the original function.
        func_alias_name = f"__wrapped_func"
        alias_canonical_name = WRAPPER_SCOPE + elm.name + func_alias_name

        self.add_name_definition(
            name=alias_canonical_name,
            identifier_definition=AliasDefinition(destination=func_canonical_name),
            location=location,
            require_future_definition=False,
        )
        self.add_name_definition(
            name=WRAPPER_SCOPE + (elm.name + "_encode_return") + "memcpy",
            identifier_definition=AliasDefinition(
                destination=ScopedName.from_string("starkware.cairo.common.memcpy.memcpy")
            ),
            location=location,
            require_future_definition=False,
        )

        with self.scoped(WRAPPER_SCOPE, parent=elm):
            wrapper_funcs = self.create_func_wrapper(elm=elm, func_alias_name=func_alias_name)

        return CodeElementScoped(
            scope=self.current_scope,
            code_elements=[
                elm,
                CodeElementScoped(scope=WRAPPER_SCOPE, code_elements=list(wrapper_funcs)),
            ],
        )
