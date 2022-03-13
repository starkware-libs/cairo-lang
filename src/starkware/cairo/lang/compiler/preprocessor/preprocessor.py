import dataclasses
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import field
from enum import Enum, auto
from typing import DefaultDict, Dict, List, Optional, Set, Tuple, Type, Union, cast

import marshmallow.fields as mfields

from starkware.cairo.lang.compiler.ast.arguments import IdentifierList
from starkware.cairo.lang.compiler.ast.cairo_types import (
    CairoType,
    CastType,
    TypeCodeoffset,
    TypeFelt,
    TypePointer,
    TypeStruct,
    TypeTuple,
)
from starkware.cairo.lang.compiler.ast.code_elements import (
    BuiltinsDirective,
    CodeBlock,
    CodeElement,
    CodeElementAllocLocals,
    CodeElementCompoundAssertEq,
    CodeElementConst,
    CodeElementDirective,
    CodeElementEmptyLine,
    CodeElementFuncCall,
    CodeElementFunction,
    CodeElementHint,
    CodeElementIf,
    CodeElementImport,
    CodeElementInstruction,
    CodeElementLabel,
    CodeElementLocalVariable,
    CodeElementMember,
    CodeElementReference,
    CodeElementReturn,
    CodeElementReturnValueReference,
    CodeElementScoped,
    CodeElementStaticAssert,
    CodeElementTailCall,
    CodeElementTemporaryVariable,
    CodeElementTypeDef,
    CodeElementUnpackBinding,
    CodeElementWith,
    CodeElementWithAttr,
    CommentedCodeElement,
    LangDirective,
)
from starkware.cairo.lang.compiler.ast.expr import (
    ExprAssignment,
    ExprCast,
    ExprConst,
    ExprDeref,
    ExprDot,
    Expression,
    ExprFutureLabel,
    ExprHint,
    ExprIdentifier,
    ExprNewOperator,
    ExprOperator,
    ExprReg,
    ExprTuple,
)
from starkware.cairo.lang.compiler.ast.expr_func_call import ExprFuncCall
from starkware.cairo.lang.compiler.ast.formatting_utils import get_max_line_length
from starkware.cairo.lang.compiler.ast.instructions import (
    AddApInstruction,
    AssertEqInstruction,
    CallInstruction,
    CallLabelInstruction,
    DefineWordInstruction,
    InstructionAst,
    InstructionBody,
    JnzInstruction,
    JumpInstruction,
    JumpToLabelInstruction,
    RetInstruction,
)
from starkware.cairo.lang.compiler.ast.module import CairoModule
from starkware.cairo.lang.compiler.ast.rvalue import RvalueCallInst, RvalueFuncCall
from starkware.cairo.lang.compiler.ast.types import TypedIdentifier
from starkware.cairo.lang.compiler.constants import SIZE_CONSTANT
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.expression_simplifier import ExpressionSimplifier
from starkware.cairo.lang.compiler.expression_transformer import ExpressionTransformer
from starkware.cairo.lang.compiler.identifier_definition import (
    ConstDefinition,
    DefinitionError,
    FunctionDefinition,
    FutureIdentifierDefinition,
    IdentifierDefinition,
    LabelDefinition,
    MemberDefinition,
    NamespaceDefinition,
    ReferenceDefinition,
    StructDefinition,
)
from starkware.cairo.lang.compiler.identifier_manager import IdentifierError, IdentifierManager
from starkware.cairo.lang.compiler.identifier_utils import get_struct_definition
from starkware.cairo.lang.compiler.injector import inject_code_elements
from starkware.cairo.lang.compiler.instruction import Register
from starkware.cairo.lang.compiler.instruction_builder import (
    InstructionBuilderError,
    get_instruction_size,
)
from starkware.cairo.lang.compiler.location_utils import add_parent_location
from starkware.cairo.lang.compiler.offset_reference import OffsetReferenceDefinition
from starkware.cairo.lang.compiler.preprocessor.auxiliary_info_collector import (
    AuxiliaryInfoCollector,
)
from starkware.cairo.lang.compiler.preprocessor.compound_expressions import (
    CompoundExpressionContext,
    SimplicityLevel,
    process_compound_assert,
    process_compound_expressions,
)
from starkware.cairo.lang.compiler.preprocessor.flow import (
    FlowTracking,
    FlowTrackingDataActual,
    FlowTrackingDataUnreachable,
    FlowTrackingMemento,
    InstructionFlows,
    LostReferenceError,
    ReferenceManager,
)
from starkware.cairo.lang.compiler.preprocessor.identifier_aware_visitor import (
    IdentifierAwareVisitor,
)
from starkware.cairo.lang.compiler.preprocessor.local_variables import (
    create_simple_ref_expr,
    preprocess_local_variables,
)
from starkware.cairo.lang.compiler.preprocessor.memento import (
    AppendOnlyListMemento,
    ByValueMemento,
    ChainMapMemento,
    MembersMemento,
    Memento,
)
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.preprocessor.preprocessor_utils import assert_no_modifier
from starkware.cairo.lang.compiler.preprocessor.reg_tracking import (
    RegChange,
    RegChangeKnown,
    RegChangeUnconstrained,
    RegChangeUnknown,
    RegTrackingData,
)
from starkware.cairo.lang.compiler.proxy_identifier_manager import IdentifierManagerMemento
from starkware.cairo.lang.compiler.references import FlowTrackingError, Reference, translate_ap
from starkware.cairo.lang.compiler.resolve_search_result import resolve_search_result
from starkware.cairo.lang.compiler.scoped_name import ScopedName, ScopedNameAsStr
from starkware.cairo.lang.compiler.substitute_identifiers import substitute_identifiers
from starkware.cairo.lang.compiler.type_casts import check_cast
from starkware.cairo.lang.compiler.type_system_visitor import get_expr_addr, simplify_type_system
from starkware.python.utils import safe_zip
from starkware.starkware_utils.validated_dataclass import ValidatedDataclass

# Indicates that the compiler should be able to deduce the change in the ap register for this
# function.
KNOWN_AP_CHANGE_DECORATOR = "known_ap_change"

# Maximum number of tries in a reference trial. See ReferenceTrial.
MAX_REFERENCE_RETRIES = 4


class ReferenceChecker(ExpressionTransformer):
    """
    Checks that a reference expression is valid. Raises a PreprocessorError otherwise.
    """

    def visit_ExprHint(self, expr: ExprHint):
        raise PreprocessorError(
            "The use of hints in reference expressions is not allowed.", location=expr.location
        )

    def visit_ExprNewOperator(self, expr: ExprNewOperator):
        raise PreprocessorError(
            "The use of 'new' in reference expressions is not allowed.", location=expr.location
        )


class ReferenceTrial:
    """
    Keeps track of an active trial, in which the preprocessor will optimistically compile a
    function, and every revoked reference will be listed in bad_references, and evaluated
    as a dummy fp based reference for the duration of the trial.
    """

    def __init__(self):
        # A map of revoked references.
        # The key is (reference_name, reference object id (id())).
        # The value is (reference, exception).
        self.bad_references: Dict[Tuple[ScopedName, int], Tuple[Reference, Exception]] = {}

    @property
    def failed(self) -> bool:
        return len(self.bad_references) > 0

    @property
    def exception(self) -> Exception:
        assert self.failed
        _, err = next(iter(self.bad_references.values()))
        return err


@dataclasses.dataclass
class PreprocessedInstruction:
    instruction: InstructionAst
    # List of fully qualified scope names accessible by the hint function of this instruction.
    accessible_scopes: List[ScopedName]
    hints: List[Tuple[CodeElementHint, FlowTrackingDataActual]]
    flow_tracking_data: FlowTrackingDataActual

    def format(self, with_locations: bool = False) -> str:
        location_str = (
            f"  # {self.instruction.location.topmost_location()}."
            if with_locations and self.instruction.location is not None
            else ""
        )
        return (
            "".join(hint.format(get_max_line_length()) + "\n" for hint, _ in self.hints)
            + self.instruction.format()
            + location_str
        )


@dataclasses.dataclass(frozen=True)
class AttributeBase:
    name: str
    value: str


@dataclasses.dataclass(frozen=True)
class AttributeScope(AttributeBase, ValidatedDataclass):
    start_pc: int
    end_pc: int
    flow_tracking_data: Optional[FlowTrackingDataActual] = field(metadata=dict(load_default=None))
    accessible_scopes: List[ScopedName] = field(
        metadata=dict(marshmallow_field=mfields.List(ScopedNameAsStr, load_default=list)),
    )


@dataclasses.dataclass
class PreprocessedProgram:
    prime: int
    reference_manager: ReferenceManager
    instructions: List[PreprocessedInstruction]
    identifiers: IdentifierManager
    attributes: List[AttributeScope]
    # A map from an identifier fully qualified name to the location of its definition.
    # This provides additional information on the compiled program which can be used by IDEs.
    identifier_locations: Dict[ScopedName, Location]
    builtins: List[str]
    auxiliary_info: AuxiliaryInfoCollector

    def format(self, with_locations: bool = False) -> str:
        """
        Returns the program as a string.
        This can be used to print the preprocessor intermediate output.
        """
        code = self._directives_code()
        code += "".join(
            inst.format(with_locations=with_locations) + "\n" for inst in self.instructions
        )
        return code

    def _directives_code(self) -> str:
        code = ""
        if self.builtins:
            code += BuiltinsDirective(builtins=self.builtins).format() + "\n"
        if code:
            code += "\n"
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


class PreprocessorMemento(MembersMemento["Preprocessor"]):
    @classmethod
    def get_fields(cls) -> Dict[str, Type[Memento]]:
        return dict(
            instructions=AppendOnlyListMemento[PreprocessedInstruction],
            current_pc=ByValueMemento[int],
            flow_tracking=FlowTrackingMemento,
            next_temp_id=ByValueMemento[int],
            reference_states=ChainMapMemento[ScopedName, ReferenceState],
            scoped_temp_ids=ChainMapMemento[ScopedName, bool],
            attributes=AppendOnlyListMemento[AttributeScope],
            identifiers=IdentifierManagerMemento,
            identifier_locations=ChainMapMemento[ScopedName, Location],
        )


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
    auxiliary_info_cls: A class to be used to collect extra information during preprocessing.
    """

    def __init__(
        self,
        prime: int,
        builtins: List[str],
        identifiers: Optional[IdentifierManager] = None,
        supported_decorators: Optional[Set[str]] = None,
        functions_to_compile: Optional[Set[ScopedName]] = None,
        auxiliary_info_cls: Optional[Type[AuxiliaryInfoCollector]] = None,
    ):
        super().__init__(
            identifiers=identifiers,
        )
        self.prime: int = prime
        self.instructions: List[PreprocessedInstruction] = []
        # Stores the program counter of the next instruction (where the first instruction is at 0).
        # This is equal to the size of the code (in field elements) so far.
        self.current_pc = 0

        self.simplifier = ExpressionSimplifier(prime)

        # The hint for the next instruction.
        self.next_instruction_hints: List[Tuple[CodeElementHint, FlowTrackingDataActual]] = []

        # List of builtins.
        self.builtins = builtins

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
        # identifier collector.
        # Implemented as a dictionary to bool, because it has an efficient memento.
        # See PreprocessorMemento.
        self.scoped_temp_ids: Dict[ScopedName, bool] = {}

        if supported_decorators is None:
            supported_decorators = set()
        self.supported_decorators = supported_decorators

        self.functions_to_compile = functions_to_compile
        # A set of all scoped prefixes that were not traversed and need to be pruned form the
        # identifier manager.
        self.removed_prefixes: Set[ScopedName] = set()

        self.attributes: List[AttributeScope] = []

        self.auxiliary_info = (
            auxiliary_info_cls.create(prime) if auxiliary_info_cls is not None else None
        )

        # Current code element that is being processed.
        self.current_code_element: Optional[CodeElement] = None

        # When a reference trial is active, this object holds the required information about it.
        # See ReferenceTrial.
        self.reference_trial: Optional[ReferenceTrial] = None

    def check_reference_expression(self, expr: Expression):
        ReferenceChecker().visit(expr)

    def search_identifier(
        self, name: str, location: Optional[Location]
    ) -> Optional[IdentifierDefinition]:
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
        self, name: ScopedName, future_definition: FutureIdentifierDefinition
    ):
        """
        Adds a future definition of an identifier.
        """
        existing_definition = self.identifiers.get_by_full_name(name)
        assert existing_definition is None
        self.identifiers.add_identifier(name, future_definition)

    def visit_uncommented_code_block(self, code_elements: List[CodeElement]):
        # Process code.
        prev_code_element = self.current_code_element
        try:
            for elm in code_elements:
                self.current_code_element = elm
                self.visit(elm)
                # Directives must appear at the top.
                if not isinstance(elm, (CodeElementDirective, CodeElementEmptyLine)):
                    self.directives_allowed = False
        finally:
            self.current_code_element = prev_code_element

        # Make sure there are no hints at the end of the code block.
        self.check_no_hints(
            "Found a hint at the end of a code block. Hints must be followed by an instruction."
        )

    def visit_CodeElementScoped(self, elm: CodeElementScoped):
        with self.scoped(elm.scope, parent=elm):
            self.visit_uncommented_code_block(elm.code_elements)

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
                location=None,
            )
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

        assert self.accessible_scopes == [], "Unexpected preprocessor state."

        for preprocessed_instruction in old_instructions:
            self.accessible_scopes = preprocessed_instruction.accessible_scopes
            new_instruction = self.visit(preprocessed_instruction.instruction)
            self.check_preprocessed_instruction(new_instruction)
            self.current_pc += self.get_instruction_size(new_instruction)
            self.instructions.append(
                PreprocessedInstruction(
                    instruction=new_instruction,
                    accessible_scopes=preprocessed_instruction.accessible_scopes,
                    hints=preprocessed_instruction.hints,
                    flow_tracking_data=preprocessed_instruction.flow_tracking_data,
                )
            )

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
            attributes=self.attributes,
            builtins=self.builtins,
            auxiliary_info=self.auxiliary_info,
        )

    def create_struct_from_identifier_list(
        self,
        identifier_list: Optional[IdentifierList],
        struct_name: ScopedName,
        location: Optional[Location],
    ):
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
                location=arg.location,
            )
            offset += self.get_size(cairo_type)

        self.add_name_definition(
            struct_name + SIZE_CONSTANT, ConstDefinition(value=offset), location=location
        )

    def add_references_from_struct_members(
        self,
        identifier_list: Optional[IdentifierList],
        members: Dict[str, MemberDefinition],
        scope: ScopedName,
        start_offset: int,
    ):
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
                name=scope + arg.identifier.name,
                reg=Register.FP,
                cairo_type=member_def.cairo_type,
                offset=start_offset + member_def.offset,
                location=arg.location,
            )

    def visit_CodeElementFunction(self, elm: CodeElementFunction):
        self.check_no_hints("Hints before functions are not allowed.")
        if elm.element_type == "struct":
            return

        # Check decorator.
        known_ap_change_decorator: Optional[ExprIdentifier] = None
        for decorator in elm.decorators:
            if decorator.name == KNOWN_AP_CHANGE_DECORATOR and elm.element_type == "func":
                known_ap_change_decorator = decorator
                continue
            if decorator.name not in self.supported_decorators:
                raise PreprocessorError(
                    f"Unsupported decorator: '{decorator.name}'.", location=decorator.location
                )

        self.flow_tracking.revoke()

        new_scope = self.current_scope + elm.name

        if self.current_scope in self.function_metadata:
            outer_function_location = self.identifier_locations.get(self.current_scope)
            notes = []
            if outer_function_location is not None:
                loc_str = outer_function_location.to_string_with_content("")
                notes.append(f"Outer function was defined here: {loc_str}")

            raise PreprocessorError(
                "Nested functions are not supported."
                if elm.element_type == "func"
                else "Cannot define a namespace inside a function.",
                location=elm.identifier.location,
                notes=notes,
            )

        if elm.element_type == "func":
            # Check if this function should be skipped.
            if self.functions_to_compile is not None and new_scope not in self.functions_to_compile:
                self.removed_prefixes.add(new_scope)
                return

            self.add_function(elm)
        else:
            assert (
                elm.element_type == "namespace"
            ), f"""\
Expected 'elm.element_type' to be a 'namespace'. Found: '{elm.element_type}'."""
            self.add_name_definition(
                self.current_scope + elm.name,
                NamespaceDefinition(),
                location=elm.identifier.location,
            )

        # Add function arguments and return values and process body.
        args_scope = new_scope + CodeElementFunction.ARGUMENT_SCOPE
        implicit_args_scope = new_scope + CodeElementFunction.IMPLICIT_ARGUMENT_SCOPE

        # Create the references for the arguments.
        args_struct = get_struct_definition(args_scope, self.identifiers)
        self.add_references_from_struct_members(
            identifier_list=elm.arguments,
            members=args_struct.members,
            scope=new_scope,
            start_offset=-(2 + args_struct.size),
        )
        implicit_args_struct = get_struct_definition(implicit_args_scope, self.identifiers)
        self.add_references_from_struct_members(
            identifier_list=elm.implicit_arguments,
            members=implicit_args_struct.members,
            scope=new_scope,
            start_offset=-(2 + args_struct.size + implicit_args_struct.size),
        )

        new_reference_states = dict(self.reference_states)
        if elm.implicit_arguments is not None:
            for typed_identifier in elm.implicit_arguments.identifiers:
                new_reference_states[
                    new_scope + typed_identifier.name
                ] = ReferenceState.ALLOW_IMPLICIT

        if self.auxiliary_info is not None:
            self.auxiliary_info.start_function_info(
                name=str(new_scope),
                start_pc=self.current_pc,
                implicit_args_struct=implicit_args_struct,
                args_struct=args_struct,
            )

        # Process code_elements.
        with self.scoped(new_scope, parent=elm), self.set_reference_states(new_reference_states):
            self.visit_function_body_with_retries(
                code_block=elm.code_block, location=elm.identifier.location
            )

        if elm.element_type == "func":
            if self.flow_tracking.data != FlowTrackingDataUnreachable():
                raise PreprocessorError(
                    "Function must end with a return instruction or a jump.",
                    location=elm.identifier.location,
                )

            self.function_metadata[new_scope].completed = True
            if known_ap_change_decorator is not None:
                if not isinstance(
                    self.function_metadata[new_scope].total_ap_change, RegChangeKnown
                ):
                    raise PreprocessorError(
                        "The compiler was unable to deduce the change of the ap register, as "
                        "required by this decorator.",
                        location=known_ap_change_decorator.location,
                    )
            if self.function_metadata[new_scope].total_ap_change == RegChangeUnconstrained():
                # No returns occured.
                self.function_metadata[new_scope].total_ap_change = RegChangeUnknown()

            if self.auxiliary_info is not None:
                self.auxiliary_info.finish_function_info(end_pc=self.current_pc)

    def visit_function_body_with_retries(self, code_block: CodeBlock, location: Optional[Location]):
        """
        Visits the body of a function, with a reference trial if possible, to fix revocations.
        See ReferenceTrial.
        """
        # Add checkpoint.
        memento: Optional[PreprocessorMemento] = None
        try_index = 0
        try:
            while True:
                memento, preprocessor = PreprocessorMemento.from_object(self)
                has_alloc_locals, code_elements = preprocess_local_variables(
                    code_elements=[x.code_elm for x in code_block.code_elements],
                    scope=self.current_scope,
                    get_size_callback=self.get_size,
                    get_unpacking_struct_definition_callback=self.get_unpacking_struct_definition,
                    default_location=location,
                )

                # These cases cannot be fixed for reference revocations:
                # * Functions without alloc_locals.
                # * Contexts with self.auxiliary_info.
                if not has_alloc_locals or self.auxiliary_info is not None:
                    self.visit_uncommented_code_block(code_elements)
                    return

                # Visit body with a reference trial.
                self.reference_trial = reference_trial = ReferenceTrial()
                try:
                    self.visit_uncommented_code_block(code_elements)
                finally:
                    self.reference_trial = None

                if not reference_trial.failed:
                    # Success, accept the new changes.
                    return

                # Failure.
                if try_index >= MAX_REFERENCE_RETRIES:
                    # Too many retries, raise.
                    raise reference_trial.exception
                try_index += 1

                # Roll back.
                # PreprocessorMemento is inplace, so the restored preprocessor should be self.
                # This is important, since the caller still has the self object.
                assert self is memento.restore(preprocessor)
                memento = None

                # Fix revocations.
                code_block = self.fix_reference_revocations(
                    code_block=code_block, reference_trial=reference_trial
                )
        finally:
            if memento is not None:
                assert self is memento.apply(preprocessor)

    def fix_reference_revocations(
        self, code_block: CodeBlock, reference_trial: ReferenceTrial
    ) -> CodeBlock:
        """
        Fixes reference revocations that occurred during a reference trial, by injecting local x = x
        for each reference after the code element that defined it.
        """

        # A mapping of code elements to inject. See inject_code_elements().
        injections: DefaultDict[int, List[CommentedCodeElement]] = defaultdict(list)
        for (name, _reference_id), (reference, err) in reference_trial.bad_references.items():
            _, expr_type = self.simplify_expr(reference.value)
            definition_code_element = reference.definition_code_element
            if definition_code_element is None:
                # Definition site not found. Unrecoverable revocation.
                raise err

            # Inject a 'local x = x' after the code element that defines the reference.
            base_name = name.path[-1]
            # location: Optional[Location]
            if len(reference.locations) > 0:
                location = reference.locations[-1].with_parent_location(
                    new_parent_location=reference.locations[-1],
                    message=f"While auto generating local variable for '{base_name}'.",
                )
            else:
                location = None
            identifier = ExprIdentifier(
                name=name.path[-1],
                location=location,
            )
            injections[id(definition_code_element)].append(
                CommentedCodeElement(
                    code_elm=CodeElementLocalVariable(
                        typed_identifier=TypedIdentifier(
                            identifier=identifier,
                            expr_type=expr_type,
                            location=location,
                        ),
                        expr=identifier,
                        location=location,
                    ),
                    comment=None,
                    location=location,
                )
            )
        return inject_code_elements(
            ast=code_block,
            injections=injections,
        )

    def visit_CodeElementTypeDef(self, elm: CodeElementTypeDef):
        self.check_no_hints('Hints before "using" statements are not allowed.')

    def visit_CodeElementWith(self, elm: CodeElementWith):
        new_reference_states = dict(self.reference_states)
        for aliased_identifier in elm.identifiers:
            src_identifier = aliased_identifier.orig_identifier
            src_full_name = self.current_scope + src_identifier.name
            if aliased_identifier.local_name is not None:
                raise PreprocessorError(
                    "The 'as' keyword is not supported in 'with' statements.",
                    location=aliased_identifier.local_name.location,
                )

            src_identifier_definition = self.identifiers.get_by_full_name(src_full_name)
            if src_identifier_definition is None:
                raise PreprocessorError(
                    f"Unknown reference '{src_identifier.name}'.", location=src_identifier.location
                )

            if not isinstance(src_identifier_definition, ReferenceDefinition):
                raise PreprocessorError(
                    f"Expected '{src_identifier.name}' to be a reference, "
                    f"found: {src_identifier_definition.TYPE}.",
                    location=src_identifier.location,
                )

            new_reference_states[src_full_name] = ReferenceState.ALLOW_IMPLICIT

        with self.set_reference_states(new_reference_states):
            self.visit(elm.code_block)

    def visit_CodeElementWithAttr(self, elm: CodeElementWithAttr):
        start_pc = self.current_pc
        # Retrieve the flow_tracking_data and accessible_scopes before visiting the code block.
        flow_tracking_data = self.flow_tracking.get()
        accessible_scopes = self.accessible_scopes.copy()
        self.visit(elm.code_block)
        end_pc = self.current_pc
        self.attributes.append(
            AttributeScope(
                name=elm.attribute_name.name,
                value=elm.get_value(),
                start_pc=start_pc,
                end_pc=end_pc,
                flow_tracking_data=flow_tracking_data,
                accessible_scopes=accessible_scopes,
            )
        )

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
        cond_expr = self.simplify_expr_as_felt(
            ExprOperator(
                a=elm.condition.a, op="-", b=elm.condition.b, location=elm.condition.location
            )
        )
        if self.auxiliary_info is not None:
            self.auxiliary_info.start_if(
                expr_a=elm.condition.a, expr_b=elm.condition.b, cond_eq=elm.condition.eq
            )

        (res_cond_expr,) = process_compound_expressions(
            [cond_expr], [SimplicityLevel.DEREF], context=self._compound_expression_context
        )

        # Prepare labels.
        assert elm.label_neq is not None
        assert elm.label_end is not None
        label_neq = ExprIdentifier(name=elm.label_neq, location=elm.location)
        label_end = ExprIdentifier(name=elm.label_end, location=elm.location)

        # Add conditional jump.
        self.visit(
            CodeElementInstruction(
                InstructionAst(
                    body=JumpToLabelInstruction(
                        label=label_neq, condition=res_cond_expr, location=elm.location
                    ),
                    inc_ap=False,
                    location=elm.location,
                )
            )
        )

        if self.auxiliary_info is not None:
            self.auxiliary_info.end_if()

        # Determine code blocks.
        eq_code_block: Optional[CodeBlock]
        neq_code_block: Optional[CodeBlock]
        if elm.condition.eq:
            eq_code_block, neq_code_block = elm.main_code_block, elm.else_code_block
        else:
            eq_code_block, neq_code_block = elm.else_code_block, elm.main_code_block

        # Equal code block.
        if eq_code_block is not None:
            self.visit(eq_code_block)

        if self.flow_tracking.data != FlowTrackingDataUnreachable() and neq_code_block is not None:
            # Code block ended with a flow to next line. Since we have a "Not equal" block, we
            # add a jump to skip it.
            self.visit(
                CodeElementInstruction(
                    InstructionAst(
                        body=JumpToLabelInstruction(
                            label=label_end, condition=None, location=elm.location
                        ),
                        inc_ap=False,
                        location=elm.location,
                    )
                )
            )

        # Add the neq label.
        self.visit(CodeElementLabel(identifier=label_neq))

        # Not equal code block.
        if neq_code_block is not None:
            self.visit(neq_code_block)

        # Add the end label.
        self.visit(CodeElementLabel(identifier=label_end))

    def visit_CodeElementDirective(self, elm: CodeElementDirective):
        # Visit directive.
        if not self.directives_allowed:
            raise PreprocessorError(
                "Directives must appear at the top of the file.", location=elm.location
            )
        self.visit(elm.directive)

    def visit_CodeElementImport(self, elm: CodeElementImport):
        pass

    def visit_CodeElementAllocLocals(self, elm: CodeElementAllocLocals):
        if self.current_scope not in self.function_metadata:
            raise PreprocessorError(
                "alloc_locals cannot be used outside of a function.", location=elm.location
            )
        # Check that ap did not change from the beginning of the function.
        if not isinstance(self.flow_tracking.data, FlowTrackingDataActual) or (
            self.flow_tracking.data.ap_tracking
            != self.function_metadata[self.current_scope].initial_ap_data
        ):
            raise PreprocessorError(
                "alloc_locals must be used before any instruction that changes the ap register.",
                location=elm.location,
            )

    def visit_CodeElementInstruction(self, elm: CodeElementInstruction):
        current_flow_tracking_data = self.flow_tracking.get()
        preprocessed_instruction = PreprocessedInstruction(
            instruction=self.visit(elm.instruction),
            accessible_scopes=self.accessible_scopes.copy(),
            hints=self.next_instruction_hints,
            flow_tracking_data=current_flow_tracking_data,
        )
        self._clear_next_hints()
        self.current_pc += self.get_instruction_size(
            preprocessed_instruction.instruction, allow_auto_deduction=True
        )
        self.instructions.append(preprocessed_instruction)

    def visit_CodeElementConst(self, elm: CodeElementConst):
        if self.inside_a_struct():
            # Was already handled by the struct collector.
            return

        name = self.current_scope + elm.identifier.name
        val = self.simplify_expr_as_felt(elm.expr)
        if not isinstance(val, ExprConst):
            raise PreprocessorError("Expected a constant expression.", location=elm.expr.location)
        self.add_name_definition(
            name, ConstDefinition(value=val.val), location=elm.identifier.location
        )

        if self.auxiliary_info is not None:
            self.auxiliary_info.add_const(name, val.val)

    def visit_CodeElementMember(self, elm: CodeElementMember):
        self.check_no_hints("Hints before member definitions are not allowed.")

        if self.inside_a_struct():
            # Was already handled by the struct collector.
            return

        raise PreprocessorError(
            "The member keyword may only be used inside a struct.",
            location=elm.typed_identifier.location,
        )

    def visit_CodeElementReference(self, elm: CodeElementReference):
        name = self.current_scope + elm.typed_identifier.identifier.name
        val, val_type = self.simplify_expr(elm.expr)

        assert_no_modifier(elm.typed_identifier)
        self.check_reference_expression(val)

        if elm.typed_identifier.expr_type is not None:
            dst_type = self.resolve_type(elm.typed_identifier.expr_type)
        else:
            # Copy the type from the value.
            dst_type = val_type
        if not check_cast(
            src_type=val_type,
            dest_type=dst_type,
            identifier_manager=self.identifiers,
            cast_type=CastType.ASSIGN,
            location=dst_type.location,
        ):
            raise PreprocessorError(
                f"Cannot assign an expression of type '{val_type.format()}' "
                f"to a reference of type '{dst_type.format()}'.",
                location=dst_type.location,
            )

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
                    location=addr.location,
                ),
                location=location,
            )
        else:
            ref_expr = ExprCast(
                expr=val, dest_type=dst_type, cast_type=CastType.FORCED, location=location
            )

        self.add_reference(
            name=name,
            value=ref_expr,
            cairo_type=dst_type,
            location=elm.typed_identifier.location,
        )

        if self.auxiliary_info is not None:
            self.auxiliary_info.add_reference(name, elm.expr, elm.typed_identifier.location)

    def visit_CodeElementLocalVariable(self, elm: CodeElementLocalVariable):
        raise PreprocessorError(
            "Local variables are not supported outside of functions.", location=elm.location
        )

    def get_expr_for_new_operator(self, new_expr: ExprNewOperator) -> Expression:
        """
        Given a new expression, pushes the inner expression onto the stack, calls get_ap
        and returns a pointer to the inner expression on the stack.
        """
        location = new_expr.location

        # Push new_expr.expr onto the stack.
        inner_expr, inner_type = self.simplify_expr(new_expr.expr)
        inner_exprs = self.simplified_expr_to_felt_expr_list(expr=inner_expr, expr_type=inner_type)
        self.push_compound_expressions(compound_expressions=inner_exprs, location=location)

        # Call get_ap().
        code_elm_call = CodeElementInstruction(
            instruction=InstructionAst(
                body=CallLabelInstruction(
                    label=ExprIdentifier(
                        name="starkware.cairo.lang.compiler.lib.registers.get_ap", location=location
                    ),
                    location=location,
                    fully_qualified_label=True,
                ),
                inc_ap=False,
                location=location,
            )
        )
        self.visit(code_elm_call)

        inner_expr_size = self.get_size(cairo_type=inner_type)

        # Create the expression that computes '[ap - 1] - inner_expr_size'.
        # Note that here [ap - 1] is the value returned by get_ap().
        current_ap_expr = create_simple_ref_expr(
            reg=Register.AP,
            offset=-1,
            cairo_type=TypeFelt(location=location),
            location=location,
        )

        expr: Expression = ExprOperator(
            a=current_ap_expr,
            op="-",
            b=ExprConst(inner_expr_size, location=location),
            location=location,
        )

        if new_expr.is_typed:
            # Cast pointer_expr to the correct type.
            expr = ExprCast(
                expr=expr,
                dest_type=TypePointer(pointee=inner_type, location=location),
                location=location,
            )
        return expr

    def visit_CodeElementTemporaryVariable(self, elm: CodeElementTemporaryVariable):
        assert_no_modifier(elm.typed_identifier)

        if self.auxiliary_info is not None:
            self.auxiliary_info.start_temp_var(
                self.current_scope + elm.typed_identifier.identifier.name,
                elm.expr,
                elm.typed_identifier.location,
            )

        if elm.expr is None or isinstance(elm.expr, ExprHint):
            # If this is an uninitialized tempvar, only increment ap.
            dest_type = self.resolve_type(elm.typed_identifier.get_type())
            src_size = self.get_size(dest_type)

            if isinstance(elm.expr, ExprHint):
                if not isinstance(dest_type, (TypeFelt, TypePointer)):
                    raise PreprocessorError(
                        "Hint tempvars must be of type felt or a pointer.",
                        location=elm.expr.location,
                    )
                self.visit(
                    CodeElementHint(
                        hint=ExprHint(
                            hint_code=f"memory[ap] = to_felt_or_relocatable({elm.expr.hint_code})",
                            n_prefix_newlines=0,
                            location=elm.location,
                        ),
                        location=elm.location,
                    )
                )

            self.visit(
                CodeElementInstruction(
                    instruction=InstructionAst(
                        body=AddApInstruction(
                            expr=ExprConst(val=src_size, location=elm.location),
                            location=elm.location,
                        ),
                        inc_ap=False,
                        location=elm.location,
                    ),
                ),
            )
        else:
            if isinstance(elm.expr, ExprNewOperator):
                expr = self.get_expr_for_new_operator(elm.expr)
            else:
                expr = elm.expr

            expr, src_type = self.simplify_expr(expr)
            src_size = self.get_size(src_type)

            if elm.typed_identifier.expr_type is None:
                dest_type = src_type
            else:
                dest_type = self.resolve_type(elm.typed_identifier.expr_type)
                if not check_cast(
                    src_type=src_type,
                    dest_type=dest_type,
                    identifier_manager=self.identifiers,
                    cast_type=CastType.ASSIGN,
                    location=elm.location,
                ):
                    raise PreprocessorError(
                        f"Cannot assign an expression of type '{src_type.format()}' "
                        f"to a temporary variable of type '{dest_type.format()}'.",
                        location=dest_type.location,
                    )

                dest_size = self.get_size(dest_type)
                assert src_size == dest_size, "Expecting src and dest types to have the same size."

            src_exprs = self.simplified_expr_to_felt_expr_list(expr=expr, expr_type=src_type)
            self.push_compound_expressions(compound_expressions=src_exprs, location=elm.location)

        self.add_simple_reference(
            name=self.current_scope + elm.typed_identifier.name,
            reg=Register.AP,
            cairo_type=dest_type,
            offset=-src_size,
            location=elm.typed_identifier.identifier.location,
        )

        if self.auxiliary_info is not None:
            self.auxiliary_info.finish_temp_var()

    def visit_CodeElementCompoundAssertEq(self, instruction: CodeElementCompoundAssertEq):
        expr_a, expr_type_a = self.simplify_expr(instruction.a)
        expr_b, expr_type_b = self.simplify_expr(instruction.b)
        if expr_type_a != expr_type_b:
            raise PreprocessorError(
                f"Cannot compare '{expr_type_a.format()}' and '{expr_type_b.format()}'.",
                location=instruction.location,
            )

        if self.auxiliary_info is not None:
            self.auxiliary_info.start_compound_assert_eq(lhs=instruction.a, rhs=instruction.b)

        dst_exprs = self.simplified_expr_to_felt_expr_list(expr=expr_a, expr_type=expr_type_a)
        src_exprs = self.simplified_expr_to_felt_expr_list(expr=expr_b, expr_type=expr_type_b)
        original_ap_tracking = self.flow_tracking.get_ap_tracking()

        for dst, src in safe_zip(dst_exprs, src_exprs):
            ap_diff = self.flow_tracking.get_ap_tracking() - original_ap_tracking
            dst = self.simplifier.visit(translate_ap(dst, ap_diff))
            src = self.simplifier.visit(translate_ap(src, ap_diff))
            (expr_a, expr_b) = process_compound_assert(dst, src, self._compound_expression_context)
            assert_eq = CodeElementInstruction(
                instruction=InstructionAst(
                    body=AssertEqInstruction(a=expr_a, b=expr_b, location=instruction.location),
                    inc_ap=False,
                    location=instruction.location,
                )
            )

            self.visit(assert_eq)

        if self.auxiliary_info is not None:
            self.auxiliary_info.finish_compound_assert_eq()

    def visit_CodeElementStaticAssert(self, elm: CodeElementStaticAssert):
        a = self.simplify_expr_as_felt(elm.a)
        b = self.simplify_expr_as_felt(elm.b)
        if a != b:
            raise PreprocessorError(
                f"Static assert failed: {a.format()} != {b.format()}.", location=elm.location
            )

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
            if not isinstance(expr.addr, ExprOperator) or expr.addr.op != "+":
                return None
            if not isinstance(expr.addr.a, ExprReg) or expr.addr.a.reg is not Register.AP:
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
        self, exprs: List[ExprAssignment], struct_name: ScopedName, location: Optional[Location]
    ) -> List[Expression]:
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
                f"Expected exactly {n_members} expressions, got {len(exprs)}.", location=location
            )

        passed_args = list(struct_def.members.items())
        reached_named = False
        compound_expressions = []
        for (member_name, member_def), expr_assignment in zip(passed_args, exprs):
            if expr_assignment.identifier is None:
                # Make sure all named args are after positional args.
                if reached_named:
                    raise PreprocessorError(
                        "Positional arguments must not appear after named arguments.",
                        location=expr_assignment.location,
                    )
            else:
                reached_named = True
                name = expr_assignment.identifier.name
                if name != member_name:
                    raise PreprocessorError(
                        f"Expected named arg '{member_name}' found '{name}'.",
                        location=expr_assignment.identifier.location,
                    )

            felt_expr_list = self.simplify_expr_to_felt_expr_list(
                expr_assignment.expr, member_def.cairo_type
            )
            compound_expressions.extend(felt_expr_list)

        return compound_expressions

    def process_implicit_argument_binding(
        self,
        implicit_args: List[ExprAssignment],
        implicit_args_struct_name: ScopedName,
        location: Optional[Location],
    ) -> List[Optional[ExprIdentifier]]:
        """
        Processes the implicit argument bindings. Returns a list whose size is the number of
        implicit arguments of the called function, with the binding variable for each argument
        if exists, and None otherwise.
        For example, given "func foo{x, y, z}", and the call "foo{y=w}()" the returned list
        will be [None, w, None].
        """
        implicit_args_struct = self.get_struct_definition(
            name=implicit_args_struct_name, location=location
        )

        # A list of (arg_name, binding).
        processed_implicit_args: List[Tuple[ExprIdentifier, ExprIdentifier]] = []
        for arg in implicit_args:
            if arg.identifier is None:
                raise PreprocessorError(
                    "Implicit argument binding must be of the form: arg_name=var.",
                    location=arg.location,
                )

            if not isinstance(arg.expr, ExprIdentifier) or "." in arg.expr.name:
                raise PreprocessorError(
                    "Implicit argument binding must be an identifier.", location=arg.expr.location
                )
            processed_implicit_args.append((arg.identifier, arg.expr))

        result: List[Optional[ExprIdentifier]] = []

        for member_name in implicit_args_struct.members.keys():
            if (
                len(processed_implicit_args) == 0
                or processed_implicit_args[0][0].name != member_name
            ):
                result.append(None)
                continue

            result.append(processed_implicit_args[0][1])
            processed_implicit_args.pop(0)

        # Make sure all implicit argument bindings were processed.
        if len(processed_implicit_args) > 0:
            raise PreprocessorError(
                f"Unexpected implicit argument binding: {processed_implicit_args[0][0].name}.",
                location=processed_implicit_args[0][0].location,
            )

        return result

    def process_implicit_arguments(
        self,
        implicit_args: Optional[List[Optional[ExprIdentifier]]],
        implicit_args_struct_name: ScopedName,
        location: Optional[Location],
    ) -> List[Expression]:
        """
        Returns the expressions for the implicit arguments.
        Used both for function call and a return instruction.

        implicit_args - list of implicit argument bindings.
        implicit_args_struct_name - ScopedName of the implicit argument struct.
        location - location to attach to errors if no finer location is relevant.
        """
        implicit_args_struct = self.get_struct_definition(
            name=implicit_args_struct_name, location=location
        )

        if implicit_args is None:
            implicit_args = [None] * len(implicit_args_struct.members)

        compound_expressions = []
        for (member_name, member_def), implicit_arg in safe_zip(
            implicit_args_struct.members.items(), implicit_args
        ):
            expr: Expression
            if implicit_arg is not None:
                # Explicit binding is given, use it.
                expr = implicit_arg
            else:
                # No explicit binding is given, use the name of the implicit argument.
                expr = add_parent_location(
                    expr=ExprIdentifier(name=member_name, location=member_def.location),
                    new_parent_location=location,
                    message=f"While trying to retrieve the implicit argument '{member_name}' in:",
                )

            felt_expr_list = self.simplify_expr_to_felt_expr_list(expr, member_def.cairo_type)
            compound_expressions.extend(felt_expr_list)

        return compound_expressions

    def push_compound_expressions(
        self, compound_expressions: List[Expression], location: Optional[Location]
    ):
        """
        Generates instructions to push all the given expressions onto the stack.
        In more detail: translates a list of expressions to a set of instructions evaluating the
        expressions and storing the values to memory, starting from address 'ap'.

        compound_expressions - list of Expression objects to process.
        location - location to attach to errors if no finer location is relevant.
        """
        # Generate instructions.
        simple_exprs = process_compound_expressions(
            compound_expressions,
            SimplicityLevel.OPERATION,
            context=self._compound_expression_context,
        )

        assert len(simple_exprs) == len(compound_expressions)
        simple_exprs = self.optimize_expressions_for_push(simple_exprs)
        compound_expressions = compound_expressions[-len(simple_exprs) :]

        for i, (simple_expr, original_expr) in enumerate(zip(simple_exprs, compound_expressions)):
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
                )
            )
            self.visit(code_elm_inst)

    def push_arguments(
        self,
        arguments: List[ExprAssignment],
        implicit_args: Optional[List[Optional[ExprIdentifier]]],
        struct_name: ScopedName,
        implicit_args_struct_name: ScopedName,
        location: Optional[Location],
    ):
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
            exprs=arguments, struct_name=struct_name, location=location
        )

        implicit_args_expressions = self.process_implicit_arguments(
            implicit_args=implicit_args,
            implicit_args_struct_name=implicit_args_struct_name,
            location=location,
        )

        self.push_compound_expressions(
            compound_expressions=implicit_args_expressions + args_expressions,
            location=location,
        )

    def visit_CodeElementReturn(self, elm: CodeElementReturn):
        if self.current_scope not in self.function_metadata:
            raise PreprocessorError(
                f"return cannot be used outside of a function.", location=elm.location
            )

        if self.auxiliary_info is not None:
            self.auxiliary_info.start_return()

        self.push_arguments(
            arguments=cast(List[ExprAssignment], elm.exprs),
            implicit_args=None,
            struct_name=CodeElementFunction.RETURN_SCOPE,
            implicit_args_struct_name=CodeElementFunction.IMPLICIT_ARGUMENT_SCOPE,
            location=elm.location,
        )
        code_elm_ret = CodeElementInstruction(
            instruction=InstructionAst(body=RetInstruction(), inc_ap=False, location=elm.location)
        )
        self.visit(code_elm_ret)

        if self.auxiliary_info is not None:
            self.auxiliary_info.finish_return(exprs=elm.exprs)

    def check_tail_call_cast(
        self,
        src_struct: StructDefinition,
        dest_struct: StructDefinition,
        location: Optional[Location],
    ) -> bool:
        """
        Checks if src_struct can be converted to dest_struct in the context of a tail call.
        """
        src_members = src_struct.members
        dest_members = dest_struct.members

        if len(src_members) != len(dest_members):
            return False

        for src_member, dest_member in zip(src_members.values(), dest_members.values()):
            if not check_cast(
                src_type=src_member.cairo_type,
                dest_type=dest_member.cairo_type,
                identifier_manager=self.identifiers,
                cast_type=CastType.ASSIGN,
                location=location,
            ):
                return False

        return True

    def visit_CodeElementTailCall(self, elm: CodeElementTailCall):
        if self.current_scope not in self.function_metadata:
            raise PreprocessorError(
                f"return cannot be used outside of a function.", location=elm.location
            )

        if self.auxiliary_info is not None:
            self.auxiliary_info.start_tail_call(args=[a.expr for a in elm.func_call.arguments.args])

        # Visit function call before type check to get better error message.
        self.visit(CodeElementFuncCall(func_call=elm.func_call))

        func_name = elm.func_call.func_ident.name

        src_struct = self.get_struct_definition(
            name=ScopedName.from_string(func_name) + CodeElementFunction.RETURN_SCOPE,
            location=elm.location,
        )

        dest_struct = get_struct_definition(
            struct_name=self.current_scope + CodeElementFunction.RETURN_SCOPE,
            identifier_manager=self.identifiers,
        )

        if not self.check_tail_call_cast(
            src_struct=src_struct, dest_struct=dest_struct, location=elm.location
        ):
            raise PreprocessorError(
                f"""\
Cannot convert the return type of {func_name} to the return type of {self.current_scope[-1:]}.""",
                location=elm.location,
            )

        src_struct = self.get_struct_definition(
            name=ScopedName.from_string(func_name) + CodeElementFunction.IMPLICIT_ARGUMENT_SCOPE,
            location=elm.location,
        )

        dest_struct = get_struct_definition(
            struct_name=self.current_scope + CodeElementFunction.IMPLICIT_ARGUMENT_SCOPE,
            identifier_manager=self.identifiers,
        )

        if list(src_struct.members.items()) != list(dest_struct.members.items()):
            notes = (
                []
                if src_struct.location is None or dest_struct.location is None
                else [
                    f"The implicit arguments of '{func_name}' were defined here:\n"
                    + src_struct.location.to_string_with_content(),
                    f"The implicit arguments of '{self.current_scope[-1:]}' were defined here:\n"
                    + dest_struct.location.to_string_with_content(),
                ]
            )

            raise PreprocessorError(
                f"""\
Cannot convert the implicit arguments of {func_name} to the implicit arguments of \
{self.current_scope[-1:]}.""",
                location=elm.location,
                notes=notes,
            )

        self.visit(
            CodeElementInstruction(
                instruction=InstructionAst(
                    body=RetInstruction(), inc_ap=False, location=elm.location
                )
            )
        )

        if self.auxiliary_info is not None:
            self.auxiliary_info.finish_tail_call()

    def add_implicit_return_references(
        self,
        implicit_args: List[Optional[ExprIdentifier]],
        called_function: ScopedName,
        location: Optional[Location],
    ):
        """
        Adds references that allow accessing the implicit return values of a called function.
        """
        implicit_args_struct = self.get_struct_definition(
            name=called_function + CodeElementFunction.IMPLICIT_ARGUMENT_SCOPE, location=location
        )
        return_size = self.get_size_by_type_name(
            struct_name=called_function + CodeElementFunction.RETURN_SCOPE, location=location
        )

        assert len(implicit_args_struct.members) == len(implicit_args)
        for (name, member_def), implicit_arg in zip(
            implicit_args_struct.members.items(), implicit_args
        ):
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
                        message=f"While trying to update the implicit return value '{name}' in:",
                    )

            self.add_simple_reference(
                name=self.current_scope + binding_var,
                reg=Register.AP,
                cairo_type=member_def.cairo_type,
                offset=member_def.offset - (return_size + implicit_args_struct.size),
                location=implicit_arg_location,
            )

            if (
                implicit_arg is None
                and self.reference_states.get(self.current_scope + name)
                is not ReferenceState.ALLOW_IMPLICIT
            ):
                raise PreprocessorError(
                    f"'{name}' cannot be used as an implicit return value. "
                    "Consider using a 'with' statement.",
                    location=implicit_arg_location,
                )

    def visit_CodeElementFuncCall(self, elm: CodeElementFuncCall):
        # Make sure the identifier for the called function refers to a function.
        called_function = ScopedName.from_string(elm.func_call.func_ident.name)
        try:
            res = self.identifiers.search(
                accessible_scopes=self.accessible_scopes, name=called_function
            )
            res.assert_fully_parsed()
        except IdentifierError as exc:
            raise PreprocessorError(str(exc), location=elm.func_call.func_ident.location)
        called_function_def = res.identifier_definition
        called_function_def_type = (
            called_function_def.identifier_type
            if isinstance(called_function_def, FutureIdentifierDefinition)
            else type(called_function_def)
        )
        if called_function_def_type is not FunctionDefinition:
            raise PreprocessorError(
                f"Expected {called_function} to be a function name. "
                f"Found: {called_function_def.TYPE}.",
                location=elm.func_call.func_ident.location,
            )

        implicit_args_struct_name = called_function + CodeElementFunction.IMPLICIT_ARGUMENT_SCOPE
        implicit_args = (
            cast(List[ExprAssignment], elm.func_call.implicit_arguments.args)
            if elm.func_call.implicit_arguments is not None
            else []
        )
        processed_implicit_args = self.process_implicit_argument_binding(
            implicit_args=implicit_args,
            implicit_args_struct_name=implicit_args_struct_name,
            location=elm.func_call.location,
        )

        if self.auxiliary_info is not None:
            self.auxiliary_info.start_func_call(
                name=str(res.canonical_name),
                args=[arg.expr for arg in elm.func_call.arguments.args],
            )

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
                location=elm.func_call.location,
            )
        )
        self.visit(code_elm_call)

        if self.auxiliary_info is not None:
            self.auxiliary_info.finish_func_call()

        self.add_implicit_return_references(
            implicit_args=processed_implicit_args,
            called_function=called_function,
            location=elm.func_call.location,
        )

    def add_simple_reference(
        self,
        name: ScopedName,
        reg: Register,
        cairo_type: CairoType,
        offset: int,
        location: Optional[Location],
    ):
        """
        Creates a simple reference with the given name to "[reg + offset]".
        """

        ref_expr = create_simple_ref_expr(
            reg=reg, offset=offset, cairo_type=cairo_type, location=location
        )
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
                )
            )
            func_ident = None
            if isinstance(elm.func_call.call_inst, CallLabelInstruction):
                func_ident = elm.func_call.call_inst.label
                assert (
                    not elm.func_call.call_inst.fully_qualified_label
                ), "Expecting a relative label."
        elif isinstance(elm.func_call, RvalueFuncCall):
            # If the function name is the name of a struct, replace the
            # CodeElementReturnValueReference with a regular reference.
            if (
                self.try_get_struct_definition(
                    ScopedName.from_string(elm.func_call.func_ident.name)
                )
                is not None
            ):
                return self.visit(
                    CodeElementReference(
                        typed_identifier=elm.typed_identifier,
                        expr=ExprFuncCall(rvalue=elm.func_call, location=elm.func_call.location),
                    )
                )
            call_elm = CodeElementFuncCall(func_call=elm.func_call)
            func_ident = elm.func_call.func_ident
        else:
            raise NotImplementedError(f"Unsupported func_call={elm.func_call}.")

        expr_type = elm.typed_identifier.expr_type
        if expr_type is None:
            if func_ident is not None:
                expr_type = TypeStruct(
                    scope=ScopedName.from_string(func_ident.name)
                    + CodeElementFunction.RETURN_SCOPE,
                    is_fully_resolved=False,
                    location=func_ident.location,
                )
            else:
                expr_type = TypeFelt(location=elm.typed_identifier.location)

        # Visit call_elm to advance pc.
        self.visit(call_elm)

        if self.auxiliary_info is not None:
            self.auxiliary_info.add_func_ret_vars([elm.typed_identifier.name])

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
                f"Cannot unpack {elm.rvalue.format()}.", location=elm.rvalue.location
            )

        func_ident = elm.rvalue.func_ident
        return_type = self.resolve_type(
            TypeStruct(
                scope=ScopedName.from_string(func_ident.name) + CodeElementFunction.RETURN_SCOPE,
                is_fully_resolved=False,
                location=func_ident.location,
            )
        )
        assert isinstance(return_type, TypeStruct), f"Unexpected type {return_type}."
        struct_def = get_struct_definition(return_type.scope, identifier_manager=self.identifiers)

        expected_len = len(struct_def.members)
        unpacking_identifiers = elm.unpacking_list.identifiers
        if len(unpacking_identifiers) != expected_len:
            suffix = "s" if expected_len > 1 else ""
            raise PreprocessorError(
                f"""\
Expected {expected_len} unpacking identifier{suffix}, found {len(unpacking_identifiers)}.""",
                location=elm.unpacking_list.location,
            )

        return struct_def

    def visit_CodeElementUnpackBinding(self, elm: CodeElementUnpackBinding):
        struct_def = self.get_unpacking_struct_definition(elm)

        assert isinstance(
            elm.rvalue, RvalueFuncCall
        ), f"Invalid type for elm.rvalue: {type(elm.rvalue).__name__}."
        self.visit(CodeElementFuncCall(func_call=elm.rvalue))

        for typed_identifier, member_def in zip(
            elm.unpacking_list.identifiers, struct_def.members.values()
        ):
            excluded = []
            if self.current_scope in self.function_metadata:
                excluded = ["local"]
            # Forbid locals outside of functions.
            assert_no_modifier(typed_identifier, excluded=excluded)

            if typed_identifier.name == "_":
                continue

            if typed_identifier.expr_type is not None:
                cairo_type = self.resolve_type(typed_identifier.get_type())
            else:
                cairo_type = member_def.cairo_type

            if not check_cast(
                src_type=member_def.cairo_type,
                dest_type=cairo_type,
                identifier_manager=self.identifiers,
                cast_type=CastType.UNPACKING,
                location=typed_identifier.location,
            ):
                raise PreprocessorError(
                    f"""\
Expected expression of type '{member_def.cairo_type.format()}', got '{cairo_type.format()}'.""",
                    location=typed_identifier.location,
                )

            self.add_simple_reference(
                name=self.current_scope + typed_identifier.identifier.name,
                reg=Register.AP,
                cairo_type=cairo_type,
                offset=member_def.offset - struct_def.size,
                location=typed_identifier.location,
            )

            if self.auxiliary_info is not None:
                self.auxiliary_info.add_func_ret_vars([typed_identifier.identifier.name])

    def add_label(self, identifier: ExprIdentifier):
        name = self.current_scope + identifier.name
        self.flow_tracking.converge_with_label(name)
        self.add_name_definition(
            name, LabelDefinition(pc=self.current_pc), location=identifier.location  # type: ignore
        )

    def add_reference(
        self,
        name: ScopedName,
        value: Expression,
        cairo_type: CairoType,
        location: Optional[Location],
        require_future_definition=True,
    ):
        if name.path[-1] == "_":
            raise PreprocessorError("Reference name cannot be '_'.", location=location)

        reference = Reference(
            pc=self.current_pc,
            value=value,
            ap_tracking_data=self.flow_tracking.get_ap_tracking(),
            locations=[] if location is None else [location],
            definition_code_element=self.current_code_element,
        )

        self.flow_tracking.add_reference(name, reference)
        existing_definition = self.identifiers.get_by_full_name(name)
        if isinstance(existing_definition, ReferenceDefinition):
            # Rebind reference.
            if existing_definition.cairo_type != cairo_type:
                raise PreprocessorError(
                    "Reference rebinding must preserve the reference type. "
                    f"Previous type: '{existing_definition.cairo_type.format()}', "
                    f"new type: '{cairo_type.format()}'.",
                    location=location,
                )
            existing_definition.references.append(reference)
        else:
            self.add_name_definition(
                name,
                ReferenceDefinition(full_name=name, cairo_type=cairo_type, references=[reference]),
                location=location,
                require_future_definition=require_future_definition,
            )

    def add_function(self, elm: CodeElementFunction):
        name = self.current_scope + elm.name
        self.add_name_definition(
            name,
            FunctionDefinition(  # type: ignore
                pc=self.current_pc,
                decorators=[identifier.name for identifier in elm.decorators],
            ),
            location=elm.identifier.location,
        )

        self.function_metadata[name] = FunctionMetadata(
            initial_ap_data=self.flow_tracking.get_ap_tracking()
        )

    def visit_CodeElementLabel(self, elm: CodeElementLabel):
        self.check_no_hints("Hints before labels are not allowed.")
        self.add_label(elm.identifier)

        if self.auxiliary_info is not None:
            _, label_full_name = self.get_label(
                label_name=elm.identifier.name,
                fully_qualified_label=False,
                location=elm.identifier.location,
            )
            self.auxiliary_info.record_label(label_full_name=label_full_name)

    def visit_CodeElementHint(self, elm: CodeElementHint):
        self._add_next_hint(hint=elm)

    def visit_CodeElementEmptyLine(self, elm: CodeElementEmptyLine):
        # Ignore empty lines.
        pass

    # Instructions.
    def visit_InstructionAst(self, instruction: InstructionAst):
        flows, instruction_body = self.visit(instruction.body)
        res = InstructionAst(
            body=instruction_body, inc_ap=instruction.inc_ap, location=instruction.location
        )
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
        if self.auxiliary_info is not None:
            self.auxiliary_info.add_assert_eq(lhs=instruction.a, rhs=instruction.b)
        return InstructionFlows(next_inst=RegChangeKnown(0)), AssertEqInstruction(
            a=self.simplify_expr_as_felt(instruction.a),
            b=self.simplify_expr_as_felt(instruction.b),
            location=instruction.location,
        )

    def visit_JumpInstruction(self, instruction: JumpInstruction):
        self.revoke_function_ap_change()
        return InstructionFlows(), JumpInstruction(
            val=self.simplify_expr_as_felt(instruction.val),
            relative=instruction.relative,
            location=instruction.location,
        )

    def visit_JumpToLabelInstruction(self, instruction: JumpToLabelInstruction):
        label_name = instruction.label.name
        label_pc, label_full_name = self.get_label(
            label_name=label_name,
            fully_qualified_label=False,
            location=instruction.label.location,
        )

        # Process instruction.
        res_instruction: InstructionBody
        if label_pc is None:
            condition = instruction.condition
            if condition is not None:
                condition = self.simplify_expr_as_felt(condition)
            res_instruction = dataclasses.replace(instruction, condition=condition)
            if self.auxiliary_info is not None:
                self.auxiliary_info.record_jump_to_labeled_instruction(
                    label_name=label_full_name,
                    condition=condition,
                    current_pc=self.current_pc,
                    pc_dest=None,
                )
        else:
            jump_offset = ExprConst(
                val=label_pc - self.current_pc, location=instruction.label.location
            )
            if instruction.condition is None:
                self.current_instruction_ended_flow = True
                res_instruction = JumpInstruction(
                    val=jump_offset, relative=True, location=instruction.location
                )
            else:
                res_instruction = JnzInstruction(
                    jump_offset=jump_offset,
                    condition=self.simplify_expr_as_felt(instruction.condition),
                    location=instruction.location,
                )

            if self.auxiliary_info is not None:
                self.auxiliary_info.record_jump_to_labeled_instruction(
                    label_name=label_full_name,
                    condition=self.simplify_expr_as_felt(instruction.condition)
                    if instruction.condition is not None
                    else None,
                    current_pc=self.current_pc,
                    pc_dest=label_pc,
                )

            if label_pc <= self.current_pc:
                self.revoke_function_ap_change()

        flow_next = None if instruction.condition is None else RegChangeKnown(0)
        if label_full_name is None:
            raise PreprocessorError(
                f"Unknown label {label_name}.", location=instruction.label.location
            )
        jumps: Dict[ScopedName, RegChange] = {label_full_name: RegChangeKnown(0)}
        return InstructionFlows(next_inst=flow_next, jumps=jumps), res_instruction

    def visit_JnzInstruction(self, instruction: JnzInstruction):
        self.revoke_function_ap_change()
        return InstructionFlows(next_inst=RegChangeKnown(0)), JnzInstruction(
            jump_offset=self.simplify_expr_as_felt(instruction.jump_offset),
            condition=self.simplify_expr_as_felt(instruction.condition),
            location=instruction.location,
        )

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
            location=instruction.location,
        )

    def visit_CallLabelInstruction(self, instruction: CallLabelInstruction):
        label_name = instruction.label.name
        label_pc, full_label_scope = self.get_label(
            label_name=label_name,
            fully_qualified_label=instruction.fully_qualified_label,
            location=instruction.label.location,
        )

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

        jump_offset = ExprConst(val=label_pc - self.current_pc, location=instruction.label.location)
        return InstructionFlows(next_inst=ap_change), CallInstruction(
            val=jump_offset, relative=True, location=instruction.location
        )

    def visit_AddApInstruction(self, instruction: AddApInstruction):
        expr = self.simplify_expr_as_felt(instruction.expr)

        if self.auxiliary_info is not None:
            self.auxiliary_info.add_add_ap(expr)

        return InstructionFlows(next_inst=RegChange.from_expr(expr)), AddApInstruction(
            expr=expr, location=instruction.location
        )

    def visit_DefineWordInstruction(self, instruction: DefineWordInstruction):
        return InstructionFlows(), DefineWordInstruction(
            expr=self.simplify_expr_as_felt(instruction.expr),
            location=instruction.location,
        )

    def visit_RetInstruction(self, instruction: RetInstruction):
        if self.current_scope in self.function_metadata:
            metadata = self.function_metadata[self.current_scope]
            ap_change = self.flow_tracking.get_ap_tracking() - metadata.initial_ap_data
            metadata.total_ap_change &= ap_change
        return InstructionFlows(), instruction

    # Directives.
    def visit_BuiltinsDirective(self, directive: BuiltinsDirective):
        pass

    def visit_LangDirective(self, directive: LangDirective):
        raise PreprocessorError(
            f"Unsupported %lang directive. Are you using the correct compiler?",
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
            resolve_type_callback=self.resolve_type,
            get_struct_members_callback=self.get_struct_members,
        )
        expr, expr_type = simplify_type_system(expr, identifiers=self.identifiers)
        return self.simplifier.visit(expr), self.resolve_type(expr_type)

    def simplify_expr_as_felt(self, expr) -> Expression:
        """
        Same as simplify_expr(), except that it verifies that the type of the result is convertible
        to felt (felt or pointer) and it does not return the type.
        """
        expr, expr_type = self.simplify_expr(expr)
        if not isinstance(expr_type, (TypeFelt, TypePointer, TypeCodeoffset)):
            raise PreprocessorError(
                f"Expected a 'felt' or a pointer type. Got: '{expr_type.format()}'.",
                location=expr.location,
            )
        return expr

    def simplify_expr_to_felt_expr_list(
        self, expr: Expression, expected_type: CairoType
    ) -> List[Expression]:
        """
        Takes a possibly typed expression, checks that it can be assigned to expected_type
        and splits it into a list of typeless expressions that can be passed to
        process_compound_expressions.
        """

        # Keep the location of the original expression for error handling.
        location = expr.location
        expr, expr_type = self.simplify_expr(expr)

        if not check_cast(
            src_type=expr_type,
            dest_type=expected_type,
            identifier_manager=self.identifiers,
            cast_type=CastType.ASSIGN,
            location=location,
        ):
            raise PreprocessorError(
                f"""\
Expected expression of type '{expected_type.format()}', got '{expr_type.format()}'.""",
                location=location,
            )

        return self.simplified_expr_to_felt_expr_list(expr=expr, expr_type=expr_type)

    def simplified_expr_to_felt_expr_list(
        self, expr: Expression, expr_type: CairoType
    ) -> List[Expression]:
        """
        Takes a simplified expression and its type and splits it into a list of typeless expressions
        that can be passed to process_compound_expressions.
        """

        if isinstance(expr_type, (TypeFelt, TypePointer, TypeCodeoffset)):
            return [expr]

        # Get the list of member types.
        if isinstance(expr_type, TypeTuple):
            member_types = expr_type.types
        elif isinstance(expr_type, TypeStruct):
            struct_definition = get_struct_definition(
                expr_type.scope, identifier_manager=self.identifiers
            )
            member_types = [
                member_def.cairo_type for member_def in struct_definition.members.values()
            ]
        else:
            raise PreprocessorError(f"Unexpected type {expr_type}.", location=expr_type.location)

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
                                op="+",
                                b=ExprConst(offset, location=location),
                                location=location,
                            ),
                            location=location,
                        )
                    )
                )

                offset += self.get_size(member_type)

        expr_list = []
        for member_expr, member_type in zip(member_exprs, member_types):
            expr_list.extend(
                self.simplified_expr_to_felt_expr_list(expr=member_expr, expr_type=member_type)
            )
        return expr_list

    def get_label(
        self, label_name: str, fully_qualified_label: bool, location: Optional[Location]
    ) -> Tuple[Optional[int], Optional[ScopedName]]:
        """
        Returns a pair (pc, canonical_name) for the given label, or (None, None) if this label
        hasn't been processed yet.

        fully_qualified_label indicates that 'label_name' is a fully qualified identifier,
        rather than a relative one.
        """
        try:
            scoped_name = ScopedName.from_string(label_name)
            if fully_qualified_label:
                search_result = self.identifiers.get(name=scoped_name)
            else:
                search_result = self.identifiers.search(
                    accessible_scopes=self.accessible_scopes,
                    name=scoped_name,
                )
            search_result.assert_fully_parsed()
        except IdentifierError as exc:
            raise PreprocessorError(str(exc), location=location)

        if isinstance(search_result.identifier_definition, FutureIdentifierDefinition):
            return None, search_result.canonical_name

        if not isinstance(search_result.identifier_definition, LabelDefinition):
            raise PreprocessorError(
                f"Expected a label name. Identifier '{label_name}' is of type "
                f"{search_result.identifier_definition.TYPE}.",
                location=location,
            )
        return search_result.identifier_definition.pc, search_result.canonical_name

    def get_variable(self, var: ExprIdentifier) -> Union[int, Expression]:
        identifier_definition = self.search_identifier(var.name, var.location)
        # Check that identifier_definition is not None for mypy.
        assert identifier_definition is not None

        if isinstance(identifier_definition, FutureIdentifierDefinition):
            if identifier_definition.identifier_type in [LabelDefinition, FunctionDefinition]:
                # Allow future label assignment.
                return ExprFutureLabel(identifier=var, is_typed=True, location=var.location)
            raise PreprocessorError(
                f"Identifier '{var.name}' referenced before definition.", location=var.location
            )

        if isinstance(identifier_definition, ConstDefinition):
            return identifier_definition.value

        if isinstance(identifier_definition, MemberDefinition):
            return identifier_definition.offset

        if isinstance(identifier_definition, LabelDefinition):
            location = var.location
            return ExprCast(
                expr=ExprConst(identifier_definition.pc, location=location),
                dest_type=TypeCodeoffset(location=location),
                location=location,
            )

        if isinstance(identifier_definition, (ReferenceDefinition, OffsetReferenceDefinition)):
            try:
                res_expr = identifier_definition.eval(
                    reference_manager=self.flow_tracking.reference_manager,
                    flow_tracking_data=self.flow_tracking.data,
                )
                if var.location is not None:
                    res_expr = add_parent_location(
                        expr=res_expr,
                        new_parent_location=var.location,
                        message=f"While expanding the reference '{var.name}' in:",
                    )
                return res_expr
            except LostReferenceError as err:
                err_to_throw = PreprocessorError(
                    f"Reference '{var.name}' was revoked.", location=var.location, notes=err.notes
                )
                if self.reference_trial is None:
                    raise err_to_throw
                self.reference_trial.bad_references[err.name, id(err.reference)] = (
                    err.reference,
                    err_to_throw,
                )
                return self.get_dummy_reference_expr(identifier_definition)
            except FlowTrackingError as exc:
                raise PreprocessorError(
                    f"Reference '{var.name}' was revoked.", location=var.location, notes=exc.notes
                )
            except DefinitionError as exc:
                raise PreprocessorError(str(exc), location=var.location)

        raise PreprocessorError(
            f"Unexpected identifier {var.name} of type {identifier_definition.TYPE}.",
            location=var.location,
        )

    def get_dummy_reference_expr(self, identifier_definition: IdentifierDefinition) -> Expression:
        if isinstance(identifier_definition, ReferenceDefinition):
            parent = identifier_definition
        elif isinstance(identifier_definition, OffsetReferenceDefinition):
            parent = identifier_definition.parent
        else:
            # Should not happen.
            raise NotImplementedError(
                f"Unsupported identifier type {type(identifier_definition).__name__}."
            )
        location = None
        if len(parent.references[0].locations) > 0:
            location = parent.references[0].locations[-1]
        expr = create_simple_ref_expr(
            reg=Register.FP,
            offset=0,
            cairo_type=parent.cairo_type,
            location=location,
        )
        if isinstance(identifier_definition, OffsetReferenceDefinition):
            for member_name in identifier_definition.member_path.path:
                expr = ExprDot(expr=expr, member=ExprIdentifier(name=member_name))
        return expr

    def get_instruction_size(self, instruction: InstructionAst, allow_auto_deduction: bool = False):
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
                exc.notes.append("Missing exact location information on this error.")
                exc.location = instruction.location
            exc.notes.append(f"Preprocessed instruction:\n{instruction.format()}")
            raise exc

    def check_preprocessed_instruction(self, instruction: InstructionAst):
        """
        Verifies that the instruction was successfully preprocessed.
        For example, an instruction of type JumpToLabelInstruction whose label is not known will
        remain of this type, which is not accepted by build_instruction().
        """
        if isinstance(instruction.body, (JumpToLabelInstruction, CallLabelInstruction)):
            label = instruction.body.label
            raise PreprocessorError(f"Unknown label {label.name}.", location=label.location)

    def check_no_hints(self, msg):
        """
        Makes sure that there are no unprocessed hints, and throws an exception with the given
        message otherwise.
        """
        if len(self.next_instruction_hints) != 0:
            raise PreprocessorError(msg, location=self.next_instruction_hints[0][0].location)

    def new_unique_id(self) -> str:
        """
        Returns a new identifier name.
        """
        name = f"__temp{self.next_temp_id}"
        self.next_temp_id += 1
        self.scoped_temp_ids[self.current_scope + name] = True
        return name

    def get_struct_members(self, struct_type: TypeStruct) -> List[str]:
        """
        Returns the list of members of the given struct.
        """
        struct_definition = self.identifiers.get_by_full_name(name=struct_type.resolved_scope)
        assert isinstance(
            struct_definition, StructDefinition
        ), f"Expected StructDefinition, found: {type(struct_definition).__name__}."
        return list(struct_definition.members.keys())

    def _add_next_hint(self, hint: CodeElementHint):
        self.next_instruction_hints.append((hint, self.flow_tracking.get()))

    def _clear_next_hints(self):
        self.next_instruction_hints = []


class PreprocessorCompoundExpressionContext(CompoundExpressionContext):
    def __init__(self, preprocessor: Preprocessor):
        self.preprocessor = preprocessor

    def new_tempvar_name(self) -> str:
        return self.preprocessor.new_unique_id()

    def get_fp_val(self, location: Optional[Location]) -> Expression:
        try:
            return self.preprocessor.simplify_expr_as_felt(
                ExprIdentifier(name="__fp__", location=location)
            )
        except PreprocessorError as exc:
            if "Unknown identifier" not in exc.message:
                raise
            raise PreprocessorError(
                "Using the value of fp directly, requires defining a variable named __fp__.",
                location=exc.location,
            )

    def visit(self, elm: CodeElement):
        self.preprocessor.visit(elm)

    def get_ap_tracking(self) -> RegTrackingData:
        return self.preprocessor.flow_tracking.get_ap_tracking()
