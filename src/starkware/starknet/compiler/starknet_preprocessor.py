import dataclasses
from typing import Any, Dict, List, Optional, Tuple

from starkware.cairo.lang.compiler.ast.cairo_types import (
    CairoType,
    TypeFelt,
    TypePointer,
    TypeStruct,
)
from starkware.cairo.lang.compiler.ast.code_elements import (
    BuiltinsDirective,
    CodeElementCompoundAssertEq,
    CodeElementFuncCall,
    CodeElementFunction,
    CodeElementHint,
    CodeElementInstruction,
    LangDirective,
)
from starkware.cairo.lang.compiler.ast.expr import (
    ArgList,
    ExprAssignment,
    ExprCast,
    ExprConst,
    ExprDeref,
    Expression,
    ExprHint,
    ExprIdentifier,
    ExprOperator,
    ExprReg,
)
from starkware.cairo.lang.compiler.ast.instructions import (
    AddApInstruction,
    InstructionAst,
    RetInstruction,
)
from starkware.cairo.lang.compiler.ast.rvalue import RvalueFuncCall
from starkware.cairo.lang.compiler.ast.types import TypedIdentifier
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.identifier_definition import (
    AliasDefinition,
    FunctionDefinition,
    FutureIdentifierDefinition,
    StructDefinition,
)
from starkware.cairo.lang.compiler.identifier_utils import get_struct_definition
from starkware.cairo.lang.compiler.instruction import Register
from starkware.cairo.lang.compiler.preprocessor.preprocessor import (
    PreprocessedProgram,
    Preprocessor,
)
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.program import CairoHint
from starkware.cairo.lang.compiler.references import create_simple_ref_expr
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.type_system import is_type_resolved
from starkware.starknet.compiler.data_encoder import (
    EncodingType,
    decode_data,
    struct_to_argument_info_list,
)
from starkware.starknet.definitions.constants import STARKNET_LANG_DIRECTIVE
from starkware.starknet.public.abi_structs import (
    prepare_type_for_abi,
    struct_definition_to_abi_entry,
)
from starkware.starknet.security.secure_hints import HintsWhitelist, InsecureHintError
from starkware.starknet.services.api.contract_definition import SUPPORTED_BUILTINS
from starkware.starkware_utils.subsequence import is_subsequence

EXTERNAL_DECORATOR = "external"
L1_HANDLER_DECORATOR = "l1_handler"
VIEW_DECORATOR = "view"
WRAPPER_SCOPE = ScopedName.from_string("__wrappers__")

ENTRY_POINT_DECORATORS = {EXTERNAL_DECORATOR, L1_HANDLER_DECORATOR, VIEW_DECORATOR}


@dataclasses.dataclass
class StarknetPreprocessedProgram(PreprocessedProgram):
    # JSON dict that contains information on the callable functions in the contract.
    abi: Any


class StarknetPreprocessor(Preprocessor):
    def __init__(self, **kwargs):
        kwargs = dict(kwargs)
        supported_decorators = kwargs.pop("supported_decorators", ENTRY_POINT_DECORATORS)

        # A whitelist of allowed hints.
        # None means that any hint is allowed.
        self.hint_whitelist: Optional[HintsWhitelist] = kwargs.pop("hint_whitelist", None)

        super().__init__(supported_decorators=supported_decorators, **kwargs)

        # A mapping from name to offset in the os_context that is passed to the contract.
        # Unfortunately we need to process the builtins directive before we can initialize it.
        self.os_context: Optional[Dict[str, int]] = None
        # JSON dict for the ABI output.
        self.abi: List[dict] = []
        # A map from external struct (short) name to its ABI entry.
        self.abi_structs: Dict[str, dict] = {}
        # A map from external struct (short) name to the fully qualified name.
        self.abi_structs_fullnames: Dict[str, ScopedName] = {}

    def get_external_decorator(self, elm: CodeElementFunction) -> Optional[ExprIdentifier]:
        """
        If the function has one of the external decorators, returns it.
        Otherwise, returns None.
        """
        for decorator in elm.decorators:
            if decorator.name in ENTRY_POINT_DECORATORS:
                return decorator

        return None

    def visit_BuiltinsDirective(self, directive: BuiltinsDirective):
        super().visit_BuiltinsDirective(directive)
        assert self.builtins is not None

        if not is_subsequence(self.builtins, SUPPORTED_BUILTINS):
            raise PreprocessorError(
                f"{self.builtins} is not a subsequence of {SUPPORTED_BUILTINS}.",
                location=directive.location,
            )

    def visit_LangDirective(self, directive: LangDirective):
        if directive.name != STARKNET_LANG_DIRECTIVE:
            raise PreprocessorError(
                f"Unsupported %lang directive. Are you using the correct compiler?",
                location=directive.location,
            )

    def handle_missing_future_definition(self, name: ScopedName, location):
        if name.path[-1].startswith("__storage_var_temp"):
            return
        if name.path[-1].startswith("__calldata"):
            return
        if name.path[-1].startswith("__return_value"):
            return
        super().handle_missing_future_definition(name=name, location=location)

    def get_os_context(self) -> Dict[str, int]:
        if self.os_context is None:
            builtins = [] if self.builtins is None else self.builtins

            os_context = {"syscall_ptr": 0, "storage_ptr": 1}
            for index, builtin_name in enumerate(builtins, len(os_context)):
                ptr_name = f"{builtin_name}_ptr"
                assert (
                    os_context.setdefault(ptr_name, index) == index
                ), f"os_context.{ptr_name} was redefined."

            self.os_context = os_context
        return self.os_context

    def create_func_wrapper(self, elm: CodeElementFunction, func_alias_name: str):
        """
        Generates a wrapper that converts between the StarkNet contract ABI and the
        Cairo calling convention.

        Arguments:
        elm - the CodeElementFunction of the wrapped function.
        func_alias_name - an alias for the FunctionDefention in the current scope.
        """

        os_context = self.get_os_context()

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

        implicit_arguments = None

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
                args.append(
                    ExprAssignment(
                        identifier=typed_identifier.identifier,
                        expr=typed_identifier.identifier,
                        location=typed_identifier.location,
                    )
                )

            implicit_arguments = ArgList(
                args=args,
                notes=[],
                has_trailing_comma=True,
                location=elm.implicit_arguments.location,
            )

        return_args_exprs: List[Expression] = []

        # Create references.
        for ptr_name, index in os_context.items():
            ref_name = self.current_scope + ptr_name

            arg_identifier = implicit_arguments_identifiers.get(ptr_name)
            if arg_identifier is None:
                location: Optional[Location] = func_location
                cairo_type: CairoType = TypeFelt(location=location)
            else:
                location = arg_identifier.location
                cairo_type = self.resolve_type(arg_identifier.get_type())

            # Add a reference of the form
            # 'let ref_name = [cast(os_context_ptr + index, cairo_type*)]'.
            self.add_reference(
                name=ref_name,
                value=ExprDeref(
                    addr=ExprCast(
                        ExprOperator(
                            os_context_ptr,
                            "+",
                            ExprConst(index, location=location),
                            location=location,
                        ),
                        dest_type=TypePointer(pointee=cairo_type, location=cairo_type.location),
                        location=cairo_type.location,
                    ),
                    location=location,
                ),
                cairo_type=cairo_type,
                location=location,
                require_future_definition=False,
            )

            assert index == len(return_args_exprs), "Unexpected index."

            return_args_exprs.append(ExprIdentifier(name=ptr_name, location=func_location))

        arg_struct_def = self.get_struct_definition(
            name=ScopedName.from_string(func_alias_name) + CodeElementFunction.ARGUMENT_SCOPE,
            location=func_location,
        )

        code_elements, call_args = decode_data(
            data_ptr=calldata_ptr.format(),
            data_size=calldata_size.format(),
            arguments=struct_to_argument_info_list(arg_struct_def),
            encoding_type=EncodingType.CALLDATA,
            has_range_check_builtin="range_check_ptr" in os_context,
            location=func_location,
            identifiers=self.identifiers,
        )

        for code_element in code_elements:
            self.visit(code_element.code_elm)

        self.visit(
            CodeElementFuncCall(
                func_call=RvalueFuncCall(
                    func_ident=ExprIdentifier(name=func_alias_name, location=func_location),
                    arguments=call_args,
                    implicit_arguments=implicit_arguments,
                    location=func_location,
                )
            )
        )

        ret_struct_name = ScopedName.from_string(func_alias_name) + CodeElementFunction.RETURN_SCOPE
        ret_struct_type = self.resolve_type(TypeStruct(ret_struct_name, False))
        ret_struct_def = self.get_struct_definition(name=ret_struct_name, location=func_location)
        ret_struct_expr = create_simple_ref_expr(
            reg=Register.AP,
            offset=-ret_struct_def.size,
            cairo_type=ret_struct_type,
            location=func_location,
        )
        self.add_reference(
            name=self.current_scope + "ret_struct",
            value=ret_struct_expr,
            cairo_type=ret_struct_type,
            require_future_definition=False,
            location=func_location,
        )

        # Add function return values.
        retdata_size, retdata_ptr = self.process_retdata(
            ret_struct_ptr=ExprIdentifier(name="ret_struct"),
            ret_struct_type=ret_struct_type,
            struct_def=ret_struct_def,
            location=func_location,
        )
        return_args_exprs += [retdata_size, retdata_ptr]

        # Push the return values.
        self.push_compound_expressions(
            compound_expressions=[self.simplify_expr_as_felt(expr) for expr in return_args_exprs],
            location=func_location,
        )

        # Add a ret instruction.
        self.visit(
            CodeElementInstruction(
                instruction=InstructionAst(
                    body=RetInstruction(), inc_ap=False, location=func_location
                )
            )
        )

        # Add an entry to the ABI.
        external_decorator = self.get_external_decorator(elm)
        assert external_decorator is not None
        is_view = external_decorator.name == "view"

        if external_decorator.name == L1_HANDLER_DECORATOR:
            entry_type = "l1_handler"
        elif external_decorator.name in [EXTERNAL_DECORATOR, VIEW_DECORATOR]:
            entry_type = "function"
        else:
            raise NotImplementedError(f"Unsupported decorator {external_decorator.name}")

        entry_type = (
            "function" if external_decorator.name != L1_HANDLER_DECORATOR else L1_HANDLER_DECORATOR
        )
        self.add_abi_entry(
            name=elm.name,
            arg_struct_def=arg_struct_def,
            ret_struct_def=ret_struct_def,
            is_view=is_view,
            entry_type=entry_type,
        )

    def add_abi_entry(
        self,
        name: str,
        arg_struct_def: StructDefinition,
        ret_struct_def: StructDefinition,
        is_view: bool,
        entry_type: str,
    ):
        """
        Adds an entry describing the function to the contract's ABI.
        """
        inputs = []
        outputs = []
        for m_name, member in arg_struct_def.members.items():
            assert is_type_resolved(member.cairo_type)
            abi_type_info = prepare_type_for_abi(member.cairo_type)
            inputs.append(
                {
                    "name": m_name,
                    "type": abi_type_info.modified_type.format(),
                }
            )
            for struct_name in abi_type_info.structs:
                self.add_struct_to_abi(struct_name)
        for m_name, member in ret_struct_def.members.items():
            assert isinstance(member.cairo_type, TypeFelt)
            outputs.append(
                {
                    "name": m_name,
                    "type": "felt",
                }
            )
        res = {
            "name": name,
            "type": entry_type,
            "inputs": inputs,
            "outputs": outputs,
        }
        if is_view:
            res["stateMutability"] = "view"
        self.abi.append(res)

    def add_struct_to_abi(self, struct_name: ScopedName):
        """
        Adds the given struct (add all the structs mentioned in its members) to self.abi_structs.
        """

        struct_definition = get_struct_definition(
            struct_name=struct_name, identifier_manager=self.identifiers
        )

        short_name = struct_name.path[-1]

        if short_name in self.abi_structs:
            existing_full_name = self.abi_structs_fullnames[short_name]
            if existing_full_name != struct_name:
                raise PreprocessorError(
                    f"Found two external structs named {short_name}: "
                    f"{existing_full_name}, {struct_name}.",
                    location=struct_definition.location,
                )
            return

        abi_entry, inner_structs = struct_definition_to_abi_entry(
            struct_definition=struct_definition
        )

        self.abi_structs_fullnames[short_name] = struct_name
        self.abi_structs[short_name] = abi_entry

        # Visit the types of the inner structs recursively.
        for name in inner_structs:
            self.add_struct_to_abi(name)

    def get_program(self) -> StarknetPreprocessedProgram:
        program = super().get_program()
        return StarknetPreprocessedProgram(  # type: ignore
            **program.__dict__,
            abi=list(self.abi_structs.values()) + self.abi,
        )

    def process_retdata(
        self,
        ret_struct_ptr: Expression,
        ret_struct_type: CairoType,
        struct_def: StructDefinition,
        location: Optional[Location],
    ) -> Tuple[Expression, Expression]:
        """
        Processes the return values and return retdata_size and retdata_ptr.
        """

        # Verify all of the return types are felts.
        for _, member_def in struct_def.members.items():
            cairo_type = member_def.cairo_type
            if not isinstance(cairo_type, TypeFelt):
                raise PreprocessorError(
                    f"Unsupported argument type {cairo_type.format()}.",
                    location=cairo_type.location,
                )

        self.add_reference(
            name=self.current_scope + "retdata_ptr",
            value=ExprDeref(
                addr=ExprReg(reg=Register.AP),
                location=location,
            ),
            cairo_type=TypePointer(TypeFelt()),
            require_future_definition=False,
            location=location,
        )

        self.visit(
            CodeElementHint(
                hint=ExprHint(
                    hint_code="memory[ap] = segments.add()",
                    n_prefix_newlines=0,
                    location=location,
                ),
                location=location,
            )
        )

        # Skip check of hint whitelist as it fails before the workaround below.
        super().visit_CodeElementInstruction(
            CodeElementInstruction(
                InstructionAst(body=AddApInstruction(ExprConst(1)), inc_ap=False, location=location)
            )
        )

        # Remove the references from the last instruction's flow tracking as they are
        # not needed by the hint and they cause the hint whitelist to fail.
        assert len(self.instructions[-1].hints) == 1
        hint, hint_flow_tracking_data = self.instructions[-1].hints[0]
        self.instructions[-1].hints[0] = hint, dataclasses.replace(
            hint_flow_tracking_data, reference_ids={}
        )
        self.visit(
            CodeElementCompoundAssertEq(
                ExprDeref(ExprCast(ExprIdentifier("retdata_ptr"), TypePointer(ret_struct_type))),
                ret_struct_ptr,
            )
        )

        return (ExprConst(struct_def.size), ExprIdentifier("retdata_ptr"))

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
        super().visit_CodeElementFunction(elm)

        external_decorator = self.get_external_decorator(elm)
        if external_decorator is None:
            return

        if self.file_lang != STARKNET_LANG_DIRECTIVE:
            raise PreprocessorError(
                "External decorators can only be used in source files that contain the "
                '"%lang starknet" directive.',
                location=external_decorator.location,
            )

        location = elm.identifier.location

        # Retrieve the canonical name of the function before switching scopes.
        _, func_canonical_name = self.get_label(elm.name, location=location)
        assert func_canonical_name is not None

        scope = WRAPPER_SCOPE

        if external_decorator.name == L1_HANDLER_DECORATOR:
            self.validate_l1_handler_signature(elm)

        self.flow_tracking.revoke()
        with self.scoped(scope, parent=elm), self.set_reference_states({}):
            current_wrapper_scope = self.current_scope + elm.name

            self.add_name_definition(
                current_wrapper_scope,
                FunctionDefinition(  # type: ignore
                    pc=self.current_pc,
                    decorators=[identifier.name for identifier in elm.decorators],
                ),
                location=elm.identifier.location,
                require_future_definition=False,
            )

            with self.scoped(current_wrapper_scope, parent=elm):
                # Generate an alias that will allow us to call the original function.
                func_alias_name = f"__wrapped_func"
                alias_canonical_name = current_wrapper_scope + func_alias_name
                self.add_future_definition(
                    name=alias_canonical_name,
                    future_definition=FutureIdentifierDefinition(identifier_type=AliasDefinition),
                )

                self.add_name_definition(
                    name=alias_canonical_name,
                    identifier_definition=AliasDefinition(destination=func_canonical_name),
                    location=location,
                )

                self.create_func_wrapper(elm=elm, func_alias_name=func_alias_name)

    def visit_CodeElementInstruction(self, elm: CodeElementInstruction):
        if self.hint_whitelist is not None:
            for hint, flow_tracking_data in self.next_instruction_hints:
                try:
                    self.hint_whitelist.verify_hint_secure(
                        hint=CairoHint(
                            code=hint.hint_code,
                            accessible_scopes=self.accessible_scopes,
                            flow_tracking_data=flow_tracking_data,
                        ),
                        reference_manager=self.flow_tracking.reference_manager,
                    )
                except InsecureHintError:
                    raise PreprocessorError(
                        """\
Hint is not whitelisted.
This may indicate that this library function cannot be used in StarkNet contracts.""",
                        location=hint.location,
                    )

        super().visit_CodeElementInstruction(elm)
