import dataclasses
from contextlib import contextmanager
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple, cast

from starkware.cairo.lang.compiler.ast.arguments import IdentifierList
from starkware.cairo.lang.compiler.ast.cairo_types import (
    CairoType, CastType, TypeFelt, TypePointer, TypeStruct, TypeTuple)
from starkware.cairo.lang.compiler.ast.code_elements import (
    BuiltinsDirective, CodeBlock, CodeElement, CodeElementAllocLocals, CodeElementCompoundAssertEq,
    CodeElementConst, CodeElementDirective, CodeElementEmptyLine, CodeElementFuncCall,
    CodeElementFunction, CodeElementHint, CodeElementIf, CodeElementImport, CodeElementInstruction,
    CodeElementLabel, CodeElementLocalVariable, CodeElementMember, CodeElementReference,
    CodeElementReturn, CodeElementReturnValueReference, CodeElementStaticAssert,
    CodeElementTailCall, CodeElementTemporaryVariable, CodeElementUnpackBinding, CodeElementWith,
    LangDirective)
from starkware.cairo.lang.compiler.ast.expr import (
    ExprAssignment, ExprCast, ExprConst, ExprDeref, Expression, ExprFutureLabel, ExprIdentifier,
    ExprOperator, ExprReg, ExprTuple)
from starkware.cairo.lang.compiler.ast.expr_func_call import ExprFuncCall
from starkware.cairo.lang.compiler.ast.formatting_utils import get_max_line_length
from starkware.cairo.lang.compiler.ast.instructions import (
    AddApInstruction, AssertEqInstruction, CallInstruction, CallLabelInstruction, InstructionAst,
    InstructionBody, JnzInstruction, JumpInstruction, JumpToLabelInstruction, RetInstruction)
from starkware.cairo.lang.compiler.ast.module import CairoModule
from starkware.cairo.lang.compiler.ast.rvalue import RvalueCallInst, RvalueFuncCall
from starkware.cairo.lang.compiler.constants import SIZE_CONSTANT
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.expression_simplifier import ExpressionSimplifier
from starkware.cairo.lang.compiler.identifier_definition import (
    ConstDefinition, DefinitionError, FunctionDefinition, FutureIdentifierDefinition,
    IdentifierDefinition, LabelDefinition, MemberDefinition, ReferenceDefinition)
from starkware.cairo.lang.compiler.identifier_manager import IdentifierError, IdentifierManager
from starkware.cairo.lang.compiler.identifier_utils import get_struct_definition
from starkware.cairo.lang.compiler.instruction import Register
from starkware.cairo.lang.compiler.instruction_builder import (
    InstructionBuilderError, get_instruction_size)
from starkware.cairo.lang.compiler.location_utils import add_parent_location
from starkware.cairo.lang.compiler.offset_reference import OffsetReferenceDefinition
from starkware.cairo.lang.compiler.preprocessor.compound_expressions import (
    CompoundExpressionContext, SimplicityLevel, process_compound_assert,
    process_compound_expressions)
from starkware.cairo.lang.compiler.preprocessor.flow import (
    FlowTracking, FlowTrackingDataActual, FlowTrackingDataUnreachable, InstructionFlows,
    ReferenceManager)
from starkware.cairo.lang.compiler.preprocessor.identifier_aware_visitor import (
    IdentifierAwareVisitor)
from starkware.cairo.lang.compiler.preprocessor.local_variables import (
    create_simple_ref_expr, preprocess_local_variables)
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.preprocessor.preprocessor_utils import assert_no_modifier
from starkware.cairo.lang.compiler.preprocessor.reg_tracking import (
    RegChange, RegChangeKnown, RegChangeUnconstrained, RegChangeUnknown, RegTrackingData)
from starkware.cairo.lang.compiler.references import FlowTrackingError, Reference, translate_ap
from starkware.cairo.lang.compiler.resolve_search_result import resolve_search_result
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.substitute_identifiers import substitute_identifiers
from starkware.cairo.lang.compiler.type_casts import check_cast
from starkware.cairo.lang.compiler.type_system_visitor import get_expr_addr, simplify_type_system
from starkware.python.utils import safe_zip


@dataclasses.dataclass
class PreprocessedInstruction:
    instruction: InstructionAst
    # List of fully qualified scope names accessible by the hint function of this instruction.
    accessible_scopes: List[ScopedName]
    hint: Optional[CodeElementHint]
    flow_tracking_data: FlowTrackingDataActual

    def format(self, with_locations: bool = False) -> str:
        location_str = (
            f'  # {self.instruction.location.topmost_location()}.'
            if with_locations and self.instruction.location is not None
            else '')
        return (self.hint.format(get_max_line_length()) + '\n' if self.hint is not None else '') + \
            self.instruction.format() + location_str


@dataclasses.dataclass
class PreprocessedProgram:
    prime: int
    reference_manager: ReferenceManager
    instructions: List[PreprocessedInstruction]
    identifiers: IdentifierManager
    # A map from an identifier fully qualified name to the location of its definition.
    # This provides additional information on the compiled program which can be used by IDEs.
    identifier_locations: Dict[ScopedName, Location]
    builtins: List[str]

    def format(self, with_locations: bool = False) -> str:
        """
        Returns the program as a string.
        This can be used to print the preprocessor intermediate output.
        """
        code = self._directives_code()
        code += ''.join(
            inst.format(with_locations=with_locations) + '\n' for inst in self.instructions)
        return code

    def _directives_code(self) -> str:
        code = ''
        if self.builtins:
            code += BuiltinsDirective(builtins=self.builtins).format() + '\n'
        if code:
            code += '\n'
        return code


@dataclasses.dataclass
class FunctionMetadata:
    """
    Collects information about a function durning preprocessing.
    """

    # Information about the ap tracking at the beginning of the function.
    initial_ap_data: RegTrackingData

    # Metadata collection complete.
    completed: bool = False
    # Total change in ap during function. RegChangeUnconstrained() means we have not completed the
    # metadata collection and we have not encountered any return flow from the function yet.
    total_ap_change: RegChange = RegChangeUnconstrained()


class ReferenceState(Enum):
    DEFAULT = 0
    # The reference can be used as an implicit argument.
    ALLOW_IMPLICIT = auto()


class Preprocessor(IdentifierAwareVisitor):
    """
    Reads the AST representing the input and recreates it after handling the following:
    * Labels.
    * Constant values.
    * Functions.

    Arguments:
    prime: The prime we are compiling for.
    identifiers: An optional initial IdentifierManager.
    supported_decorators: A set of decorators that may appear before a function decleration.
    functions_to_compile: A set of functions to compile. None means compile everything.
    """

    def __init__(
            self, prime: int, identifiers: Optional[IdentifierManager] = None,
            supported_decorators: Optional[Set[str]] = None,
            functions_to_compile: Optional[Set[ScopedName]] = None):
        super().__init__(identifiers=identifiers,)
        self.prime: int = prime
        self.instructions: List[PreprocessedInstruction] = []
        # Stores the program counter of the next instruction (where the first instruction is at 0).
        # This is equal to the size of the code (in field elements) so far.
        self.current_pc = 0

        self.simplifier = ExpressionSimplifier(prime)

        # A list of hints for the next instruction.
        self.next_instruction_hint: Optional[CodeElementHint] = None

        # List of builtins.
        self.builtins: Optional[List[str]] = None
        # True if directives are allowed at this point.
        self.directives_allowed = True

        self.flow_tracking = FlowTracking()
        self.function_metadata: Dict[ScopedName, FunctionMetadata] = {}

        # The number of allocated temporary identifiers.
        self.next_temp_id = 0

        self._compound_expression_context = PreprocessorCompoundExpressionContext(preprocessor=self)

        # A map from reference names to their implicit/forbidden state (see ReferenceState).
        self.reference_states: Dict[ScopedName, ReferenceState] = {}

        # A set of temporary identifiers that are not expected to be collected by the
        # identifier collector
        self.scoped_temp_ids: Set[ScopedName] = set()

        if supported_decorators is None:
            supported_decorators = set()
        self.supported_decorators = supported_decorators

        self.functions_to_compile = functions_to_compile
        # A set of all scoped prefixes that were not traversed and need to be pruned form the
        # identifier manager.
        self.removed_prefixes: Set[ScopedName] = set()

    def search_identifier(
            self, name: str, location: Optional[Location]) -> Optional[IdentifierDefinition]:
        """
        Searches for the given identifier in self.identifiers and returns the corresponding
        IdentifierDefinition.
        """
        try:
            result = self.identifiers.search(self.accessible_scopes, ScopedName.from_string(name))
            return resolve_search_result(result, identifiers=self.identifiers)
        except IdentifierError as exc:
            raise PreprocessorError(str(exc), location=location)

    def handle_missing_future_definition(self, name: ScopedName, location):
        if name not in self.scoped_temp_ids:
            super().handle_missing_future_definition(name=name, location=location)

    def update_identifiers(self, identifiers: IdentifierManager):
        """
        Adds yet-undefined identifiers as FutureIdentifierDefinitions.
        """
        for name, future_definition in identifiers.as_dict().items():
            self.add_future_definition(name, future_definition)

    def add_future_definition(
            self, name: ScopedName, future_definition: FutureIdentifierDefinition):
        """
        Adds a future definition of an identifier.
        """
        existing_definition = self.identifiers.get_by_full_name(name)
        assert existing_definition is None
        self.identifiers.add_identifier(name, future_definition)

    def visit_uncommented_code_block(self, code_elements: List[CodeElement]):
        # Process code.
        for elm in code_elements:
            self.visit(elm)

            # Directives must appear at the top.
            if not isinstance(elm, (CodeElementDirective, CodeElementEmptyLine)):
                self.directives_allowed = False
        # Make sure there are no hints at the end of the code block.
        self.check_no_hints(
            'Found a hint at the end of a code block. Hints must be followed by an instruction.')

    def visit_CodeBlock(self, code_block: CodeBlock):
        # Remove the CommentedCodeElement wrapper.
        self.visit_uncommented_code_block([x.code_elm for x in code_block.code_elements])

    def visit_CairoModule(self, module: CairoModule):
        identifier_value = self.identifiers.get_by_full_name(module.module_name)
        self.directives_allowed = True
        if identifier_value is not None:
            raise PreprocessorError(
                f"Scope '{module.module_name}' collides with a different identifier "
                f"of type '{identifier_value.TYPE}'.",
                location=None)
        self.flow_tracking.revoke()
        super().visit_CairoModule(module)

    def resolve_labels(self):
        """
        Performs a second pass on the instructions to resolve labels.
        """
        self.instructions, old_instructions = [], self.instructions
        self.current_pc, old_pc = 0, self.current_pc
        self.flow_tracking, old_flow_tracking = FlowTracking(), self.flow_tracking
        self.function_metadata, old_function_metadata = {}, self.function_metadata

        assert self.accessible_scopes == [], 'Unexpected preprocessor state.'

        for preprocessed_instruction in old_instructions:
            self.accessible_scopes = preprocessed_instruction.accessible_scopes
            new_instruction = self.visit(preprocessed_instruction.instruction)
            self.check_preprocessed_instruction(new_instruction)
            self.current_pc += self.get_instruction_size(new_instruction)
            self.instructions.append(PreprocessedInstruction(
                instruction=new_instruction,
                accessible_scopes=preprocessed_instruction.accessible_scopes,
                hint=preprocessed_instruction.hint,
                flow_tracking_data=preprocessed_instruction.flow_tracking_data))

        self.accessible_scopes = []
        assert old_pc == self.current_pc
        self.flow_tracking = old_flow_tracking
        self.function_metadata = old_function_metadata

    def get_program(self):
        # Prune identifiers.
        self.identifiers.prune(self.removed_prefixes)
        return PreprocessedProgram(
            prime=self.prime,
            reference_manager=self.flow_tracking.reference_manager,
            instructions=list(self.instructions),
            identifiers=self.identifiers,
            identifier_locations=self.identifier_locations,
            builtins=[] if self.builtins is None else self.builtins,
        )

    def create_struct_from_identifier_list(
            self, identifier_list: Optional[IdentifierList], struct_name: ScopedName,
            location: Optional[Location]):
        """
        Creates a struct based on the given 'identifier_list'.
        """
        offset = 0
        args = identifier_list.identifiers if identifier_list is not None else []

        for arg in args:
            assert_no_modifier(arg)
            cairo_type = self.resolve_type(arg.get_type())
            member_def = MemberDefinition(offset=offset, cairo_type=cairo_type)
            self.add_name_definition(
                name=struct_name + arg.identifier.name,
                identifier_definition=member_def,
                location=arg.location)
            offset += self.get_size(cairo_type)

        self.add_name_definition(
            struct_name + SIZE_CONSTANT,
            ConstDefinition(value=offset),
            location=location)

    def add_references_from_struct_members(
            self, identifier_list: Optional[IdentifierList], members: Dict[str, MemberDefinition],
            scope: ScopedName, start_offset: int):
        """
        Adds a reference to an expression of the form '[fp + *]' for each of the struct members,
        starting from '[fp + start_offset]'.
        identifier_list should contain an item for each member, which is used for the argument name
        and location.
        """
        args = identifier_list.identifiers if identifier_list is not None else []
        for arg, member_def in safe_zip(args, members.values()):
            # Add a reference for the argument.
            assert_no_modifier(arg)
            self.add_simple_reference(
                name=scope + arg.identifier.name, reg=Register.FP,
                cairo_type=member_def.cairo_type, offset=start_offset + member_def.offset,
                location=arg.location)

    def visit_CodeElementFunction(self, elm: CodeElementFunction):
        self.check_no_hints('Hints before functions are not allowed.')
        if elm.element_type == 'struct':
            return

        for decorator in elm.decorators:
            if decorator.name not in self.supported_decorators:
                raise PreprocessorError(
                    f"Unsupported decorator: '{decorator.name}'.",
                    location=decorator.location)

        self.flow_tracking.revoke()

        new_scope = self.current_scope + elm.name

        if self.current_scope in self.function_metadata:
            outer_function_location = self.identifier_locations.get(self.current_scope)
            notes = []
            if outer_function_location is not None:
                loc_str = outer_function_location.to_string_with_content('')
                notes.append(f'Outer function was defined here: {loc_str}')

            raise PreprocessorError(
                'Nested functions are not supported.' if elm.element_type == 'func'
                else 'Cannot define a namespace inside a function.',
                location=elm.identifier.location,
                notes=notes,
            )

        if elm.element_type == 'func':
            # Check if this function should be skipped.
            if self.functions_to_compile is not None and new_scope not in self.functions_to_compile:
                self.removed_prefixes.add(new_scope)
                return

            self.add_function(elm)
        else:
            assert elm.element_type == 'namespace', f"""\
Expected 'elm.element_type' to be a 'namespace'. Found: '{elm.element_type}'."""
            self.add_label(identifier=elm.identifier)

        # Add function arguments and return values and process body.
        args_scope = new_scope + CodeElementFunction.ARGUMENT_SCOPE
        implicit_args_scope = new_scope + CodeElementFunction.IMPLICIT_ARGUMENT_SCOPE

        # Create the references for the arguments.
        args_struct = get_struct_definition(args_scope, self.identifiers)
        self.add_references_from_struct_members(
            identifier_list=elm.arguments, members=args_struct.members, scope=new_scope,
            start_offset=-(2 + args_struct.size))
        implicit_args_struct = get_struct_definition(implicit_args_scope, self.identifiers)
        self.add_references_from_struct_members(
            identifier_list=elm.implicit_arguments, members=implicit_args_struct.members,
            scope=new_scope, start_offset=-(2 + args_struct.size + implicit_args_struct.size))

        new_reference_states = dict(self.reference_states)
        if elm.implicit_arguments is not None:
            for typed_identifier in elm.implicit_arguments.identifiers:
                new_reference_states[new_scope + typed_identifier.name] = \
                    ReferenceState.ALLOW_IMPLICIT

        # Process code_elements.
        with self.scoped(new_scope, parent=elm), self.set_reference_states(new_reference_states):
            # Process local variable declaration.
            code_elements = preprocess_local_variables(
                code_elements=[x.code_elm for x in elm.code_block.code_elements],
                scope=new_scope,
                new_unique_id_callback=self.new_unique_id,
                get_size_callback=self.get_size,
                get_unpacking_struct_definition_callback=self.get_unpacking_struct_definition,
                default_location=elm.identifier.location,
            )

            self.visit_uncommented_code_block(code_elements)

        if elm.element_type == 'func':
            if self.flow_tracking.data != FlowTrackingDataUnreachable():
                raise PreprocessorError(
                    'Function must end with a return instruction or a jump.',
                    location=elm.identifier.location)

            self.function_metadata[new_scope].completed = True
            if self.function_metadata[new_scope].total_ap_change == RegChangeUnconstrained():
                # No returns occured.
                self.function_metadata[new_scope].total_ap_change = RegChangeUnknown()

    def visit_CodeElementWith(self, elm: CodeElementWith):
        new_reference_states = dict(self.reference_states)
        for aliased_identifier in elm.identifiers:
            src_identifier = aliased_identifier.orig_identifier
            src_full_name = self.current_scope + src_identifier.name
            if aliased_identifier.local_name is not None:
                raise PreprocessorError(
                    "The 'as' keyword is not supported in 'with' statements.",
                    location=aliased_identifier.local_name.location)

            src_identifier_definition = self.identifiers.get_by_full_name(src_full_name)
            if src_identifier_definition is None:
                raise PreprocessorError(
                    f"Unknown reference '{src_identifier.name}'.", location=src_identifier.location)

            if not isinstance(src_identifier_definition, ReferenceDefinition):
                raise PreprocessorError(
                    f"Expected '{src_identifier.name}' to be a reference, "
                    f'found: {src_identifier_definition.TYPE}.',
                    location=src_identifier.location)

            new_reference_states[src_full_name] = ReferenceState.ALLOW_IMPLICIT

        with self.set_reference_states(new_reference_states):
            for commented_code_element in elm.code_block.code_elements:
                self.visit(commented_code_element.code_elm)

    @contextmanager
    def set_reference_states(self, new_reference_states: Dict[ScopedName, ReferenceState]):
        """
        Context manager for overriding the value of self.reference_states (references that can be
        used as implicit arguments or cannot be set).
        """

        self.reference_states, old_reference_states = new_reference_states, self.reference_states

        try:
            yield
        finally:
            # Restore the old list.
            self.reference_states = old_reference_states

    def visit_CodeElementIf(self, elm: CodeElementIf):
        # Prepare branch compound expression.
        cond_expr = self.simplify_expr_as_felt(ExprOperator(
            a=elm.condition.a, op='-', b=elm.condition.b, location=elm.condition.location))
        compound_expressions_code_elements, (res_cond_expr,), _ = process_compound_expressions(
            [cond_expr], [SimplicityLevel.DEREF],
            context=self._compound_expression_context)
        for code_element in compound_expressions_code_elements:
            self.visit(code_element)

        # Prepare labels.
        assert elm.label_neq is not None
        assert elm.label_end is not None
        label_neq = ExprIdentifier(name=elm.label_neq, location=elm.location)
        label_end = ExprIdentifier(name=elm.label_end, location=elm.location)

        # Add conditional jump.
        self.visit(CodeElementInstruction(InstructionAst(
            body=JumpToLabelInstruction(
                label=label_neq, condition=res_cond_expr, location=elm.location),
            inc_ap=False, location=elm.location)))

        # Determine code blocks.
        eq_code_block: Optional[CodeBlock]
        neq_code_block: Optional[CodeBlock]
        if elm.condition.eq:
            eq_code_block, neq_code_block = elm.main_code_block, elm.else_code_block
        else:
            eq_code_block, neq_code_block = elm.else_code_block, elm.main_code_block

        # Equal code block.
        if eq_code_block is not None:
            for commented_code_element in eq_code_block.code_elements:
                self.visit(commented_code_element.code_elm)

        if self.flow_tracking.data != FlowTrackingDataUnreachable() and neq_code_block is not None:
            # Code block ended with a flow to next line. Since we have a "Not equal" block, we
            # add a jump to skip it.
            self.visit(CodeElementInstruction(InstructionAst(
                body=JumpToLabelInstruction(label=label_end, condition=None, location=elm.location),
                inc_ap=False, location=elm.location)))

        # Add the neq label.
        self.visit(CodeElementLabel(identifier=label_neq))

        # Not equal code block.
        if neq_code_block is not None:
            for commented_code_element in neq_code_block.code_elements:
                self.visit(commented_code_element.code_elm)

        # Add the end label.
        self.visit(CodeElementLabel(identifier=label_end))

    def visit_CodeElementDirective(self, elm: CodeElementDirective):
        # Visit directive.
        if not self.directives_allowed:
            raise PreprocessorError(
                'Directives must appear at the top of the file.',
                location=elm.location)
        self.visit(elm.directive)

    def visit_CodeElementImport(self, elm: CodeElementImport):
        pass

    def visit_CodeElementAllocLocals(self, elm: CodeElementAllocLocals):
        if self.current_scope not in self.function_metadata:
            raise PreprocessorError(
                'alloc_locals cannot be used outside of a function.',
                location=elm.location)
        # Check that ap did not change from the beginning of the function.
        if not isinstance(self.flow_tracking.data, FlowTrackingDataActual) or (
                self.flow_tracking.data.ap_tracking !=
                self.function_metadata[self.current_scope].initial_ap_data):
            raise PreprocessorError(
                'alloc_locals must be used before any instruction that changes the ap register.',
                location=elm.location)

    def visit_CodeElementInstruction(self, elm: CodeElementInstruction):
        current_flow_tracking_data = self.flow_tracking.get()
        preprocessed_instruction = PreprocessedInstruction(
            instruction=self.visit(elm.instruction),
            accessible_scopes=self.accessible_scopes.copy(),
            hint=self.next_instruction_hint,
            flow_tracking_data=current_flow_tracking_data)
        self.next_instruction_hint = None
        self.current_pc += self.get_instruction_size(
            preprocessed_instruction.instruction, allow_auto_deduction=True)
        self.instructions.append(preprocessed_instruction)

    def visit_CodeElementConst(self, elm: CodeElementConst):
        self.check_no_hints('Hints before constant definitions are not allowed.')

        if self.inside_a_struct():
            # Was already handled by the struct collector.
            return

        name = self.current_scope + elm.identifier.name
        val = self.simplify_expr_as_felt(elm.expr)
        if not isinstance(val, ExprConst):
            raise PreprocessorError('Expected a constant expression.', location=elm.expr.location)
        self.add_name_definition(
            name,
            ConstDefinition(value=val.val),
            location=elm.identifier.location)

    def visit_CodeElementMember(self, elm: CodeElementMember):
        self.check_no_hints('Hints before member definitions are not allowed.')

        if self.inside_a_struct():
            # Was already handled by the struct collector.
            return

        raise PreprocessorError(
            'The member keyword may only be used inside a struct.',
            location=elm.typed_identifier.location)

    def visit_CodeElementReference(self, elm: CodeElementReference):
        name = self.current_scope + elm.typed_identifier.identifier.name
        val, val_type = self.simplify_expr(elm.expr)

        assert_no_modifier(elm.typed_identifier)

        if elm.typed_identifier.expr_type is not None:
            dst_type = self.resolve_type(elm.typed_identifier.expr_type)
        else:
            # Copy the type from the value.
            dst_type = val_type
        if not check_cast(
                src_type=val_type,
                dest_type=dst_type,
                identifier_manager=self.identifiers,
                cast_type=CastType.ASSIGN):
            raise PreprocessorError(
                f"Cannot assign an expression of type '{val_type.format()}' "
                f"to a reference of type '{dst_type.format()}'.",
                location=dst_type.location)

        location = val.location

        # At this point 'val' is a simplified typeless expression and we need 'ref_expr'
        # to include a cast to the correct type.
        # We insert the cast at the correct location according to the outermost expression in 'val'.
        if isinstance(val, ExprDeref):
            # Add the cast inside the ExprDeref. For example, "[cast(ap, T*)]".
            addr = get_expr_addr(val)
            ref_expr: Expression = ExprDeref(
                addr=ExprCast(
                    expr=addr,
                    dest_type=TypePointer(pointee=dst_type, location=location),
                    location=addr.location),
                location=location)
        else:
            ref_expr = ExprCast(expr=val, dest_type=dst_type, location=location)

        self.add_reference(
            name=name,
            value=ref_expr,
            cairo_type=dst_type,
            location=elm.typed_identifier.location,
        )

    def visit_CodeElementLocalVariable(self, elm: CodeElementLocalVariable):
        raise PreprocessorError(
            'Local variables are not supported outside of functions.', location=elm.location)

    def visit_CodeElementTemporaryVariable(self, elm: CodeElementTemporaryVariable):
        assert_no_modifier(elm.typed_identifier)

        expr, src_type = self.simplify_expr(elm.expr)
        src_size = self.get_size(src_type)

        if elm.typed_identifier.expr_type is None:
            dest_type = src_type
        else:
            dest_type = self.resolve_type(elm.typed_identifier.expr_type)
            if not check_cast(
                    src_type=src_type, dest_type=dest_type, identifier_manager=self.identifiers,
                    cast_type=CastType.ASSIGN):
                raise PreprocessorError(
                    f"Cannot assign an expression of type '{src_type.format()}' "
                    f"to a temporary variable of type '{dest_type.format()}'.",
                    location=dest_type.location)

            dest_size = self.get_size(dest_type)
            assert src_size == dest_size, 'Expecting src and dest types to have the same size.'

        src_exprs = self.simplified_expr_to_felt_expr_list(expr=expr, expr_type=src_type)
        self.push_compound_expressions(compound_expressions=src_exprs, location=elm.location)
        self.add_simple_reference(
            name=self.current_scope + elm.typed_identifier.name,
            reg=Register.AP,
            cairo_type=dest_type,
            offset=-src_size,
            location=elm.typed_identifier.identifier.location)

    def visit_CodeElementCompoundAssertEq(self, instruction: CodeElementCompoundAssertEq):
        expr_a, expr_type_a = self.simplify_expr(instruction.a)
        expr_b, expr_type_b = self.simplify_expr(instruction.b)
        if expr_type_a != expr_type_b:
            raise PreprocessorError(
                f"Cannot compare '{expr_type_a.format()}' and '{expr_type_b.format()}'.",
                location=instruction.location)

        src_exprs = self.simplified_expr_to_felt_expr_list(expr=expr_a, expr_type=expr_type_a)
        dst_exprs = self.simplified_expr_to_felt_expr_list(expr=expr_b, expr_type=expr_type_b)
        original_ap_tracking = self.flow_tracking.get_ap_tracking()

        for src, dst in safe_zip(src_exprs, dst_exprs):
            ap_diff = self.flow_tracking.get_ap_tracking() - original_ap_tracking
            src = self.simplifier.visit(translate_ap(src, ap_diff))
            dst = self.simplifier.visit(translate_ap(dst, ap_diff))
            compound_expressions_code_elements, (expr_a, expr_b) = process_compound_assert(
                src,
                dst,
                self._compound_expression_context)
            assert_eq = CodeElementInstruction(
                instruction=InstructionAst(
                    body=AssertEqInstruction(
                        a=expr_a,
                        b=expr_b,
                        location=instruction.location),
                    inc_ap=False,
                    location=instruction.location))

            for code_element in compound_expressions_code_elements:
                self.visit(code_element)
            self.visit(assert_eq)

    def visit_CodeElementStaticAssert(self, elm: CodeElementStaticAssert):
        a = self.simplify_expr_as_felt(elm.a)
        b = self.simplify_expr_as_felt(elm.b)
        if a != b:
            raise PreprocessorError(
                f'Static assert failed: {a.format()} != {b.format()}.', location=elm.location)

    def optimize_expressions_for_push(self, exprs: List[Expression]) -> List[Expression]:
        """
        Optimizes a list of expressions intended to be pushed onto the stack. Returns an equivalent
        list of expressions.

        Example:
        If we need to push [ap - 2], [ap - 1], [fp] + 3, there is no need to push the first 2
        expressions, since they are already at the top of the stack.
        """

        if len(exprs) == 0:
            return exprs

        exprs = [self.simplify_expr_as_felt(expr) for expr in exprs]

        # If a prefix of the expressions are simple and pushed onto the stack, don't push them
        # again.
        # Only continue if the first expression is of the form [ap - n] for 0 < n <= len(exprs).
        def get_ap_minus_n(expr: Expression) -> Optional[int]:
            """
            If the expression is [ap + (-n)], returns n. Otherwise, returns None.
            """
            if not isinstance(expr, ExprDeref):
                return None
            if not isinstance(expr.addr, ExprOperator) or expr.addr.op != '+':
                return None
            if not isinstance(expr.addr.a, ExprReg) or expr.addr.a.reg != Register.AP:
                return None
            if not isinstance(expr.addr.b, ExprConst):
                return None
            return -expr.addr.b.val

        # Get the candidate prefix size from the first value being pushed.
        prefix_size = get_ap_minus_n(exprs[0])
        if prefix_size is None or prefix_size <= 0 or prefix_size > len(exprs):
            return exprs

        # Make sure the first n expressions are all [ap - prefix_size].
        for i in range(1, prefix_size):
            if get_ap_minus_n(exprs[i]) != prefix_size - i:
                return exprs

        # We know that the first n expressions are all [ap - prefix_size].
        # We can safely remove them.
        return exprs[prefix_size:]

    def process_expr_assignment_list(
            self, exprs: List[ExprAssignment], struct_name: ScopedName,
            location: Optional[Location]) -> List[Expression]:
        """
        Returns the expressions for an argument list.
        Used both for function call and a return instruction.
        Verifies the correctness of expr assignment with respect to the expected struct.

        exprs - list of ExprAssignment objects to process.
        struct_name - ScopedName of the struct against which the expr list is verified.
        location - location to attach to errors if no finer location is relevant.
        """

        struct_def = self.get_struct_definition(name=struct_name, location=location)
        n_members = len(struct_def.members)
        # Make sure we have the correct number of expressions.
        if len(exprs) != n_members:
            raise PreprocessorError(
                f'Expected exactly {n_members} expressions, got {len(exprs)}.',
                location=location)

        passed_args = list(struct_def.members.items())
        reached_named = False
        compound_expressions = []
        for (member_name, member_def), expr_assignment in zip(passed_args, exprs):
            if expr_assignment.identifier is None:
                # Make sure all named args are after positional args.
                if reached_named:
                    raise PreprocessorError(
                        'Positional arguments must not appear after named arguments.',
                        location=expr_assignment.location)
            else:
                reached_named = True
                name = expr_assignment.identifier.name
                if name != member_name:
                    raise PreprocessorError(
                        f"Expected named arg '{member_name}' found '{name}'.",
                        location=expr_assignment.identifier.location)

            felt_expr_list = self.simplify_expr_to_felt_expr_list(
                expr_assignment.expr, member_def.cairo_type)
            compound_expressions.extend(felt_expr_list)

        return compound_expressions

    def process_implicit_argument_binding(
            self, implicit_args: List[ExprAssignment],
            implicit_args_struct_name: ScopedName,
            location: Optional[Location]) -> List[Optional[ExprIdentifier]]:
        """
        Processes the implicit argument bindings. Returns a list whose size is the number of
        implicit arguments of the called function, with the binding variable for each argument
        if exists, and None otherwise.
        For example, given "func foo{x, y, z}", and the call "foo{y=w}()" the returned list
        will be [None, w, None].
        """
        implicit_args_struct = self.get_struct_definition(
            name=implicit_args_struct_name, location=location)

        # A list of (arg_name, binding).
        processed_implicit_args: List[Tuple[ExprIdentifier, ExprIdentifier]] = []
        for arg in implicit_args:
            if arg.identifier is None:
                raise PreprocessorError(
                    'Implicit argument binding must be of the form: arg_name=var.',
                    location=arg.location)

            if not isinstance(arg.expr, ExprIdentifier) or '.' in arg.expr.name:
                raise PreprocessorError(
                    'Implicit argument binding must be an identifier.',
                    location=arg.expr.location)
            processed_implicit_args.append((arg.identifier, arg.expr))

        result: List[Optional[ExprIdentifier]] = []

        for member_name in implicit_args_struct.members.keys():
            if len(processed_implicit_args) == 0 or \
                    processed_implicit_args[0][0].name != member_name:
                result.append(None)
                continue

            result.append(processed_implicit_args[0][1])
            processed_implicit_args.pop(0)

        # Make sure all implicit argument bindings were processed.
        if len(processed_implicit_args) > 0:
            raise PreprocessorError(
                f'Unexpected implicit argument binding: {processed_implicit_args[0][0].name}.',
                location=processed_implicit_args[0][0].location)

        return result

    def process_implicit_arguments(
            self, implicit_args: Optional[List[Optional[ExprIdentifier]]],
            implicit_args_struct_name: ScopedName,
            location: Optional[Location]) -> List[Expression]:
        """
        Returns the expressions for the implicit arguments.
        Used both for function call and a return instruction.

        implicit_args - list of implicit argument bindings.
        implicit_args_struct_name - ScopedName of the implicit argument struct.
        location - location to attach to errors if no finer location is relevant.
        """
        implicit_args_struct = self.get_struct_definition(
            name=implicit_args_struct_name, location=location)

        if implicit_args is None:
            implicit_args = [None] * len(implicit_args_struct.members)

        compound_expressions = []
        for (member_name, member_def), implicit_arg in safe_zip(
                implicit_args_struct.members.items(), implicit_args):
            expr: Expression
            if implicit_arg is not None:
                # Explicit binding is given, use it.
                expr = implicit_arg
            else:
                # No explicit binding is given, use the name of the implicit argument.
                expr = add_parent_location(
                    expr=ExprIdentifier(name=member_name, location=member_def.location),
                    new_parent_location=location,
                    message=f"While trying to retrieve the implicit argument '{member_name}' in:")

            felt_expr_list = self.simplify_expr_to_felt_expr_list(expr, member_def.cairo_type)
            compound_expressions.extend(felt_expr_list)

        return compound_expressions

    def push_compound_expressions(
            self, compound_expressions: List[Expression], location: Optional[Location]):
        """
        Generates instructions to push all the given expressions onto the stack.
        In more detail: translates a list of expressions to a set of instructions evaluating the
        expressions and storing the values to memory, starting from address 'ap'.

        compound_expressions - list of Expression objects to process.
        location - location to attach to errors if no finer location is relevant.
        """
        # Generate instructions.
        compound_expressions_code_elements, simple_exprs, first_compound_expr = \
            process_compound_expressions(
                compound_expressions,
                SimplicityLevel.OPERATION,
                context=self._compound_expression_context)

        for code_element in compound_expressions_code_elements:
            self.visit(code_element)

        assert len(simple_exprs) == len(compound_expressions)
        simple_exprs = self.optimize_expressions_for_push(simple_exprs)
        compound_expressions = compound_expressions[-len(simple_exprs):]

        for i, (simple_expr, original_expr) in enumerate(
                zip(simple_exprs, compound_expressions)):
            location = original_expr.location
            code_elm_inst = CodeElementInstruction(
                instruction=InstructionAst(
                    body=AssertEqInstruction(
                        a=ExprDeref(
                            addr=ExprReg(reg=Register.AP, location=location),
                            location=location,
                        ),
                        b=translate_ap(simple_expr, RegChangeKnown(i)),
                        location=location,
                    ),
                    inc_ap=True,
                    location=location,
                ))
            self.visit(code_elm_inst)

    def push_arguments(
            self, arguments: List[ExprAssignment],
            implicit_args: Optional[List[Optional[ExprIdentifier]]],
            struct_name: ScopedName, implicit_args_struct_name: ScopedName,
            location: Optional[Location]):
        """
        Generates instructions to push all arguments (including the implicit arguments) onto the
        stack.
        Used both for function call and a return instruction.
        Verifies the correctness of expr assignment with respect to the expected struct.
        In more detail: translates a list of expressions to a set of instructions evaluating the
        expressions and storing the values to memory, starting from address 'ap'.

        arguments - list of ExprAssignment objects to process.
        implicit_args - list of implicit argument bindings.
        struct_name - ScopedName of the struct against which the expr list is verified.
        implicit_args_struct_name - Similar to struct_name, for the implicit arguments.
        location - location to attach to errors if no finer location is relevant.
        """
        args_expressions = self.process_expr_assignment_list(
            exprs=arguments, struct_name=struct_name, location=location)

        implicit_args_expressions = self.process_implicit_arguments(
            implicit_args=implicit_args,
            implicit_args_struct_name=implicit_args_struct_name, location=location)

        self.push_compound_expressions(
            compound_expressions=implicit_args_expressions + args_expressions,
            location=location,
        )

    def visit_CodeElementReturn(self, elm: CodeElementReturn):
        if self.current_scope not in self.function_metadata:
            raise PreprocessorError(
                f'return cannot be used outside of a function.', location=elm.location)

        self.push_arguments(
            arguments=cast(List[ExprAssignment], elm.exprs),
            implicit_args=None,
            struct_name=CodeElementFunction.RETURN_SCOPE,
            implicit_args_struct_name=CodeElementFunction.IMPLICIT_ARGUMENT_SCOPE,
            location=elm.location,
        )
        code_elm_ret = CodeElementInstruction(
            instruction=InstructionAst(
                body=RetInstruction(),
                inc_ap=False,
                location=elm.location))
        self.visit(code_elm_ret)

    def check_tail_call_cast(self, src_type: CairoType, dest_type: CairoType) -> bool:
        """
        Checks if src_type can be converted to dest_type in the context of a tail call.
        """
        if check_cast(
                src_type=src_type, dest_type=dest_type, identifier_manager=self.identifiers,
                cast_type=CastType.ASSIGN):
            return True

        if not isinstance(src_type, TypeStruct) or not isinstance(dest_type, TypeStruct):
            return False

        src_members = get_struct_definition(
            src_type.scope, identifier_manager=self.identifiers).members
        dest_members = get_struct_definition(
            dest_type.scope, identifier_manager=self.identifiers).members

        if len(src_members) != len(dest_members):
            return False

        for src_member, dest_member in zip(src_members.values(), dest_members.values()):
            if not check_cast(
                    src_type=src_member.cairo_type,
                    dest_type=dest_member.cairo_type,
                    identifier_manager=self.identifiers,
                    cast_type=CastType.ASSIGN):
                return False

        return True

    def visit_CodeElementTailCall(self, elm: CodeElementTailCall):
        if self.current_scope not in self.function_metadata:
            raise PreprocessorError(
                f'return cannot be used outside of a function.', location=elm.location)

        # Visit function call before type check to get better error message.
        self.visit(CodeElementFuncCall(func_call=elm.func_call))

        func_name = elm.func_call.func_ident.name

        src_type = self.resolve_type(TypeStruct(
            scope=ScopedName.from_string(func_name) + CodeElementFunction.RETURN_SCOPE,
            is_fully_resolved=False, location=elm.location))

        dest_type = self.resolve_type(TypeStruct(
            scope=self.current_scope + CodeElementFunction.RETURN_SCOPE,
            is_fully_resolved=True, location=elm.location))

        if not self.check_tail_call_cast(src_type=src_type, dest_type=dest_type):
            raise PreprocessorError(
                f"""\
Cannot convert the return type of {func_name} to the return type of {self.current_scope[-1:]}.""",
                location=elm.func_call.location)

        src_type = self.resolve_type(TypeStruct(
            scope=ScopedName.from_string(func_name) + CodeElementFunction.IMPLICIT_ARGUMENT_SCOPE,
            is_fully_resolved=False, location=elm.location))

        dest_type = self.resolve_type(TypeStruct(
            scope=self.current_scope + CodeElementFunction.IMPLICIT_ARGUMENT_SCOPE,
            is_fully_resolved=True, location=elm.location))

        if not self.check_tail_call_cast(src_type=src_type, dest_type=dest_type):
            raise PreprocessorError(
                f"""\
Cannot convert the implicit arguments of {func_name} to the implicit arguments of \
{self.current_scope[-1:]}.""",
                location=elm.func_call.location)

        self.visit(CodeElementInstruction(
            instruction=InstructionAst(
                body=RetInstruction(),
                inc_ap=False,
                location=elm.location)))

    def add_implicit_return_references(
            self, implicit_args: List[Optional[ExprIdentifier]],
            called_function: ScopedName,
            location: Optional[Location]):
        """
        Adds references that allow accessing the implicit return values of a called function.
        """
        implicit_args_struct = self.get_struct_definition(
            name=called_function + CodeElementFunction.IMPLICIT_ARGUMENT_SCOPE,
            location=location)
        return_size = self.get_struct_size(
            struct_name=called_function + CodeElementFunction.RETURN_SCOPE,
            location=location)

        assert len(implicit_args_struct.members) == len(implicit_args)
        for (name, member_def), implicit_arg in zip(
                implicit_args_struct.members.items(), implicit_args):
            if implicit_arg is not None:
                # Use the implicit argument binding.
                binding_var = implicit_arg.name
                implicit_arg_location = implicit_arg.location
            else:
                binding_var = name
                implicit_arg_location = member_def.location
                if location is not None and implicit_arg_location is not None:
                    implicit_arg_location = implicit_arg_location.with_parent_location(
                        new_parent_location=location,
                        message=f"While trying to update the implicit return value '{name}' in:")

            self.add_simple_reference(
                name=self.current_scope + binding_var,
                reg=Register.AP,
                cairo_type=member_def.cairo_type,
                offset=member_def.offset - (return_size + implicit_args_struct.size),
                location=implicit_arg_location)

            if implicit_arg is None and self.reference_states.get(
                    self.current_scope + name) is not ReferenceState.ALLOW_IMPLICIT:
                raise PreprocessorError(
                    f"'{name}' cannot be used as an implicit return value. "
                    "Consider using a 'with' statement.",
                    location=implicit_arg_location)

    def visit_CodeElementFuncCall(self, elm: CodeElementFuncCall):
        # Make sure the identifier for the called function refers to a function.
        called_function = ScopedName.from_string(elm.func_call.func_ident.name)
        try:
            res = self.identifiers.search(
                accessible_scopes=self.accessible_scopes, name=called_function)
            res.assert_fully_parsed()
        except IdentifierError as exc:
            raise PreprocessorError(str(exc), location=elm.func_call.func_ident.location)
        called_function_def = res.identifier_definition
        called_function_def_type = called_function_def.identifier_type \
            if isinstance(called_function_def, FutureIdentifierDefinition) \
            else type(called_function_def)
        if called_function_def_type is not FunctionDefinition:
            raise PreprocessorError(
                f'Expected {called_function} to be a function name. '
                f'Found: {called_function_def.TYPE}.',
                location=elm.func_call.func_ident.location)

        implicit_args_struct_name = called_function + CodeElementFunction.IMPLICIT_ARGUMENT_SCOPE
        implicit_args = (
            cast(List[ExprAssignment], elm.func_call.implicit_arguments.args)
            if elm.func_call.implicit_arguments is not None
            else [])
        processed_implicit_args = self.process_implicit_argument_binding(
            implicit_args=implicit_args,
            implicit_args_struct_name=implicit_args_struct_name,
            location=elm.func_call.location)

        self.push_arguments(
            arguments=cast(List[ExprAssignment], elm.func_call.arguments.args),
            implicit_args=processed_implicit_args,
            struct_name=called_function + CodeElementFunction.ARGUMENT_SCOPE,
            implicit_args_struct_name=called_function + CodeElementFunction.IMPLICIT_ARGUMENT_SCOPE,
            location=elm.func_call.location,
        )
        code_elm_call = CodeElementInstruction(
            instruction=InstructionAst(
                body=CallLabelInstruction(
                    label=elm.func_call.func_ident,
                    location=elm.func_call.location,
                ),
                inc_ap=False,
                location=elm.func_call.location))
        self.visit(code_elm_call)

        self.add_implicit_return_references(
            implicit_args=processed_implicit_args,
            called_function=called_function,
            location=elm.func_call.location,
        )

    def add_simple_reference(
            self, name: ScopedName, reg: Register, cairo_type: CairoType, offset: int,
            location: Optional[Location]):
        """
        Creates a simple reference with the given name to "[reg + offset]".
        """

        ref_expr = create_simple_ref_expr(
            reg=reg,
            offset=offset,
            cairo_type=cairo_type,
            location=location)
        self.add_reference(
            name=name,
            value=ref_expr,
            cairo_type=cairo_type,
            location=location,
        )

    def visit_CodeElementReturnValueReference(self, elm: CodeElementReturnValueReference):
        assert_no_modifier(elm.typed_identifier)
        if isinstance(elm.func_call, RvalueCallInst):
            call_elm: CodeElement = CodeElementInstruction(
                instruction=InstructionAst(
                    body=elm.func_call.call_inst,
                    inc_ap=False,
                    location=elm.func_call.call_inst.location,
                ))
            func_ident = None
            if isinstance(elm.func_call.call_inst, CallLabelInstruction):
                func_ident = elm.func_call.call_inst.label
        elif isinstance(elm.func_call, RvalueFuncCall):
            # If the function name is the name of a struct, replace the
            # CodeElementReturnValueReference with a regular reference.
            if self.try_get_struct_definition(
                    ScopedName.from_string(elm.func_call.func_ident.name)) is not None:
                return self.visit(CodeElementReference(
                    typed_identifier=elm.typed_identifier,
                    expr=ExprFuncCall(
                        rvalue=elm.func_call,
                        location=elm.func_call.location)))
            call_elm = CodeElementFuncCall(func_call=elm.func_call)
            func_ident = elm.func_call.func_ident
        else:
            raise NotImplementedError(f'Unsupported func_call={elm.func_call}.')

        expr_type = elm.typed_identifier.expr_type
        if expr_type is None:
            if func_ident is not None:
                expr_type = TypeStruct(
                    scope=ScopedName.from_string(func_ident.name) +
                    CodeElementFunction.RETURN_SCOPE,
                    is_fully_resolved=False,
                    location=func_ident.location,
                )
            else:
                expr_type = TypeFelt(location=elm.typed_identifier.location)

        # Visit call_elm to advance pc.
        self.visit(call_elm)

        cairo_type = self.resolve_type(expr_type)
        struct_size = self.get_size(cairo_type)
        self.add_simple_reference(
            name=self.current_scope + elm.typed_identifier.identifier.name,
            reg=Register.AP,
            cairo_type=cairo_type,
            offset=-struct_size,
            location=elm.typed_identifier.location,
        )

    def get_unpacking_struct_definition(self, elm: CodeElementUnpackBinding):
        if not isinstance(elm.rvalue, RvalueFuncCall):
            raise PreprocessorError(
                f'Cannot unpack {elm.rvalue.format()}.',
                location=elm.rvalue.location)

        func_ident = elm.rvalue.func_ident
        return_type = self.resolve_type(TypeStruct(
            scope=ScopedName.from_string(func_ident.name) + CodeElementFunction.RETURN_SCOPE,
            is_fully_resolved=False,
            location=func_ident.location,
        ))
        assert isinstance(return_type, TypeStruct), f'Unexpected type {return_type}.'
        struct_def = get_struct_definition(return_type.scope, identifier_manager=self.identifiers)

        expected_len = len(struct_def.members)
        unpacking_identifiers = elm.unpacking_list.identifiers
        if len(unpacking_identifiers) != expected_len:
            suffix = 's' if expected_len > 1 else ''
            raise PreprocessorError(
                f"""\
Expected {expected_len} unpacking identifier{suffix}, found {len(unpacking_identifiers)}.""",
                location=elm.unpacking_list.location)

        return struct_def

    def visit_CodeElementUnpackBinding(self, elm: CodeElementUnpackBinding):
        struct_def = self.get_unpacking_struct_definition(elm)

        assert isinstance(elm.rvalue, RvalueFuncCall), \
            f'Invalid type for elm.rvalue: {type(elm.rvalue).__name__}.'
        self.visit(CodeElementFuncCall(func_call=elm.rvalue))

        for typed_identifier, member_def in zip(
                elm.unpacking_list.identifiers, struct_def.members.values()):
            assert_no_modifier(typed_identifier)

            if typed_identifier.name == '_':
                continue

            if typed_identifier.expr_type is not None:
                cairo_type = self.resolve_type(typed_identifier.get_type())
            else:
                cairo_type = member_def.cairo_type

            if not check_cast(
                    src_type=member_def.cairo_type, dest_type=cairo_type,
                    identifier_manager=self.identifiers,
                    cast_type=CastType.UNPACKING):
                raise PreprocessorError(
                    f"""\
Expected expression of type '{member_def.cairo_type.format()}', got '{cairo_type.format()}'.""",
                    location=typed_identifier.location
                )

            self.add_simple_reference(
                name=self.current_scope + typed_identifier.identifier.name, reg=Register.AP,
                cairo_type=cairo_type, offset=member_def.offset - struct_def.size,
                location=typed_identifier.location)

    def add_label(self, identifier: ExprIdentifier):
        name = self.current_scope + identifier.name
        self.flow_tracking.converge_with_label(name)
        self.add_name_definition(
            name,
            LabelDefinition(pc=self.current_pc),  # type: ignore
            location=identifier.location)

    def add_reference(
            self, name: ScopedName, value: Expression, cairo_type: CairoType,
            location: Optional[Location], require_future_definition=True):
        if name.path[-1] == '_':
            raise PreprocessorError("Reference name cannot be '_'.", location=location)

        reference = Reference(
            pc=self.current_pc,
            value=value,
            ap_tracking_data=self.flow_tracking.get_ap_tracking(),
            locations=[] if location is None else [location],
        )

        self.flow_tracking.add_reference(name, reference)
        existing_definition = self.identifiers.get_by_full_name(name)
        if isinstance(existing_definition, ReferenceDefinition):
            # Rebind reference.
            if existing_definition.cairo_type != cairo_type:
                raise PreprocessorError(
                    'Reference rebinding must preserve the reference type. '
                    f"Previous type: '{existing_definition.cairo_type.format()}', "
                    f"new type: '{cairo_type.format()}'.",
                    location=location)
            existing_definition.references.append(reference)
        else:
            self.add_name_definition(
                name,
                ReferenceDefinition(full_name=name, cairo_type=cairo_type, references=[reference]),
                location=location, require_future_definition=require_future_definition)

    def add_function(self, elm: CodeElementFunction):
        name = self.current_scope + elm.name
        self.add_name_definition(
            name,
            FunctionDefinition(  # type: ignore
                pc=self.current_pc,
                decorators=[identifier.name for identifier in elm.decorators],
            ),
            location=elm.identifier.location)

        self.function_metadata[name] = FunctionMetadata(
            initial_ap_data=self.flow_tracking.get_ap_tracking())

    def visit_CodeElementLabel(self, elm: CodeElementLabel):
        self.check_no_hints('Hints before labels are not allowed.')
        self.add_label(elm.identifier)

    def visit_CodeElementHint(self, elm: CodeElementHint):
        self.check_no_hints('Only one hint is allowed per instruction.')
        self.next_instruction_hint = elm

    def visit_CodeElementEmptyLine(self, elm: CodeElementEmptyLine):
        # Ignore empty lines.
        pass

    # Instructions.
    def visit_InstructionAst(self, instruction: InstructionAst):
        flows, instruction_body = self.visit(instruction.body)
        res = InstructionAst(
            body=instruction_body,
            inc_ap=instruction.inc_ap,
            location=instruction.location)
        added_ap = 1 if instruction.inc_ap else 0

        # Add jump flows.
        for label, change in flows.jumps.items():
            self.flow_tracking.add_flow_to_label(label, change + added_ap)

        # Add flow to next instruction if needed.
        if flows.next_inst is not None:
            # There is a flow to the next instruction. Add ap change.
            self.flow_tracking.add_ap(flows.next_inst + added_ap)
        else:
            # There is no flow to the next instruction. Revoke.
            self.flow_tracking.revoke()
        return res

    def visit_AssertEqInstruction(self, instruction: AssertEqInstruction):
        return InstructionFlows(next_inst=RegChangeKnown(0)), AssertEqInstruction(
            a=self.simplify_expr_as_felt(instruction.a),
            b=self.simplify_expr_as_felt(instruction.b),
            location=instruction.location)

    def visit_JumpInstruction(self, instruction: JumpInstruction):
        self.revoke_function_ap_change()
        return InstructionFlows(), JumpInstruction(
            val=self.simplify_expr_as_felt(instruction.val),
            relative=instruction.relative,
            location=instruction.location)

    def visit_JumpToLabelInstruction(self, instruction: JumpToLabelInstruction):
        label_name = instruction.label.name
        label_pc, label_full_name = self.get_label(label_name, instruction.label.location)

        # Process instruction.
        res_instruction: InstructionBody
        if label_pc is None:
            condition = instruction.condition
            if condition is not None:
                condition = self.simplify_expr_as_felt(condition)
            res_instruction = dataclasses.replace(instruction, condition=condition)
        else:
            jump_offset = ExprConst(
                val=label_pc - self.current_pc, location=instruction.label.location)
            if instruction.condition is None:
                self.current_instruction_ended_flow = True
                res_instruction = JumpInstruction(
                    val=jump_offset,
                    relative=True,
                    location=instruction.location)
            else:
                res_instruction = JnzInstruction(
                    jump_offset=jump_offset,
                    condition=self.simplify_expr_as_felt(instruction.condition),
                    location=instruction.location)

            if label_pc <= self.current_pc:
                self.revoke_function_ap_change()

        flow_next = None if instruction.condition is None else RegChangeKnown(0)
        if label_full_name is None:
            raise PreprocessorError(
                f'Unknown label {label_name}.',
                location=instruction.label.location)
        jumps: Dict[ScopedName, RegChange] = {label_full_name: RegChangeKnown(0)}
        return InstructionFlows(next_inst=flow_next, jumps=jumps), res_instruction

    def visit_JnzInstruction(self, instruction: JnzInstruction):
        self.revoke_function_ap_change()
        return InstructionFlows(next_inst=RegChangeKnown(0)), JnzInstruction(
            jump_offset=self.simplify_expr_as_felt(instruction.jump_offset),
            condition=self.simplify_expr_as_felt(instruction.condition),
            location=instruction.location)

    def revoke_function_ap_change(self):
        """
        Revokes the total_ap_change tracking of the function (which implies that calling it will
        revoke the ap tracking).
        """
        if self.current_scope in self.function_metadata:
            self.function_metadata[self.current_scope].total_ap_change = RegChangeUnknown()

    def visit_CallInstruction(self, instruction: CallInstruction):
        return InstructionFlows(next_inst=RegChangeUnknown()), CallInstruction(
            val=self.simplify_expr_as_felt(instruction.val),
            relative=instruction.relative,
            location=instruction.location)

    def visit_CallLabelInstruction(self, instruction: CallLabelInstruction):
        label_name = instruction.label.name
        label_pc, full_label_scope = self.get_label(label_name, instruction.label.location)

        # If the function has a known reg change, use it.
        ap_change = RegChangeUnknown()
        if label_pc is None:
            return InstructionFlows(next_inst=ap_change), instruction

        if full_label_scope in self.function_metadata:
            metadata = self.function_metadata[full_label_scope]
            if metadata.completed:
                assert isinstance(metadata.total_ap_change, (RegChangeKnown, RegChangeUnknown))
                # Add 2 for call instruction.
                ap_change = 2 + metadata.total_ap_change

        jump_offset = ExprConst(
            val=label_pc - self.current_pc, location=instruction.label.location)
        return InstructionFlows(next_inst=ap_change), \
            CallInstruction(val=jump_offset, relative=True, location=instruction.location)

    def visit_AddApInstruction(self, instruction: AddApInstruction):
        expr = self.simplify_expr_as_felt(instruction.expr)
        return InstructionFlows(next_inst=RegChange.from_expr(expr)), AddApInstruction(
            expr=expr,
            location=instruction.location)

    def visit_RetInstruction(self, instruction: RetInstruction):
        if self.current_scope in self.function_metadata:
            metadata = self.function_metadata[self.current_scope]
            ap_change = self.flow_tracking.get_ap_tracking() - metadata.initial_ap_data
            metadata.total_ap_change &= ap_change
        return InstructionFlows(), instruction

    # Directives.
    def visit_BuiltinsDirective(self, directive: BuiltinsDirective):
        if self.builtins is not None:
            raise PreprocessorError(
                'Redefinition of builtins directive.',
                location=directive.location,
            )

        seen_builtins = set()
        for builtin in directive.builtins:
            if builtin in seen_builtins:
                raise PreprocessorError(
                    f"The builtin '{builtin}' appears twice in builtins directive.",
                    location=directive.location,
                )

            seen_builtins.add(builtin)

        self.builtins = directive.builtins

    def visit_LangDirective(self, directive: LangDirective):
        raise PreprocessorError(
            f'Unsupported %lang directive. Are you using the correct compiler?',
            location=directive.location,
        )

    def simplify_expr(self, expr) -> Tuple[Expression, CairoType]:
        """
        Simplifies the expression by resolving identifiers, type-system related reductions
        and numeric simplifications.
        Returns the simplified expression and its type.
        """
        expr = substitute_identifiers(
            expr=expr,
            get_identifier_callback=self.get_variable,
            resolve_type_callback=self.resolve_type)
        expr, expr_type = simplify_type_system(expr, identifiers=self.identifiers)
        return self.simplifier.visit(expr), self.resolve_type(expr_type)

    def simplify_expr_as_felt(self, expr) -> Expression:
        """
        Same as simplify_expr(), except that it verifies that the type of the result is convertible
        to felt (felt or pointer) and it does not return the type.
        """
        expr, expr_type = self.simplify_expr(expr)
        if not isinstance(expr_type, (TypeFelt, TypePointer)):
            raise PreprocessorError(
                f"Expected a 'felt' or a pointer type. Got: '{expr_type.format()}'.",
                location=expr.location)
        return expr

    def simplify_expr_to_felt_expr_list(
            self, expr: Expression, expected_type: CairoType) -> List[Expression]:
        """
        Takes a possibly typed expression, checks that it can be assigned to expected_type
        and splits it into a list of typeless expressions that can be passed to
        process_compound_expressions.
        """

        # Keep the location of the original expression for error handling.
        location = expr.location
        expr, expr_type = self.simplify_expr(expr)

        if not check_cast(
                src_type=expr_type, dest_type=expected_type, identifier_manager=self.identifiers,
                cast_type=CastType.ASSIGN):
            raise PreprocessorError(
                f"""\
Expected expression of type '{expected_type.format()}', got '{expr_type.format()}'.""",
                location=location
            )

        return self.simplified_expr_to_felt_expr_list(expr=expr, expr_type=expr_type)

    def simplified_expr_to_felt_expr_list(
            self, expr: Expression, expr_type: CairoType) -> List[Expression]:
        """
        Takes a simplified expression and its type and splits it into a list of typeless expressions
        that can be passed to process_compound_expressions.
        """

        if isinstance(expr_type, (TypeFelt, TypePointer)):
            return [expr]

        # Get the list of member types.
        if isinstance(expr_type, TypeTuple):
            member_types = expr_type.members
        elif isinstance(expr_type, TypeStruct):
            struct_definition = get_struct_definition(
                expr_type.scope, identifier_manager=self.identifiers)
            member_types = [
                member_def.cairo_type for member_def in struct_definition.members.values()]
        else:
            raise PreprocessorError(f'Unexpected type {expr_type}.', location=expr_type.location)

        # Get the list of member expressions.
        if isinstance(expr, ExprTuple):
            member_exprs = [assign_expr.expr for assign_expr in expr.members.args]
        else:
            addr = get_expr_addr(expr)

            offset = 0
            member_exprs = []
            location = expr.location
            for member_type in member_types:
                # Call simplifier to convert (fp + offset_1) + offset_2 to
                # fp + (offset_1 + offset_2).
                member_exprs.append(
                    self.simplifier.visit(
                        ExprDeref(
                            ExprOperator(
                                a=addr,
                                op='+',
                                b=ExprConst(offset, location=location),
                                location=location,
                            ),
                            location=location,
                        )))

                offset += self.get_size(member_type)

        expr_list = []
        for member_expr, member_type in zip(member_exprs, member_types):
            expr_list.extend(self.simplified_expr_to_felt_expr_list(
                expr=member_expr, expr_type=member_type))
        return expr_list

    def get_label(self, label_name: str, location: Optional[Location]) -> \
            Tuple[Optional[int], Optional[ScopedName]]:
        """
        Returns a pair (pc, canonical_name) for the given label, or (None, None) if this label
        hasn't been processed yet.
        """
        try:
            search_result = self.identifiers.search(
                accessible_scopes=self.accessible_scopes,
                name=ScopedName.from_string(label_name))
            search_result.assert_fully_parsed()
        except IdentifierError as exc:
            raise PreprocessorError(str(exc), location=location)

        if isinstance(search_result.identifier_definition, FutureIdentifierDefinition):
            return None, search_result.canonical_name

        if not isinstance(search_result.identifier_definition, LabelDefinition):
            raise PreprocessorError(
                f"Expected a label name. Identifier '{label_name}' is of type "
                f'{search_result.identifier_definition.TYPE}.', location=location)
        return search_result.identifier_definition.pc, search_result.canonical_name

    def get_variable(self, var: ExprIdentifier):
        identifier_definition = self.search_identifier(var.name, var.location)
        # Check that identifier_definition is not None for mypy.
        assert identifier_definition is not None

        if isinstance(identifier_definition, FutureIdentifierDefinition):
            if identifier_definition.identifier_type == LabelDefinition:
                # Allow future label assignment.
                return ExprFutureLabel(identifier=var)
            raise PreprocessorError(
                f"Identifier '{var.name}' referenced before definition.",
                location=var.location)

        if isinstance(identifier_definition, ConstDefinition):
            return identifier_definition.value

        if isinstance(identifier_definition, LabelDefinition):
            return identifier_definition.pc

        if isinstance(identifier_definition, MemberDefinition):
            return identifier_definition.offset

        if isinstance(identifier_definition, (ReferenceDefinition, OffsetReferenceDefinition)):
            try:
                res_expr = identifier_definition.eval(
                    reference_manager=self.flow_tracking.reference_manager,
                    flow_tracking_data=self.flow_tracking.data)
                if var.location is not None:
                    res_expr = add_parent_location(
                        expr=res_expr,
                        new_parent_location=var.location,
                        message=f"While expanding the reference '{var.name}' in:")
                return res_expr
            except FlowTrackingError as exc:
                raise PreprocessorError(
                    f"Reference '{var.name}' was revoked.", location=var.location, notes=exc.notes)
            except DefinitionError as exc:
                raise PreprocessorError(str(exc), location=var.location)

        raise PreprocessorError(
            f'Unexpected identifier {var.name} of type {identifier_definition.TYPE}.',
            location=var.location)

    def get_instruction_size(
            self, instruction: InstructionAst, allow_auto_deduction: bool = False):
        """
        Returns the size of the instruction in field elements by calling build_instruction().
        If allow_auto_deduction is True, then in some cases (where labels are involved)
        build_instruction() will not be used.
        """
        try:
            return get_instruction_size(instruction, allow_auto_deduction)
        except InstructionBuilderError as exc:
            # If for some reason location is not known, use the location of the full instruction.
            if exc.location is None:
                exc.notes.append('Missing exact location information on this error.')
                exc.location = instruction.location
            exc.notes.append(f'Preprocessed instruction:\n{instruction.format()}')
            raise exc

    def check_preprocessed_instruction(self, instruction: InstructionAst):
        """
        Verifies that the instruction was successfully preprocessed.
        For example, an instruction of type JumpToLabelInstruction whose label is not known will
        remain of this type, which is not accepted by build_instruction().
        """
        if isinstance(instruction.body, (JumpToLabelInstruction, CallLabelInstruction)):
            label = instruction.body.label
            raise PreprocessorError(f'Unknown label {label.name}.', location=label.location)

    def check_no_hints(self, msg):
        """
        Makes sure that there are no unprocessed hints, and throws an exception with the given
        message otherwise.
        """
        if self.next_instruction_hint is not None:
            raise PreprocessorError(msg, location=self.next_instruction_hint.location)

    def new_unique_id(self) -> str:
        """
        Returns a new identifier name.
        """
        name = f'__temp{self.next_temp_id}'
        self.next_temp_id += 1
        self.scoped_temp_ids.add(self.current_scope + name)
        return name


class PreprocessorCompoundExpressionContext(CompoundExpressionContext):
    def __init__(self, preprocessor: Preprocessor):
        self.preprocessor = preprocessor

    def new_tempvar_name(self) -> str:
        return self.preprocessor.new_unique_id()

    def get_fp_val(self, location: Optional[Location]) -> Expression:
        try:
            return self.preprocessor.simplify_expr_as_felt(
                ExprIdentifier(name='__fp__', location=location))
        except PreprocessorError as exc:
            if 'Unknown identifier' not in exc.message:
                raise
            raise PreprocessorError(
                'Using the value of fp directly, requires defining a variable named __fp__.',
                location=exc.location)
