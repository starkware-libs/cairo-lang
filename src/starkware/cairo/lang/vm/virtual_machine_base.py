import dataclasses
import re
import sys
from abc import ABC
from typing import Any, Callable, Dict, List, Optional, Tuple

from typing_extensions import Protocol

from starkware.cairo.lang.compiler.debug_info import DebugInfo, InstructionLocation
from starkware.cairo.lang.compiler.encode import is_call_instruction
from starkware.cairo.lang.compiler.expression_evaluator import ExpressionEvaluator
from starkware.cairo.lang.compiler.instruction import decode_instruction_values
from starkware.cairo.lang.compiler.preprocessor.flow import FlowTrackingDataActual
from starkware.cairo.lang.compiler.preprocessor.preprocessor import AttributeBase, AttributeScope
from starkware.cairo.lang.compiler.preprocessor.reg_tracking import RegTrackingData
from starkware.cairo.lang.compiler.program import Program, ProgramBase
from starkware.cairo.lang.compiler.references import ApDeductionError
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.vm.builtin_runner import BuiltinRunner
from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.cairo.lang.vm.trace_entry import TraceEntry
from starkware.cairo.lang.vm.utils import decimal_repr
from starkware.cairo.lang.vm.validated_memory_dict import ValidatedMemoryDict, ValidationRule
from starkware.cairo.lang.vm.vm_consts import VmConsts, VmConstsContext
from starkware.cairo.lang.vm.vm_exceptions import (
    HintException,
    InconsistentAutoDeductionError,
    VmException,
    VmExceptionBase,
)
from starkware.starknet.security.simple_references import (
    InvalidReferenceExpressionError,
    is_simple_reference,
)


class Rule(Protocol):
    def __call__(
        self, vm: "VirtualMachineBase", addr: RelocatableValue, *args: Any
    ) -> Optional[MaybeRelocatable]:
        pass


MAX_TRACEBACK_ENTRIES = 20
ERROR_MESSAGE_ATTRIBUTE = "error_message"


@dataclasses.dataclass(frozen=True)
class VmAttributeScope(AttributeBase):
    start_pc: MaybeRelocatable
    end_pc: MaybeRelocatable
    flow_tracking_data: Optional[FlowTrackingDataActual]
    accessible_scopes: List[ScopedName]

    @classmethod
    def from_attribute_scope(cls, attr: AttributeScope, program_base: MaybeRelocatable):
        return cls(
            name=attr.name,
            value=attr.value,
            start_pc=program_base + attr.start_pc,
            end_pc=program_base + attr.end_pc,
            flow_tracking_data=attr.flow_tracking_data,
            accessible_scopes=attr.accessible_scopes,
        )


@dataclasses.dataclass
class CompiledHint:
    compiled: Any
    consts: Callable[..., VmConsts]


class RunContextBase(ABC):
    """
    Contains a complete state of the virtual machine. This includes registers and memory.
    """

    memory: MemoryDict
    pc: MaybeRelocatable
    ap: MaybeRelocatable
    fp: MaybeRelocatable
    prime: int

    def get_traceback_entries(self) -> List[Tuple[MaybeRelocatable, MaybeRelocatable]]:
        """
        Returns the values (fp, pc) corresponding to each call instruction in the traceback.
        Returns the most recent call last.
        """
        entries = []
        fp = self.fp
        for _ in range(MAX_TRACEBACK_ENTRIES):
            if self.memory.get(fp - 2) == fp:
                break

            # Get the previous fp and the return pc.
            opt_fp, opt_ret_pc = self.memory.get(fp - 2), self.memory.get(fp - 1)

            # If one of them is not in memory, abort.
            if opt_fp is None or opt_ret_pc is None:
                break

            fp, ret_pc = opt_fp, opt_ret_pc

            # Get the two memory cells before ret_pc.
            instruction0, instruction1 = self.memory.get(ret_pc - 2), self.memory.get(ret_pc - 1)

            # Try to check if the call instruction is (instruction0, instruction1) or just
            # instruction1 (with no immediate).
            # In rare cases this may be ambiguous.
            if isinstance(instruction1, int) and is_call_instruction(
                encoded_instruction=instruction1, imm=None
            ):
                call_pc = ret_pc - 1
            elif (
                isinstance(instruction0, int)
                and isinstance(instruction1, int)
                and is_call_instruction(encoded_instruction=instruction0, imm=instruction1)
            ):
                call_pc = ret_pc - 2
            else:
                # If none of them seems like the calling instruction, abort.
                break

            entries.append((fp, call_pc))

        return entries[::-1]


class VirtualMachineBase(ABC):
    run_context: RunContextBase

    def __init__(
        self,
        program: ProgramBase,
        run_context: RunContextBase,
        hint_locals: Dict[str, Any],
        static_locals: Optional[Dict[str, Any]],
        builtin_runners: Dict[str, BuiltinRunner],
        program_base: MaybeRelocatable,
    ):
        """
        hints - a dictionary from memory addresses to an executable object.
          When the pc points to the memory address, before the execution of the instruction,
          the executable object will be run.
          Executable objects are anything that can be placed inside exec.
          For example, 'a=5', or compile('a=5').
        hint_locals - dictionary holding local values for execution of hints.
          Passed as locals parameter for the exec function.
        static_locals - dictionary holding static values for execution. They are available in all
          scopes.
        program_base - The pc of the first instruction in program.
        """
        self.prime = program.prime
        self.builtin_runners = builtin_runners
        self.exec_scopes: List[dict] = []
        self.enter_scope(dict(hint_locals))
        self.hints: Dict[MaybeRelocatable, List[CompiledHint]] = {}
        # A map from hint id to pc and index (index is required when there is more than one hint
        # for a single pc).
        self.hint_pc_and_index: Dict[int, Tuple[MaybeRelocatable, int]] = {}
        self.instruction_debug_info: Dict[MaybeRelocatable, InstructionLocation] = {}
        self.debug_file_contents: Dict[str, str] = {}
        self.error_message_attributes: List[VmAttributeScope] = []
        self.program = program
        self.validated_memory = ValidatedMemoryDict(memory=run_context.memory)

        # If program is a StrippedProgram, there are no hints or debug information to load.
        if isinstance(program, Program):
            self.load_program(program=program, program_base=program_base)

        # auto_deduction contains a mapping from a memory segment index to a list of functions
        # (and a tuple of additional arguments) that may try to automatically deduce the value
        # of memory cells in the segment (based on other memory cells).
        self.auto_deduction: Dict[int, List[Tuple[Rule, tuple]]] = {}

        from starkware.python import math_utils

        self.static_locals = static_locals.copy() if static_locals is not None else {}
        self.static_locals.update(
            {
                "PRIME": self.prime,
                "fadd": lambda a, b, p=self.prime: (a + b) % p,
                "fsub": lambda a, b, p=self.prime: (a - b) % p,
                "fmul": lambda a, b, p=self.prime: (a * b) % p,
                "fdiv": lambda a, b, p=self.prime: math_utils.div_mod(a, b, p),
                "fpow": lambda a, b, p=self.prime: pow(a, b, p),
                "fis_quad_residue": lambda a, p=self.prime: math_utils.is_quad_residue(a, p),
                "fsqrt": lambda a, p=self.prime: math_utils.sqrt(a, p),
                "safe_div": math_utils.safe_div,
                "to_felt_or_relocatable": RelocatableValue.to_felt_or_relocatable,
            }
        )

    def validate_existing_memory(self):
        """
        Validates the builtin values (e.g., range-checks) that are already written to the VM's
        memory.
        """
        self.validated_memory.validate_existing_memory()

    def load_hints(self, program: Program, program_base: MaybeRelocatable):
        for pc, hints in program.hints.items():
            compiled_hints = []
            for hint_index, hint in enumerate(hints):
                hint_id = len(self.hint_pc_and_index)
                self.hint_pc_and_index[hint_id] = (pc + program_base, hint_index)
                compiled_hints.append(
                    CompiledHint(
                        compiled=self.compile_hint(
                            hint.code, f"<hint{hint_id}>", hint_index=hint_index
                        ),
                        # Use hint=hint in the lambda's arguments to capture this value (otherwise,
                        # it will use the same hint object for all iterations).
                        consts=lambda pc, ap, fp, memory, hint=hint: VmConsts(
                            context=VmConstsContext(
                                identifiers=program.identifiers,
                                evaluator=ExpressionEvaluator(
                                    self.prime, ap, fp, memory, program.identifiers
                                ).eval,
                                reference_manager=program.reference_manager,
                                flow_tracking_data=hint.flow_tracking_data,
                                memory=memory,
                                pc=pc,
                            ),
                            accessible_scopes=hint.accessible_scopes,
                        ),
                    )
                )
            self.hints[pc + program_base] = compiled_hints

    def load_debug_info(self, debug_info: Optional[DebugInfo], program_base: MaybeRelocatable):
        if debug_info is None:
            return

        self.debug_file_contents.update(debug_info.file_contents)

        for offset, location_info in debug_info.instruction_locations.items():
            self.instruction_debug_info[program_base + offset] = location_info

    def load_program(self, program: Program, program_base: MaybeRelocatable):
        assert (
            self.prime == program.prime
        ), f"Unexpected prime for loaded program: {program.prime} != {self.prime}."

        self.load_debug_info(program.debug_info, program_base)
        self.load_hints(program, program_base)
        self.error_message_attributes.extend(
            VmAttributeScope.from_attribute_scope(attr=attr, program_base=program_base)
            for attr in program.attributes
            if attr.name == ERROR_MESSAGE_ATTRIBUTE
        )

    def enter_scope(self, new_scope_locals: Optional[dict] = None):
        """
        Starts a new scope of user-defined local variables available to hints.
        Note that variables defined in outer scopes will not be available in the new scope.
        A dictionary of locals that should be available in the new scope should be passed in
        new_scope_locals.
        The scope starts only from the next hint.
        exit_scope() must be called to resume the previous scope.
        """
        if new_scope_locals is None:
            new_scope_locals = {}

        self.exec_scopes.append({**new_scope_locals, **self.builtin_runners})

    def exit_scope(self):
        assert len(self.exec_scopes) > 1, "Cannot exit main scope."
        self.exec_scopes.pop()

    def compile_hint(self, source, filename, hint_index: int):
        """
        Compiles the given python source code.
        This function can be overridden by subclasses.
        """
        try:
            return compile(source, filename, mode="exec")
        except (IndentationError, SyntaxError):
            hint_exception = HintException(self, *sys.exc_info())
            raise self.as_vm_exception(
                hint_exception, notes=[hint_exception.exception_str], hint_index=hint_index
            ) from None

    def exec_hint(self, code, globals_, hint_index):
        """
        Executes the given code with the given globals.
        This function can be overridden by subclasses.
        """
        try:
            exec(code, globals_)
        except Exception:
            hint_exception = HintException(self, *sys.exc_info())
            raise self.as_vm_exception(
                hint_exception, notes=[hint_exception.exception_str], hint_index=hint_index
            ) from None

    def as_vm_exception(
        self,
        exc,
        with_traceback: bool = True,
        notes: Optional[List[str]] = None,
        hint_index: Optional[int] = None,
    ):
        """
        Wraps the exception with a VmException, adding to it location information.
        The current pc is used.
        """
        pc = self.run_context.pc
        traceback = self.get_traceback() if with_traceback else None

        return VmException(
            pc=pc,
            inst_location=self.get_location(pc=pc),
            inner_exc=exc,
            error_attr_value=self.get_error_attr_value(pc=pc, fp=self.run_context.fp),
            traceback=traceback,
            notes=notes,
            hint_index=hint_index,
        )

    def get_location(self, pc) -> Optional[InstructionLocation]:
        return self.instruction_debug_info.get(pc)

    def evaluate_reference(
        self,
        name: str,
        accessible_scopes: List[ScopedName],
        flow_tracking_data: FlowTrackingDataActual,
        fp: MaybeRelocatable,
    ) -> MaybeRelocatable:
        """
        Returns the value of the given reference with respect to the given fp.
        If the reference is ap-based, ApDeductionError is thrown.
        """
        assert isinstance(self.program, Program)
        identifier = self.program.identifiers.search(
            accessible_scopes=accessible_scopes, name=ScopedName.from_string(name)
        )
        reference = flow_tracking_data.resolve_reference(
            reference_manager=self.program.reference_manager,
            name=identifier.get_canonical_name(),
        )

        # A security check that the reference is not too complicated, doesn't rely on other
        # references, doesn't contain nondet-hints, etc.
        if not is_simple_reference(reference.value, simplicity_bound=20):
            raise InvalidReferenceExpressionError()

        # Evaluate the reference using an invalid ap_tracking, which will throw an ApDeductionError
        # exception if the reference is ap-based.
        expr = reference.eval(RegTrackingData(-1, 0))
        return ExpressionEvaluator[MaybeRelocatable](
            prime=self.prime,
            ap=None,
            fp=fp,
            memory=self.validated_memory,  # type: ignore
        ).eval(expr)

    def substitute_error_message_references(self, error_message_attr: VmAttributeScope, fp) -> str:
        """
        Substitutes references in the given error_message attribute with their actual value.
        References are defined with '{}'. E.g., 'x must be positive. Got: {x}'.
        """
        error_message = error_message_attr.value
        if error_message_attr.flow_tracking_data is None:
            return error_message
        flow_tracking_data = error_message_attr.flow_tracking_data

        invalid_references = []

        def substitute_ref(match):
            reference = match.group("name")
            try:
                val = self.evaluate_reference(
                    name=reference,
                    accessible_scopes=error_message_attr.accessible_scopes,
                    flow_tracking_data=flow_tracking_data,
                    fp=fp,
                )
                return decimal_repr(val, self.prime)
            except (ApDeductionError, InvalidReferenceExpressionError):
                invalid_references.append(reference)
                return match.group(0)

        error_message = re.sub(r"{(?P<name>[a-zA-Z_0-9.]+)}", substitute_ref, error_message)
        if len(invalid_references) > 0:
            error_message += (
                f" (Cannot evaluate ap-based or complex references: {invalid_references})"
            )

        return error_message

    def get_error_attr_value(self, pc, fp) -> str:
        """
        Returns the error messages that correspond to the error_message attribute scopes surrounding
        the given pc.
        """
        errors = ""
        for error_message_attr in self.error_message_attributes:
            if error_message_attr.start_pc <= pc < error_message_attr.end_pc:
                error_message = self.substitute_error_message_references(error_message_attr, fp)
                errors += f"Error message: {error_message}\n"
        return errors

    def get_traceback(self) -> Optional[str]:
        """
        Returns the traceback at the current pc.
        """
        traceback = ""
        for fp, traceback_pc in self.run_context.get_traceback_entries():
            traceback += self.get_error_attr_value(pc=traceback_pc, fp=fp)
            location = self.get_location(pc=traceback_pc)
            if location is None:
                traceback += f"Unknown location (pc={traceback_pc})\n"
                continue
            traceback += location.inst.to_string_with_content(message=f"(pc={traceback_pc})") + "\n"
        if len(traceback) == 0:
            return None
        return "Cairo traceback (most recent call last):\n" + traceback

    def add_validation_rule(self, segment_index, rule: ValidationRule, *args):
        self.validated_memory.add_validation_rule(segment_index, rule, *args)

    def add_auto_deduction_rule(self, segment_index, rule: Rule, *args):
        """
        Adds an auto deduction rule for the given memory segment.
        'rule' will be called with an address of a memory cell. It may return a value for the
        memory cell or None if the auto deduction does not apply.
        """
        self.auto_deduction.setdefault(segment_index, []).append((rule, args))

    def deduce_memory_cell(self, addr) -> Optional[MaybeRelocatable]:
        """
        Tries to deduce the value of memory[addr] if it was not already computed.
        Returns the value if deduced, otherwise returns None.
        """
        if not isinstance(addr, RelocatableValue):
            return None

        rules = self.auto_deduction.get(addr.segment_index, [])
        for rule, args in rules:
            value = rule(self, addr, *args)
            if value is None:
                continue

            self.validated_memory[addr] = value
            return value
        return None

    def verify_auto_deductions(self):
        """
        Makes sure that all assigned memory cells are consistent with their auto deduction rules.
        """
        for addr in self.validated_memory:
            if not isinstance(addr, RelocatableValue):
                continue
            for rule, args in self.auto_deduction.get(addr.segment_index, []):
                value = rule(self, addr, *args)
                if value is None:
                    continue

                current = self.validated_memory[addr]
                # If the values are not the same, try using check_eq to allow a subclass
                # to override this result.
                if current != value and not self.check_eq(current, value):
                    raise InconsistentAutoDeductionError(addr, current, value)

    def end_run(self):
        self.verify_auto_deductions()
        if len(self.exec_scopes) != 1:
            raise VmExceptionBase("Every enter_scope() requires a corresponding exit_scope().")

    def check_eq(self, val0: MaybeRelocatable, val1: MaybeRelocatable) -> bool:
        """
        Called when an instruction encounters an assertion that two values should be equal.
        This function can be overridden by subclasses.
        """
        return val0 == val1


def get_perm_range_check_limits(
    trace: List[TraceEntry[int]], memory: MemoryDict
) -> Tuple[int, int]:
    """
    Returns the minimum value and maximum value in the perm_range_check component.
    """
    offsets: List[int] = []
    for entry in trace:
        encoded_instruction = memory[entry.pc]
        _, off0, off1, off2 = decode_instruction_values(encoded_instruction)
        offsets += [off0, off1, off2]
    return min(offsets), max(offsets)
