import dataclasses
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple, Type, cast

from starkware.cairo.lang.compiler.ast.cairo_types import (
    CairoType, TypeFelt, TypePointer, TypeStruct)
from starkware.cairo.lang.compiler.ast.code_elements import (
    BuiltinsDirective, CodeBlock, CodeElement, CodeElementAllocLocals, CodeElementCompoundAssertEq,
    CodeElementConst, CodeElementDirective, CodeElementEmptyLine, CodeElementFuncCall,
    CodeElementFunction, CodeElementHint, CodeElementIf, CodeElementImport, CodeElementInstruction,
    CodeElementLabel, CodeElementLocalVariable, CodeElementMember, CodeElementReference,
    CodeElementReturn, CodeElementReturnValueReference, CodeElementStaticAssert,
    CodeElementTemporaryVariable, CodeElementUnpackBinding)
from starkware.cairo.lang.compiler.ast.expr import (
    ArgListItem, EllipsisSymbol, ExprAssignment, ExprCast, ExprConst, ExprDeref, Expression,
    ExprFutureLabel, ExprIdentifier, ExprOperator, ExprReg)
from starkware.cairo.lang.compiler.ast.formatting_utils import get_max_line_length
from starkware.cairo.lang.compiler.ast.instructions import (
    AddApInstruction, AssertEqInstruction, CallInstruction, CallLabelInstruction, InstructionAst,
    InstructionBody, JnzInstruction, JumpInstruction, JumpToLabelInstruction, RetInstruction)
from starkware.cairo.lang.compiler.ast.module import CairoModule
from starkware.cairo.lang.compiler.ast.rvalue import RvalueCallInst, RvalueFuncCall
from starkware.cairo.lang.compiler.ast.visitor import Visitor
from starkware.cairo.lang.compiler.constants import SIZE_CONSTANT
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.expression_simplifier import ExpressionSimplifier
from starkware.cairo.lang.compiler.identifier_definition import (
    ConstDefinition, DefinitionError, FutureIdentifierDefinition, IdentifierDefinition,
    LabelDefinition, MemberDefinition, OffsetReferenceDefinition, ReferenceDefinition,
    get_struct_size)
from starkware.cairo.lang.compiler.identifier_manager import IdentifierError, IdentifierManager
from starkware.cairo.lang.compiler.identifier_utils import get_struct_members, resolve_search_result
from starkware.cairo.lang.compiler.import_loader import collect_imports
from starkware.cairo.lang.compiler.instruction import Register
from starkware.cairo.lang.compiler.instruction_builder import (
    InstructionBuilderError, get_instruction_size)
from starkware.cairo.lang.compiler.location_utils import add_parent_location
from starkware.cairo.lang.compiler.preprocessor.compound_expressions import (
    CompoundExpressionContext, SimplicityLevel, process_compound_assert,
    process_compound_expressions)
from starkware.cairo.lang.compiler.preprocessor.flow import (
    FlowTracking, FlowTrackingDataActual, FlowTrackingDataUnreachable, InstructionFlows,
    ReferenceManager)
from starkware.cairo.lang.compiler.preprocessor.identifier_collector import (
    AnonymousLabelGenerator, IdentifierCollector)
from starkware.cairo.lang.compiler.preprocessor.local_variables import (
    create_simple_ref_expr, preprocess_local_variables)
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.preprocessor.preprocessor_utils import assert_no_modifier
from starkware.cairo.lang.compiler.preprocessor.reg_tracking import (
    RegChange, RegChangeKnown, RegChangeUnconstrained, RegChangeUnknown, RegTrackingData)
from starkware.cairo.lang.compiler.references import FlowTrackingError, Reference, translate_ap
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.substitute_identifiers import substitute_identifiers
from starkware.cairo.lang.compiler.type_system_visitor import (
    check_assign_cast, check_unpack_cast, get_expr_addr, simplify_type_system)


@dataclasses.dataclass
class PreprocessedInstruction:
    instruction: InstructionAst
    # List of fully qualified scope names accessible by the hint function of this instruction.
    accessible_scopes: List[ScopedName]
    hint: Optional[CodeElementHint]
    flow_tracking_data: FlowTrackingDataActual

    def format(self) -> str:
        return (self.hint.format(get_max_line_length()) + '\n' if self.hint is not None else '') + \
            self.instruction.format()


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

    def format(self) -> str:
        """
        Returns the program as a string.
        This can be used to print the preprocessor intermediate output.
        """
        code = self._directives_code()
        code += ''.join(inst.format() + '\n' for inst in self.instructions)
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


class Preprocessor(Visitor):
    """
    Reads the AST representing the input and recreates it after handling the following:
    * Labels.
    * Constant values.
    * Functions.
    """

    def __init__(self, prime: int):
        super().__init__()
        self.prime: int = prime
        self.instructions: List[PreprocessedInstruction] = []
        # Stores the program counter of the next instruction (where the first instruction is at 0).
        # This is equal to the size of the code (in field elements) so far.
        self.current_pc = 0
        # Generates anonymous labels.
        self.anon_label_gen = AnonymousLabelGenerator()
        self.simplifier = ExpressionSimplifier(prime)

        self.identifiers = IdentifierManager()
        self.identifier_locations: Dict[ScopedName, Location] = {}

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
        self.scoped_temp_ids: Set[ScopedName] = set()

        self._compound_expression_context = PreprocessorCompoundExpressionContext(preprocessor=self)

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

    def remove_unresolved_futures(self):
        """
        Removes any unresolved future identifier definitions.
        """
        self.identifiers.remove_unresolved_futures()

    def resolve_labels(self):
        """
        Performs a second pass on the instructions to resolve labels.
        """
        self.instructions, old_instructions = [], self.instructions
        self.current_pc, old_pc = 0, self.current_pc
        self.flow_tracking, old_flow_tracking = FlowTracking(), self.flow_tracking
        self.anon_label_gen, old_anon_label_gen = AnonymousLabelGenerator(), self.anon_label_gen

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
        self.anon_label_gen = old_anon_label_gen

    def get_program(self):
        return PreprocessedProgram(
            prime=self.prime,
            reference_manager=self.flow_tracking.reference_manager,
            instructions=list(self.instructions),
            identifiers=self.identifiers,
            identifier_locations=self.identifier_locations,
            builtins=[] if self.builtins is None else self.builtins,
        )

    def visit_CodeElementFunction(self, elm: CodeElementFunction):
        self.check_no_hints('Hints before functions are not allowed.')
        if elm.element_type != 'struct':
            self.flow_tracking.revoke()

        self.add_label(elm.identifier)

        new_scope = self.current_scope + elm.name
        if elm.element_type == 'func':
            self.function_metadata[new_scope] = FunctionMetadata(
                initial_ap_data=self.flow_tracking.get_ap_tracking())

        # Add function arguments and return values and process body.
        args = elm.arguments.identifiers
        args_scope = new_scope + CodeElementFunction.ARGUMENT_SCOPE

        # Create the Args struct.
        offset = 0
        member_defs = []
        for arg in args:
            assert_no_modifier(arg)
            cairo_type = self.resolve_type(arg.get_type())
            member_def = MemberDefinition(offset=offset, cairo_type=cairo_type)
            member_defs.append(member_def)
            self.add_name_definition(
                name=args_scope + arg.identifier.name,
                identifier_definition=member_def,
                location=arg.location)
            offset += self.get_size(cairo_type)

        self.add_name_definition(
            args_scope + SIZE_CONSTANT,
            ConstDefinition(value=offset),
            location=elm.identifier.location)

        # Skip return fp and pc.
        offset += 2

        # Create the references for the arguments.
        for arg, member_def in zip(args, member_defs):
            # Add a reference for the argument.
            self.add_simple_reference(
                name=new_scope + arg.identifier.name, reg=Register.FP,
                cairo_type=member_def.cairo_type, offset=member_def.offset - offset,
                location=arg.location)

        # Add Return struct.
        return_scope = new_scope + CodeElementFunction.RETURN_SCOPE
        rets = elm.returns.identifiers if elm.returns is not None else []
        offset = 0
        for ret in rets:
            assert_no_modifier(ret)
            expr_type = ret.get_type()
            cairo_type = self.resolve_type(expr_type)
            self.add_name_definition(
                return_scope + ret.identifier.name,
                MemberDefinition(offset=offset, cairo_type=cairo_type),
                location=ret.location)
            offset += self.get_size(expr_type)

        self.add_name_definition(
            return_scope + SIZE_CONSTANT,
            ConstDefinition(value=offset),
            location=elm.identifier.location)

        # Process code_elements.
        with self.scoped(new_scope):
            # Process local variable declaration.
            code_elements = preprocess_local_variables(
                code_elements=[x.code_elm for x in elm.code_block.code_elements],
                scope=new_scope,
                new_unique_id_callback=self.new_unique_id,
                get_size_callback=self.get_size,
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
        label_neq_name = self.anon_label_gen.get()
        label_end_name = self.anon_label_gen.get()
        label_neq = ExprIdentifier(name=label_neq_name, location=elm.location)
        label_end = ExprIdentifier(name=label_end_name, location=elm.location)

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
        assert_no_modifier(elm.typed_identifier)

        identifier = elm.typed_identifier.identifier
        expr_type = elm.typed_identifier.get_type()
        name = self.current_scope + identifier.name
        val = self.simplify_expr_as_felt(elm.expr)
        if not isinstance(val, ExprConst):
            raise PreprocessorError('Expected a constant expression.', location=elm.expr.location)
        self.add_name_definition(
            name,
            MemberDefinition(offset=val.val, cairo_type=self.resolve_type(expr_type)),
            location=identifier.location)

    def visit_CodeElementReference(self, elm: CodeElementReference):
        name = self.current_scope + elm.typed_identifier.identifier.name
        val, val_type = self.simplify_expr(elm.expr)

        if elm.typed_identifier.expr_type is not None:
            dst_type = self.resolve_type(elm.typed_identifier.expr_type)
        else:
            # Copy the type from the value.
            dst_type = val_type
        if not check_assign_cast(src_type=val_type, dest_type=dst_type):
            raise PreprocessorError(
                f"Cannot assign an expression of type '{val_type.format()}' "
                f"to a reference of type '{dst_type.format()}'.",
                location=dst_type.location)

        val = ExprCast(expr=val, dest_type=dst_type)

        self.add_reference(
            name=name,
            reference=Reference(
                pc=self.current_pc,
                value=val,
                ap_tracking_data=self.flow_tracking.get_ap_tracking()),
            location=elm.typed_identifier.location,
        )

    def visit_CodeElementLocalVariable(self, elm: CodeElementLocalVariable):
        raise PreprocessorError(
            'Local variables are not supported outside of functions.', location=elm.location)

    def visit_CodeElementTemporaryVariable(self, elm: CodeElementTemporaryVariable):
        assert_no_modifier(elm.typed_identifier)

        # Build the instruction: [ap] = elm.expr; ap++.
        compound_expressions_code_elements, (expr,), _ = process_compound_expressions(
            [self.simplify_expr_as_felt(elm.expr)], [SimplicityLevel.OPERATION],
            context=self._compound_expression_context)
        for code_element in compound_expressions_code_elements:
            self.visit(code_element)

        # Store the hint to avoid the check_no_hints() when invoking the reference element.
        hint, self.next_instruction_hint = self.next_instruction_hint, None

        if elm.typed_identifier.expr_type is not None:
            expr_type = elm.typed_identifier.expr_type
        else:
            # Copy the type from the original expression.
            _, expr_type = self.simplify_expr(elm.expr)
        if isinstance(expr_type, TypeStruct):
            raise PreprocessorError(
                "tempvar type annotation must be 'felt' or a pointer.",
                location=expr_type.location)

        # Build an expression for [ap].
        deref_ap = ExprCast(
            expr=ExprDeref(
                addr=ExprReg(reg=Register.AP, location=elm.typed_identifier.identifier.location),
                location=elm.typed_identifier.identifier.location),
            dest_type=expr_type,
            location=elm.typed_identifier.identifier.location)

        # Convert CodeElementTemporaryVariable to two code elements.
        # Build the code element: let <elm.identifier> = [ap].
        self.visit(CodeElementReference(
            typed_identifier=elm.typed_identifier,
            expr=deref_ap,
        ))

        # Restore the hint.
        assert self.next_instruction_hint is None
        self.next_instruction_hint = hint

        self.visit(CodeElementInstruction(
            instruction=InstructionAst(
                body=AssertEqInstruction(
                    a=deref_ap,
                    b=expr,
                    location=elm.location,
                ),
                inc_ap=True,
                location=elm.location)))

    def visit_CodeElementCompoundAssertEq(self, instruction: CodeElementCompoundAssertEq):
        compound_expressions_code_elements, (expr_a, expr_b) = process_compound_assert(
            self.simplify_expr_as_felt(instruction.a),
            self.simplify_expr_as_felt(instruction.b),
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

    def handle_ellipsis(self, items: List[ArgListItem]) -> Tuple[List[ExprAssignment], bool]:
        """
        Returns (new_exprs, ellipsis).
        If items starts with EllipsisSymbol, removes it and returns ellipsis=True.
        Verifies that the rest of the expressions are not EllipsisSymbol.
        """
        ellipsis = len(items) > 0 and isinstance(items[0], EllipsisSymbol)
        if ellipsis:
            items = items[1:]

        for item in items:
            if isinstance(item, EllipsisSymbol):
                raise PreprocessorError(
                    'Ellipsis ("...") can only be used at the beginning of the list.',
                    location=item.location)
            assert isinstance(item, ExprAssignment)

        return cast(List[ExprAssignment], items), ellipsis

    def process_expr_assignment_list(
            self, exprs: List[ExprAssignment], ellipsis: bool, struct_name: ScopedName,
            location: Optional[Location]):
        """
        Generates instructions to push all expressions onto the stack.
        Verifies the correctness of expr assignment with respect to the expected struct.
        In more details: translates a list of expressions to a set of instructions evaluating the
        expressions and storing the values to memory, starting from address 'ap'.

        exprs - list of ExprAssignment objects to process.
        struct_name - ScopedName of the struct against which the expr list is verified.
        location - location to attach to errors if no finer location is relevant.
        """

        struct_full_name = self.get_fully_qualified_scope(struct_name, location)

        struct_size_definition = self.identifiers.get_by_full_name(struct_full_name + SIZE_CONSTANT)
        if isinstance(struct_size_definition, FutureIdentifierDefinition):
            raise PreprocessorError(
                'The called function must be defined before the call site.',
                location=location)

        struct_members = get_struct_members(struct_full_name, identifier_manager=self.identifiers)
        n_members = len(struct_members)
        if ellipsis:
            # Make sure we don't have too many expressions. We allow to return only a suffix of the
            # struct.
            if len(exprs) > n_members - 1:
                if n_members == 0:
                    error_msg = (
                        'Ellipsis ("...") is not supported for functions with no return values. '
                        "Use 'return()' instead.")
                else:
                    expected_n_args = 'none' if n_members <= 1 else f'at most {n_members - 1}'
                    # Removing the ellipsis may be helpful only when all members appear.
                    optional_suggestion = 'Ellipsis ("...") should be removed.'
                    error_msg = \
                        f'Too many expressions. Expected {expected_n_args}, got {len(exprs)}.' + \
                        (f' {optional_suggestion}' if len(exprs) == n_members else '')
                raise PreprocessorError(message=error_msg, location=location)
        else:
            # Make sure we have the correct number of expressions.
            if len(exprs) != n_members:
                raise PreprocessorError(
                    f'Expected exactly {n_members} expressions, got {len(exprs)}.',
                    location=location)

        # Take the last len(exprs) member to handle Ellipsis.
        passed_args = list(struct_members.items())[n_members - len(exprs):]

        offset = 0
        if ellipsis and len(passed_args) > 0:
            # Start from the offset of the first expected member to handle Ellipsis.
            offset = passed_args[0][1].offset

        reached_named = False
        compound_expressions = []
        for (member_name, member_def), expr_assignment in zip(passed_args, exprs):
            if isinstance(expr_assignment, EllipsisSymbol):
                raise PreprocessorError(
                    'Ellipsis ("...") can only be used at the beginning of the list.',
                    location=expr_assignment.location)

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

            # Check member offset after checking the name to improve error message.
            if offset != member_def.offset:
                raise PreprocessorError(
                    f"""\
'{member_name}' is at offset {member_def.offset}, the expected offset is {offset}.""",
                    location=expr_assignment.location)

            felt_expr_list = self.simplify_expr_to_felt_expr_list(
                expr_assignment.expr, member_def.cairo_type)
            compound_expressions.extend(felt_expr_list)
            offset += len(felt_expr_list)

        struct_size = self.get_struct_size(struct_name, location)
        if offset != struct_size and len(passed_args) > 0:
            raise PreprocessorError(
                f"'{struct_name}' ended at offset {offset}, the expected offset is {struct_size}.",
                location=location)

        # Generate instructions.
        compound_expressions_code_elements, simple_exprs, first_compound_expr = \
            process_compound_expressions(
                compound_expressions,
                SimplicityLevel.OPERATION,
                context=self._compound_expression_context)

        if ellipsis and first_compound_expr is not None:
            raise PreprocessorError(
                'Compound expressions cannot be used with an ellipsis ("...").',
                location=first_compound_expr.location)

        for code_element in compound_expressions_code_elements:
            self.visit(code_element)

        assert len(simple_exprs) == len(compound_expressions)
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

    def visit_CodeElementReturn(self, elm: CodeElementReturn):
        exprs, ellipsis = self.handle_ellipsis(elm.exprs)
        self.process_expr_assignment_list(
            exprs=exprs,
            ellipsis=ellipsis,
            struct_name=CodeElementFunction.RETURN_SCOPE,
            location=elm.location,
        )
        code_elm_ret = CodeElementInstruction(
            instruction=InstructionAst(
                body=RetInstruction(),
                inc_ap=False,
                location=elm.location))
        self.visit(code_elm_ret)

    def visit_CodeElementFuncCall(self, elm: CodeElementFuncCall):
        exprs, ellipsis = self.handle_ellipsis(elm.func_call.exprs)
        self.process_expr_assignment_list(
            exprs=exprs,
            ellipsis=ellipsis,
            struct_name=ScopedName.from_string(elm.func_call.func_ident.name) +
            CodeElementFunction.ARGUMENT_SCOPE,
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
            reference=Reference(
                pc=self.current_pc,
                value=ref_expr,
                ap_tracking_data=self.flow_tracking.get_ap_tracking()),
            location=location,
        )

    def visit_CodeElementReturnValueReference(self, elm: CodeElementReturnValueReference):
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
            name=self.current_scope + elm.typed_identifier.identifier.name, reg=Register.AP,
            cairo_type=cairo_type, offset=-struct_size, location=elm.typed_identifier.location)

    def visit_CodeElementUnpackBinding(self, elm: CodeElementUnpackBinding):
        if not isinstance(elm.rvalue, RvalueFuncCall):
            raise PreprocessorError(
                f'Cannot unpack {elm.rvalue.format()}.',
                location=elm.rvalue.location)

        self.visit(CodeElementFuncCall(func_call=elm.rvalue))

        func_ident = elm.rvalue.func_ident
        return_type = self.resolve_type(TypeStruct(
            scope=ScopedName.from_string(func_ident.name) + CodeElementFunction.RETURN_SCOPE,
            is_fully_resolved=False,
            location=func_ident.location,
        ))
        assert isinstance(return_type, TypeStruct), f'Unexpected type {return_type}.'
        struct_members = get_struct_members(return_type.scope, identifier_manager=self.identifiers)

        expected_len = len(struct_members)
        unpacking_identifiers = elm.unpacking_list.identifiers
        if len(unpacking_identifiers) != len(struct_members):
            suffix = 's' if expected_len > 1 else ''
            raise PreprocessorError(
                f"""\
Expected {expected_len} unpacking identifier{suffix}, found {len(unpacking_identifiers)}.""",
                location=elm.unpacking_list.location)

        offset = 0
        return_value_size = self.get_size(return_type)
        for typed_identifier, member_def in zip(unpacking_identifiers, struct_members.values()):
            assert_no_modifier(typed_identifier)

            if typed_identifier.expr_type is not None:
                cairo_type = self.resolve_type(typed_identifier.get_type())
            else:
                cairo_type = member_def.cairo_type

            if not check_unpack_cast(src_type=member_def.cairo_type, dest_type=cairo_type):
                raise PreprocessorError(
                    f"""\
Expected expression of type '{member_def.cairo_type.format()}', got '{cairo_type.format()}'.""",
                    location=typed_identifier.location
                )

            if offset != member_def.offset:
                raise PreprocessorError(
                    f"Failed to unpack '{return_type.format()}', the struct is discontinuous.",
                    location=return_type.location)

            self.add_simple_reference(
                name=self.current_scope + typed_identifier.identifier.name, reg=Register.AP,
                cairo_type=cairo_type, offset=offset - return_value_size,
                location=typed_identifier.location)

            offset += self.get_size(cairo_type)

        if offset != return_value_size:
            raise PreprocessorError(
                f"""\
'{return_type.format()}' ended at offset {offset}, the expected offset is {return_value_size}.""",
                location=return_type.location)

    def add_name_definition(
            self, name: ScopedName, identifier_definition: IdentifierDefinition, location):
        """
        Adds a definition of an identifier named 'name' at 'location'.
        Identifier must already be found as a FutureIdentifierDefinition in 'self.identifiers'
        and be of a compatible type, unless it's a temporary variable.
        """
        if name not in self.scoped_temp_ids:
            future_definition = self.identifiers.get_by_full_name(name)
            if future_definition is None:
                raise PreprocessorError(
                    f"Identifier '{name}' not found by IdentifierCollector.",
                    location=location)
            if not isinstance(future_definition, FutureIdentifierDefinition):
                raise PreprocessorError(f"Redefinition of '{name}'.", location=location)
            if not isinstance(identifier_definition, future_definition.identifier_type):
                raise PreprocessorError(
                    f"Identifier '{name}' expected to be of type "
                    f"'{future_definition.identifier_type.__name__}', not "
                    f"'{type(identifier_definition).__name__}'.",
                    location=location)

        self.identifiers.add_identifier(name, identifier_definition)
        self.identifier_locations[name] = location

    def add_label(self, identifier: ExprIdentifier):
        name = self.current_scope + identifier.name
        self.flow_tracking.converge_with_label(name)
        self.add_name_definition(
            name,
            LabelDefinition(pc=self.current_pc),  # type: ignore
            location=identifier.location)

    def add_reference(self, name: ScopedName, reference: Reference, location: Optional[Location]):
        self.flow_tracking.add_reference(name, reference)
        existing_definition = self.identifiers.get_by_full_name(name)
        if isinstance(existing_definition, ReferenceDefinition):
            # Rebind reference.
            existing_definition.references.append(reference)
        else:
            self.add_name_definition(
                name,
                ReferenceDefinition(full_name=name, references=[reference]),
                location=location)

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
        self.builtins = directive.builtins

    def simplify_expr(self, expr) -> Tuple[Expression, CairoType]:
        """
        Simplifies the expression by resolving identifiers, type-system related reductions
        and numeric simplifications.
        Returns the simplified expression and its type.
        """
        expr = substitute_identifiers(expr, get_identifier_callback=self.get_variable)
        expr, expr_type = simplify_type_system(expr)
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

        if not check_assign_cast(src_type=expr_type, dest_type=expected_type):
            raise PreprocessorError(
                f"""\
Expected expression of type '{expected_type.format()}', got '{expr_type.format()}'.""",
                location=location
            )

        if isinstance(expr_type, (TypeFelt, TypePointer)):
            return [expr]

        assert isinstance(expr_type, TypeStruct), f'Unexpected type {expr_type}.'

        struct_members = get_struct_members(expr_type.scope, identifier_manager=self.identifiers)
        addr = get_expr_addr(expr)
        exprs: List[Expression] = []
        for offset, member_def in enumerate(struct_members.values()):
            if not isinstance(member_def.cairo_type, (TypeFelt, TypePointer)):
                raise PreprocessorError(
                    'Nested structs are not supported.',
                    location=location)

            if offset != member_def.offset:
                raise PreprocessorError(
                    'Discontinuous structs are not supported.',
                    location=location)

            # Call simplifier to convert (fp + offset_1) + offset_2 to fp + (offset_1 + offset_2).
            exprs.append(
                self.simplifier.visit(
                    ExprDeref(
                        ExprOperator(
                            a=addr,
                            op='+',
                            b=ExprConst(member_def.offset, location=location),
                            location=location,
                        ),
                        location=location,
                    )))

        return exprs

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

    def get_struct_size(self, struct_name: ScopedName, location: Optional[Location]):
        size_identifier = struct_name + SIZE_CONSTANT
        size_definition = self.search_identifier(str(size_identifier), location)
        if not isinstance(size_definition, ConstDefinition):
            raise PreprocessorError(
                f'{size_identifier} must be a constant.',
                location=location)
        return size_definition.value

    def get_size(self, cairo_type: CairoType):
        """
        Returns the size of the given type.
        """
        if isinstance(cairo_type, (TypeFelt, TypePointer)):
            return 1
        elif isinstance(cairo_type, TypeStruct):
            if cairo_type.is_fully_resolved:
                try:
                    return get_struct_size(
                        struct_name=cairo_type.scope, identifier_values=self.identifiers.as_dict())
                except DefinitionError as exc:
                    raise PreprocessorError(str(exc), location=cairo_type.location)
            else:
                return self.get_struct_size(
                    struct_name=cairo_type.scope, location=cairo_type.location)
        else:
            raise NotImplementedError(f'Type {type(cairo_type).__name__} is not supported.')

    def resolve_type(self, cairo_type: CairoType) -> CairoType:
        """
        Resolves a CairoType instance to fully qualified name.
        """
        if isinstance(cairo_type, TypeFelt):
            return cairo_type
        elif isinstance(cairo_type, TypePointer):
            return dataclasses.replace(cairo_type, pointee=self.resolve_type(cairo_type.pointee))
        elif isinstance(cairo_type, TypeStruct):
            if cairo_type.is_fully_resolved:
                return cairo_type
            return dataclasses.replace(
                cairo_type,
                scope=self.get_fully_qualified_scope(
                    cairo_type.scope, location=cairo_type.location),
                is_fully_resolved=True)
        else:
            raise NotImplementedError(f'Type {type(cairo_type).__name__} is not supported.')

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
            except FlowTrackingError:
                raise PreprocessorError(
                    f"Reference '{var.name}' was revoked.", location=var.location)
            except DefinitionError as exc:
                raise PreprocessorError(str(exc), location=var.location)

        raise PreprocessorError(
            f'Unexpected identifier {var.name} of type {identifier_definition.TYPE}.',
            location=var.location)

    def get_fully_qualified_scope(
            self, scope: ScopedName, location: Optional[Location]) -> ScopedName:
        """
        Returns the fully qualified canonical scope name that corresponds to the given identifier.
        location is used if there is an error.
        """
        try:
            return self.identifiers.search_scope(
                accessible_scopes=self.accessible_scopes, name=scope).fullname
        except IdentifierError as exc:
            raise PreprocessorError(str(exc), location=location)

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


def default_read_module(module_name: str):
    raise Exception(
        f'Error: trying to read module {module_name}, no reading algorithm provided.')


def preprocess_str(
        code: str, prime: int, main_scope: ScopedName = ScopedName()) -> PreprocessedProgram:
    return preprocess_codes(
        [(code, '')], prime, read_module=default_read_module, main_scope=main_scope)


def preprocess_codes(
        codes: Sequence[Tuple[str, str]], prime: int,
        read_module: Callable[[str], Tuple[str, str]],
        main_scope: ScopedName = ScopedName(),
        preprocessor_cls: Optional[Type[Preprocessor]] = None) -> PreprocessedProgram:
    """
    Preprocesses a list of Cairo file and returns a PreprocessedProgram instance.
    codes is a list of pairs (code_string, file_name).
    read_module is a callback that gets a module name ('a.b.c') and returns a pair
    (file content, file name)
    """
    modules = []
    for code, filename in codes:
        # Function used to read files given module names.
        # The root module (filename) is handled separately, for this module code is returned.
        def read_file_fixed(name):
            return (code, filename) if name == filename else read_module(name)

        files = collect_imports(filename, read_file=read_file_fixed)
        for module_name, ast in files.items():
            # Preprocess files explicitly provided in the root scope.
            scope = main_scope if module_name == filename else ScopedName.from_string(module_name)
            modules.append(CairoModule(cairo_file=ast, module_name=scope))

    if preprocessor_cls is None:
        preprocessor_cls = Preprocessor

    preprocessor = preprocessor_cls(prime=prime)
    identifier_collector = IdentifierCollector()
    for module in modules:
        identifier_collector.visit(module)
    preprocessor.update_identifiers(identifier_collector.identifiers)
    for module in modules:
        preprocessor.visit(module)

    preprocessor.resolve_labels()
    return preprocessor.get_program()


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
