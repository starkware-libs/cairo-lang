import dataclasses
from typing import Any, Dict, List, Optional, Tuple

from starkware.cairo.lang.compiler.ast.cairo_types import (
    CairoType, TypeFelt, TypePointer, TypeStruct)
from starkware.cairo.lang.compiler.ast.code_elements import (
    BuiltinsDirective, CodeElementCompoundAssertEq, CodeElementFuncCall, CodeElementFunction,
    CodeElementHint, CodeElementInstruction, LangDirective)
from starkware.cairo.lang.compiler.ast.expr import (
    ArgList, ExprAssignment, ExprCast, ExprConst, ExprDeref, Expression, ExprIdentifier,
    ExprOperator, ExprReg)
from starkware.cairo.lang.compiler.ast.instructions import (
    AddApInstruction, InstructionAst, RetInstruction)
from starkware.cairo.lang.compiler.ast.rvalue import RvalueFuncCall
from starkware.cairo.lang.compiler.ast.types import TypedIdentifier
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.identifier_definition import (
    AliasDefinition, FunctionDefinition, FutureIdentifierDefinition, StructDefinition)
from starkware.cairo.lang.compiler.instruction import Register
from starkware.cairo.lang.compiler.preprocessor.preprocessor import (
    PreprocessedProgram, Preprocessor)
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.program import CairoHint
from starkware.cairo.lang.compiler.references import create_simple_ref_expr
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.starknet.compiler.calldata_parser import process_calldata
from starkware.starknet.definitions.constants import STARKNET_LANG_DIRECTIVE
from starkware.starknet.security.secure_hints import HintsWhitelist, InsecureHintError

EXTERNAL_DECORATOR = 'external'
VIEW_DECORATOR = 'view'
WRAPPER_SCOPE = ScopedName.from_string('__wrappers__')


@dataclasses.dataclass
class StarknetPreprocessedProgram(PreprocessedProgram):
    # JSON dict that contains information on the callable functions in the contract.
    abi: Any


class StarknetPreprocessor(Preprocessor):
    def __init__(self, **kwargs):
        kwargs = dict(kwargs)
        supported_decorators = kwargs.pop('supported_decorators', {
            EXTERNAL_DECORATOR, VIEW_DECORATOR})

        # A whitelist of allowed hints.
        # None means that any hint is allowed.
        self.hint_whitelist: Optional[HintsWhitelist] = kwargs.pop('hint_whitelist', None)

        super().__init__(supported_decorators=supported_decorators, **kwargs)

        # A mapping from name to offset in the os_context that is passed to the contract.
        # Unfortunately we need to process the builtins directive before we can initialize it.
        self.os_context: Optional[Dict[str, int]] = None
        # JSON dict for the ABI output.
        self.abi: List[dict] = []

    def get_external_decorator(self, elm: CodeElementFunction) -> Optional[ExprIdentifier]:
        """
        If the function has the @external or @view decorator, returns it.
        Otherwise, returns None.
        """
        for decorator in elm.decorators:
            if decorator.name in [EXTERNAL_DECORATOR, VIEW_DECORATOR]:
                return decorator

        return None

    def visit_BuiltinsDirective(self, directive: BuiltinsDirective):
        super().visit_BuiltinsDirective(directive)
        assert self.builtins is not None
        if 'storage' in self.builtins:
            raise PreprocessorError(
                "'storage' may not appear in the builtins directive.",
                location=directive.location)

    def visit_LangDirective(self, directive: LangDirective):
        if directive.name != STARKNET_LANG_DIRECTIVE:
            raise PreprocessorError(
                f'Unsupported %lang directive. Are you using the correct compiler?',
                location=directive.location,
            )

    def get_os_context(self) -> Dict[str, int]:
        if self.os_context is None:
            builtins = [] if self.builtins is None else self.builtins

            os_context = {'storage_ptr': 0}
            for index, builtin_name in enumerate(builtins, len(os_context)):
                ptr_name = f'{builtin_name}_ptr'
                assert os_context.setdefault(ptr_name, index) == index, \
                    f'os_context.{ptr_name} was redefined.'

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

        # We expect the call stack to look as follows:
        # pointer to builtins struct.
        # pointer to the call data array.
        # ret_fp.
        # ret_pc.
        builtins_ptr = ExprDeref(
            addr=ExprOperator(
                ExprReg(reg=Register.FP, location=func_location),
                '+',
                ExprConst(-4, location=func_location),
                location=func_location),
            location=func_location)
        calldata_ptr = ExprDeref(
            addr=ExprOperator(
                ExprReg(reg=Register.FP, location=func_location),
                '+',
                ExprConst(-3, location=func_location),
                location=func_location),
            location=func_location)

        implicit_arguments = None

        implicit_arguments_identifiers: Dict[str, TypedIdentifier] = {}
        if elm.implicit_arguments is not None:
            args = []
            for typed_identifier in elm.implicit_arguments.identifiers:
                ptr_name = typed_identifier.name
                if ptr_name not in os_context:
                    raise PreprocessorError(
                        f"Unexpected implicit argument '{ptr_name}' in an external function.",
                        location=typed_identifier.identifier.location)

                implicit_arguments_identifiers[ptr_name] = typed_identifier

                # Add the assignment expression 'ptr_name = ptr_name' to the implicit arg list.
                args.append(ExprAssignment(
                    identifier=typed_identifier.identifier,
                    expr=typed_identifier.identifier,
                    location=typed_identifier.location,
                ))

            implicit_arguments = ArgList(
                args=args, notes=[], has_trailing_comma=True,
                location=elm.implicit_arguments.location)

        return_args_exprs: List[Expression] = []

        # Create references.
        for ptr_name, index in os_context.items():
            ref_name = self.current_scope + ptr_name

            arg_identifier = implicit_arguments_identifiers.get(ptr_name)
            if arg_identifier is None:
                location = func_location
                cairo_type: CairoType = TypeFelt(location=location)
            else:
                location = arg_identifier.location
                cairo_type = self.resolve_type(arg_identifier.get_type())

            # Add a reference of the form
            # 'let ref_name = [cast(builtins_ptr + index, cairo_type*)]'.
            self.add_reference(
                name=ref_name,
                value=ExprDeref(
                    addr=ExprCast(
                        ExprOperator(
                            builtins_ptr, '+', ExprConst(index, location=location),
                            location=location),
                        dest_type=TypePointer(pointee=cairo_type, location=cairo_type.location),
                        location=cairo_type.location),
                    location=location),
                cairo_type=cairo_type,
                location=location,
                require_future_definition=False)

            assert index == len(return_args_exprs), 'Unexpected index.'

            return_args_exprs.append(ExprIdentifier(name=ptr_name, location=func_location))

        arg_struct_def = self.get_struct_definition(
            name=ScopedName.from_string(func_alias_name) + CodeElementFunction.ARGUMENT_SCOPE,
            location=func_location)
        self.visit(CodeElementFuncCall(
            func_call=RvalueFuncCall(
                func_ident=ExprIdentifier(name=func_alias_name, location=func_location),
                arguments=process_calldata(
                    calldata_ptr=calldata_ptr,
                    identifiers=self.identifiers,
                    struct_def=arg_struct_def
                ),
                implicit_arguments=implicit_arguments,
                location=func_location)))

        ret_struct_name = ScopedName.from_string(func_alias_name) + CodeElementFunction.RETURN_SCOPE
        ret_struct_type = self.resolve_type(TypeStruct(ret_struct_name, False))
        ret_struct_def = self.get_struct_definition(
            name=ret_struct_name,
            location=func_location)
        ret_struct_expr = create_simple_ref_expr(
            reg=Register.AP, offset=-ret_struct_def.size, cairo_type=ret_struct_type,
            location=func_location)
        self.add_reference(
            name=self.current_scope + 'ret_struct',
            value=ret_struct_expr,
            cairo_type=ret_struct_type,
            require_future_definition=False,
            location=func_location)

        # Add function return values.
        retdata_size, retdata_ptr = self.process_retdata(
            ret_struct_ptr=ExprIdentifier(name='ret_struct'),
            ret_struct_type=ret_struct_type, struct_def=ret_struct_def,
            location=func_location,
        )
        return_args_exprs += [retdata_size, retdata_ptr]

        # Push the return values.
        self.push_compound_expressions(
            compound_expressions=[self.simplify_expr_as_felt(expr) for expr in return_args_exprs],
            location=func_location,
        )

        # Add a ret instruction.
        self.visit(CodeElementInstruction(
            instruction=InstructionAst(
                body=RetInstruction(),
                inc_ap=False,
                location=func_location)))

        # Add an entry to the ABI.
        external_decorator = self.get_external_decorator(elm)
        assert external_decorator is not None
        is_view = external_decorator.name == 'view'
        self.add_abi_entry(
            name=elm.name, arg_struct_def=arg_struct_def, ret_struct_def=ret_struct_def,
            is_view=is_view)

    def add_abi_entry(
            self, name: str, arg_struct_def: StructDefinition, ret_struct_def: StructDefinition,
            is_view: bool):
        """
        Adds an entry describing the function to the contract's ABI.
        """
        inputs = []
        outputs = []
        for m_name, member in arg_struct_def.members.items():
            assert isinstance(member.cairo_type, TypeFelt)
            inputs.append({
                'name': m_name,
                'type': 'felt',
            })
        for m_name, member in ret_struct_def.members.items():
            assert isinstance(member.cairo_type, TypeFelt)
            outputs.append({
                'name': m_name,
                'type': 'felt',
            })
        res = {
            'name': name,
            'type': 'function',
            'inputs': inputs,
            'outputs': outputs,
        }
        if is_view:
            res['stateMutability'] = 'view'
        self.abi.append(res)

    def get_program(self) -> StarknetPreprocessedProgram:
        program = super().get_program()
        return StarknetPreprocessedProgram(  # type: ignore
            **program.__dict__,
            abi=self.abi,
        )

    def process_retdata(
            self, ret_struct_ptr: Expression, ret_struct_type: CairoType,
            struct_def: StructDefinition,
            location: Optional[Location]) -> Tuple[Expression, Expression]:
        """
        Processes the return values and return retdata_size and retdata_ptr.
        """

        # Verify all of the return types are felts.
        for _, member_def in struct_def.members.items():
            cairo_type = member_def.cairo_type
            if not isinstance(cairo_type, TypeFelt):
                raise PreprocessorError(
                    f'Unsupported argument type {cairo_type.format()}.',
                    location=cairo_type.location)

        self.add_reference(
            name=self.current_scope + 'retdata_ptr',
            value=ExprDeref(
                addr=ExprReg(reg=Register.AP),
                location=location,
            ),
            cairo_type=TypePointer(TypeFelt()),
            require_future_definition=False,
            location=location)

        self.visit(CodeElementHint(
            hint_code='memory[ap] = segments.add()', n_prefix_newlines=0, location=location))

        # Skip check of hint whitelist as it fails before the workaround below.
        super().visit_CodeElementInstruction(CodeElementInstruction(InstructionAst(
            body=AddApInstruction(ExprConst(1)),
            inc_ap=False,
            location=location)))

        # Remove the references from the last instruction's flow tracking as they are
        # not needed by the hint and they cause the hint whitelist to fail.
        self.instructions[-1].flow_tracking_data = dataclasses.replace(
            self.instructions[-1].flow_tracking_data, reference_ids={})
        self.visit(CodeElementCompoundAssertEq(
            ExprDeref(
                ExprCast(ExprIdentifier('retdata_ptr'), TypePointer(ret_struct_type))),
            ret_struct_ptr))

        return (ExprConst(struct_def.size), ExprIdentifier('retdata_ptr'))

    def visit_CodeElementFunction(self, elm: CodeElementFunction):
        super().visit_CodeElementFunction(elm)

        external_decorator = self.get_external_decorator(elm)
        if external_decorator is None:
            return

        location = elm.identifier.location

        # Retrieve the canonical name of the function before switching scopes.
        _, func_canonical_name = self.get_label(elm.name, location=location)
        assert func_canonical_name is not None

        self.flow_tracking.revoke()
        with self.scoped(WRAPPER_SCOPE, parent=elm), self.set_reference_states({}):
            current_wrapper_scope = self.current_scope + elm.name

            self.add_name_definition(
                current_wrapper_scope,
                FunctionDefinition(  # type: ignore
                    pc=self.current_pc,
                    decorators=[identifier.name for identifier in elm.decorators],
                ),
                location=elm.identifier.location,
                require_future_definition=False)

            with self.scoped(current_wrapper_scope, parent=elm):
                # Generate an alias that will allow us to call the original function.
                func_alias_name = f'__wrapped_func'
                alias_canonical_name = current_wrapper_scope + func_alias_name
                self.add_future_definition(
                    name=alias_canonical_name,
                    future_definition=FutureIdentifierDefinition(
                        identifier_type=AliasDefinition),
                )

                self.add_name_definition(
                    name=alias_canonical_name,
                    identifier_definition=AliasDefinition(destination=func_canonical_name),
                    location=location)

                self.create_func_wrapper(elm=elm, func_alias_name=func_alias_name)

    def visit_CodeElementInstruction(self, elm: CodeElementInstruction):
        if self.hint_whitelist is not None:
            hint = self.next_instruction_hint
            if hint is not None:
                try:
                    self.hint_whitelist.verify_hint_secure(
                        hint=CairoHint(
                            code=hint.hint_code,
                            accessible_scopes=self.accessible_scopes,
                            flow_tracking_data=self.flow_tracking.get(),
                        ),
                        reference_manager=self.flow_tracking.reference_manager)
                except InsecureHintError:
                    raise PreprocessorError(
                        """\
Hint is not whitelisted.
This may indicate that this library function cannot be used in StarkNet contracts.""",
                        location=hint.location)

        super().visit_CodeElementInstruction(elm)
