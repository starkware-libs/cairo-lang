import copy
import dataclasses
import re
import sys
import traceback
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, Tuple

from starkware.cairo.lang.compiler.debug_info import DebugInfo, InstructionLocation
from starkware.cairo.lang.compiler.encode import decode_instruction, is_call_instruction
from starkware.cairo.lang.compiler.error_handling import LocationError
from starkware.cairo.lang.compiler.expression_evaluator import ExpressionEvaluator
from starkware.cairo.lang.compiler.instruction import (
    Instruction, Register, decode_instruction_values)
from starkware.cairo.lang.compiler.program import Program, ProgramBase
from starkware.cairo.lang.vm.builtin_runner import BuiltinRunner
from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.cairo.lang.vm.trace_entry import TraceEntry
from starkware.cairo.lang.vm.validated_memory_dict import ValidatedMemoryDict, ValidationRule
from starkware.cairo.lang.vm.vm_consts import VmConsts, VmConstsContext
from starkware.python.math_utils import div_mod

Rule = Callable[['VirtualMachine', RelocatableValue], Optional[int]]

MAX_TRACEBACK_ENTRIES = 20


@dataclasses.dataclass
class Operands:
    """
    Values of the operands.
    """

    dst: MaybeRelocatable
    res: Optional[MaybeRelocatable]
    op0: MaybeRelocatable
    op1: MaybeRelocatable


class VmException(LocationError):
    def __init__(
            self, pc, inst_location: Optional[InstructionLocation], inner_exc,
            traceback: Optional[str] = None, notes: Optional[List[str]] = None, hint: bool = False):
        self.pc = pc
        self.inner_exc = inner_exc
        location = None
        if inst_location is not None:
            location = inst_location.inst
            # If the hint location is missing, fall back to the instruction location.
            if hint and inst_location.hint is not None:
                location = inst_location.hint.location
        super().__init__(
            f'Error at pc={self.pc}:\n{inner_exc}', location=location, traceback=traceback)
        if notes is not None:
            self.notes += notes


class InconsistentAutoDeductionError(Exception):
    def __init__(self, addr, current_value, new_value):
        self.addr = addr
        self.current_value = current_value
        self.new_value = new_value
        super().__init__(
            f'Inconsistent auto deduction rule at address {addr}. {current_value} != {new_value}.')


class PureValueError(Exception):
    def __init__(self, oper, *values):
        self.oper = oper
        self.values = values
        values_str = f'values {values}' if len(values) > 1 else f'value {values[0]}'
        super().__init__(
            f'Could not complete computation {oper} of non pure {values_str}.')


class HintException(Exception):
    def __init__(self, vm, exc_type, exc_value, exc_tb):
        tb_exception = traceback.TracebackException(exc_type, exc_value, exc_tb)
        # First item in the traceback is the call to exec, remove it.
        assert tb_exception.stack[0].filename.endswith('vm.py')
        del tb_exception.stack[0]

        # If we have location information, replace '<hint*>' entries with the correct filename
        # and line.
        def replace_stack_item(item: traceback.FrameSummary) -> traceback.FrameSummary:
            m = re.match('^<hint(?P<index>[0-9]+)>$', item.filename)
            if not m:
                return item
            location = vm.get_location(vm.hint_pcs[int(m.group('index'))])
            if not (location and location.hint):
                return item
            line_num = (
                item.lineno + location.hint.location.start_line +
                location.hint.n_prefix_newlines - 1)
            return traceback.FrameSummary(
                filename=location.hint.location.input_file.filename,
                lineno=line_num,
                name=item.name)
        tb_exception.stack = traceback.StackSummary.from_list(
            map(replace_stack_item, tb_exception.stack))
        super().__init__(f'Got an exception while executing a hint.')
        self.exception_str = ''.join(tb_exception.format())
        self.inner_exc = exc_value


@dataclasses.dataclass
class RunContext:
    """
    Contains a complete state of the virtual machine. This includes registers and memory.
    """

    memory: MemoryDict
    pc: MaybeRelocatable
    ap: MaybeRelocatable
    fp: MaybeRelocatable
    prime: int

    def get_instruction_encoding(self) -> Tuple[int, Optional[int]]:
        """
        Returns the encoded instruction (the value at pc) and the immediate value (the value at
        pc + 1, if it exists in the memory).
        """
        instruction_encoding = self.memory[self.pc]

        assert isinstance(instruction_encoding, int), \
            f'Instruction should be an int. Found: {instruction_encoding}'

        imm_addr = (self.pc + 1) % self.prime
        return instruction_encoding, self.memory.get(imm_addr)

    def compute_dst_addr(self, instruction: Instruction):
        base_addr: MaybeRelocatable
        if instruction.dst_register is Register.AP:
            base_addr = self.ap
        elif instruction.dst_register is Register.FP:
            base_addr = self.fp
        else:
            raise NotImplementedError('Invalid dst_register value')
        return (base_addr + instruction.off0) % self.prime

    def compute_op0_addr(self, instruction: Instruction):
        base_addr: MaybeRelocatable
        if instruction.op0_register is Register.AP:
            base_addr = self.ap
        elif instruction.op0_register is Register.FP:
            base_addr = self.fp
        else:
            raise NotImplementedError('Invalid op0_register value')
        return (base_addr + instruction.off1) % self.prime

    def compute_op1_addr(self, instruction: Instruction, op0: Optional[MaybeRelocatable]):
        base_addr: MaybeRelocatable
        if instruction.op1_addr is Instruction.Op1Addr.FP:
            base_addr = self.fp
        elif instruction.op1_addr is Instruction.Op1Addr.AP:
            base_addr = self.ap
        elif instruction.op1_addr is Instruction.Op1Addr.IMM:
            assert instruction.off2 == 1, 'In immediate mode, off2 should be 1'
            base_addr = self.pc
        elif instruction.op1_addr is Instruction.Op1Addr.OP0:
            assert op0 is not None, 'op0 must be known in double dereference'
            base_addr = op0
        else:
            raise NotImplementedError('Invalid op1_register value')
        return (base_addr + instruction.off2) % self.prime

    def get_traceback_entries(self):
        """
        Returns the values of pc of the call instructions in the traceback.
        Returns the most recent call last.
        """
        entries = []
        fp = self.fp
        for _ in range(MAX_TRACEBACK_ENTRIES):
            # Get the previous fp and the return pc.
            fp, ret_pc = self.memory.get(fp - 2), self.memory.get(fp - 1)

            # If one of them is not in memory, abort.
            if fp is None or ret_pc is None:
                break

            # Get the two memory cells before ret_pc.
            instruction0, instruction1 = self.memory.get(ret_pc - 2), self.memory.get(ret_pc - 1)

            # Try to check if the call instruction is (instruction0, instruction1) or just
            # instruction1 (with no immediate).
            # In rare cases this may be ambiguous.
            if instruction1 is not None and is_call_instruction(
                    encoded_instruction=instruction1, imm=None):
                call_pc = ret_pc - 1
            elif instruction0 is not None and instruction1 is not None and is_call_instruction(
                    encoded_instruction=instruction0, imm=instruction1):
                call_pc = ret_pc - 2
            else:
                # If none of them seems like the calling instruction, abort.
                break

            entries.append(call_pc)

        return entries[::-1]


@dataclasses.dataclass
class CompiledHint:
    compiled: Any
    consts: Callable[..., VmConsts]


class VirtualMachine:
    def __init__(
            self, program: ProgramBase, run_context: RunContext,
            hint_locals: dict, static_locals: dict = {},
            builtin_runners: Dict[str, BuiltinRunner] = {}, program_base: Optional[int] = None):
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
        program_base - The pc of the first instruction in program (default is run_context.pc).
        """
        self.prime = program.prime
        self.builtin_runners = builtin_runners
        self.exec_scopes: List[dict] = []
        self.enter_scope(dict(hint_locals))
        self.run_context = copy.copy(run_context)  # Shallow copy.
        self.hints: Dict[MaybeRelocatable, CompiledHint] = {}
        # A map from hint index to pc.
        self.hint_pcs: Dict[int, MaybeRelocatable] = {}
        self.instruction_debug_info: Dict[MaybeRelocatable, InstructionLocation] = {}
        self.debug_file_contents: Dict[str, str] = {}
        self.program = program
        self.program_base = program_base if program_base is not None else self.run_context.pc
        self.validated_memory = ValidatedMemoryDict(memory=self.run_context.memory)

        # If program is a StrippedProgram, there are no hints or debug information to load.
        if isinstance(program, Program):
            self.load_program(
                program=program,
                program_base=self.program_base,
            )

        self.trace: List[TraceEntry[MaybeRelocatable]] = []

        # auto_deduction contains a mapping from a memory segment index to a list of functions
        # (and a tuple of additional arguments) that may try to automatically deduce the value
        # of memory cells in the segment (based on other memory cells).
        self.auto_deduction: Dict[int, List[Tuple[Rule, tuple]]] = {}
        # Current step.
        self.current_step = 0

        # This flag can be set to true by hints to avoid the execution of the current step in
        # step() (so that only the hint will be performed, but nothing else will happen).
        self.skip_instruction_execution = False

        from starkware.python import math_utils
        self.static_locals = static_locals.copy()
        self.static_locals.update({
            'PRIME': self.prime,
            'fadd': lambda a, b, p=self.prime: (a + b) % p,
            'fsub': lambda a, b, p=self.prime: (a - b) % p,
            'fmul': lambda a, b, p=self.prime: (a * b) % p,
            'fdiv': lambda a, b, p=self.prime: math_utils.div_mod(a, b, p),
            'fpow': lambda a, b, p=self.prime: pow(a, b, p),
            'fis_quad_residue': lambda a, p=self.prime: math_utils.is_quad_residue(a, p),
            'fsqrt': lambda a, p=self.prime: math_utils.sqrt(a, p),
            'safe_div': math_utils.safe_div,
        })

    def load_hints(self, program: Program, program_base: MaybeRelocatable):
        for i, (pc, hint) in enumerate(program.hints.items(), len(self.hint_pcs)):
            self.hints[pc + program_base] = CompiledHint(
                compiled=self.compile_hint(hint.code, f'<hint{i}>'),
                # Use hint=hint in the lambda's arguments to capture this value (otherwise, it
                # will use the same hint object for all iterations).
                consts=lambda pc, ap, fp, memory, hint=hint: VmConsts(
                    context=VmConstsContext(
                        identifiers=program.identifiers,
                        evaluator=ExpressionEvaluator(self.prime, ap, fp, memory).eval,
                        reference_manager=program.reference_manager,
                        flow_tracking_data=hint.flow_tracking_data,
                        memory=memory,
                        pc=pc),
                    accessible_scopes=hint.accessible_scopes))
            self.hint_pcs[i] = pc + program_base

    def load_debug_info(self, debug_info: Optional[DebugInfo], program_base: MaybeRelocatable):
        if debug_info is None:
            return

        self.debug_file_contents.update(debug_info.file_contents)

        for offset, location_info in debug_info.instruction_locations.items():
            self.instruction_debug_info[program_base + offset] = location_info

    def load_program(self, program: Program, program_base: MaybeRelocatable):
        assert self.prime == program.prime, \
            f'Unexpected prime for loaded program: {program.prime} != {self.prime}.'

        self.load_hints(program, program_base)
        self.load_debug_info(program.debug_info, program_base)

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
        self.exec_scopes.pop()

    def update_registers(self, instruction: Instruction, operands: Operands):
        # Update fp.
        if instruction.fp_update is Instruction.FpUpdate.AP_PLUS2:
            self.run_context.fp = self.run_context.ap + 2
        elif instruction.fp_update is Instruction.FpUpdate.DST:
            self.run_context.fp = operands.dst
        elif instruction.fp_update is not Instruction.FpUpdate.REGULAR:
            raise NotImplementedError('Invalid fp_update value')

        # Update ap.
        if instruction.ap_update is Instruction.ApUpdate.ADD:
            if operands.res is None:
                raise NotImplementedError('Res.UNCONSTRAINED cannot be used with ApUpdate.ADD')
            self.run_context.ap += operands.res % self.prime
        elif instruction.ap_update is Instruction.ApUpdate.ADD1:
            self.run_context.ap += 1
        elif instruction.ap_update is Instruction.ApUpdate.ADD2:
            self.run_context.ap += 2
        elif instruction.ap_update is not Instruction.ApUpdate.REGULAR:
            raise NotImplementedError('Invalid ap_update value')
        self.run_context.ap = self.run_context.ap % self.prime

        # Update pc.
        # The pc update should be done last so that we will have the correct pc in case of an
        # exception during one of the updates above.
        if instruction.pc_update is Instruction.PcUpdate.REGULAR:
            self.run_context.pc += instruction.size
        elif instruction.pc_update is Instruction.PcUpdate.JUMP:
            if operands.res is None:
                raise NotImplementedError('Res.UNCONSTRAINED cannot be used with PcUpdate.JUMP')
            self.run_context.pc = operands.res
        elif instruction.pc_update is Instruction.PcUpdate.JUMP_REL:
            if operands.res is None:
                raise NotImplementedError('Res.UNCONSTRAINED cannot be used with PcUpdate.JUMP_REL')
            if not isinstance(operands.res, int):
                raise PureValueError('jmp rel', operands.res)
            self.run_context.pc += operands.res
        elif instruction.pc_update is Instruction.PcUpdate.JNZ:
            if self.is_zero(operands.dst):
                self.run_context.pc += instruction.size
            else:
                self.run_context.pc += operands.op1
        else:
            raise NotImplementedError('Invalid pc_update value')
        self.run_context.pc = self.run_context.pc % self.prime

    def deduce_op0(
            self, instruction: Instruction, dst: Optional[MaybeRelocatable],
            op1: Optional[MaybeRelocatable]) -> \
            Tuple[Optional[MaybeRelocatable], Optional[MaybeRelocatable]]:
        if instruction.opcode is Instruction.Opcode.CALL:
            return self.run_context.pc + instruction.size, None
        elif instruction.opcode is Instruction.Opcode.ASSERT_EQ:
            if (instruction.res is Instruction.Res.ADD) and (dst is not None) and \
                    (op1 is not None):
                return (dst - op1) % self.prime, dst  # type: ignore
            elif (instruction.res is Instruction.Res.MUL) and isinstance(dst, int) and \
                    isinstance(op1, int) and op1 != 0:
                return div_mod(dst, op1, self.prime), dst
        return None, None

    def deduce_op1(
            self, instruction: Instruction, dst: Optional[MaybeRelocatable],
            op0: Optional[MaybeRelocatable]) -> \
            Tuple[Optional[MaybeRelocatable], Optional[MaybeRelocatable]]:
        if instruction.opcode is Instruction.Opcode.ASSERT_EQ:
            if (instruction.res is Instruction.Res.OP1) and (dst is not None):
                return dst, dst
            elif (instruction.res is Instruction.Res.ADD) and (dst is not None) and \
                    (op0 is not None):
                return (dst - op0) % self.prime, dst  # type: ignore
            elif (instruction.res is Instruction.Res.MUL) and isinstance(dst, int) and \
                    isinstance(op0, int) and op0 != 0:
                return div_mod(dst, op0, self.prime), dst
        return None, None

    def compute_res(
            self, instruction: Instruction, op0: MaybeRelocatable, op1: MaybeRelocatable,
            op0_addr: MaybeRelocatable) -> Optional[MaybeRelocatable]:
        if instruction.res is Instruction.Res.OP1:
            return op1
        elif instruction.res is Instruction.Res.ADD:
            return (op0 + op1) % self.prime
        elif instruction.res is Instruction.Res.MUL:
            if isinstance(op0, RelocatableValue) or isinstance(op1, RelocatableValue):
                raise PureValueError('*', op0, op1)
            return (op0 * op1) % self.prime
        elif instruction.res is Instruction.Res.UNCONSTRAINED:
            # In this case res should be the inverse of dst.
            # For efficiency, we do not compute it here.
            return None
        else:
            raise NotImplementedError('Invalid res value')

    def compute_operands(self, instruction: Instruction) -> \
            Tuple[Operands, List[int], List[MaybeRelocatable]]:
        """
        Computes the values of the operands. Deduces dst if needed.
        Returns:
          operands - an Operands instance with the values of the operands.
          mem_addresses - the memory addresses for the 3 memory units used (dst, op0, op1).
          mem_values - the corresponding memory values.
        """
        # Try to fetch dst, op0, op1.
        # op0 throughout this function represents the value at op0_addr.
        # If op0 is set, this implies that we are going to set memory at op0_addr to that value.
        # Same for op1, dst.
        dst_addr = self.run_context.compute_dst_addr(instruction)
        dst: Optional[MaybeRelocatable] = self.validated_memory.get(dst_addr)
        op0_addr = self.run_context.compute_op0_addr(instruction)
        op0: Optional[MaybeRelocatable] = self.validated_memory.get(op0_addr)
        op1_addr = self.run_context.compute_op1_addr(instruction, op0=op0)
        op1: Optional[MaybeRelocatable] = self.validated_memory.get(op1_addr)
        # res throughout this function represents the computation on op0,op1
        # as defined in decode.py.
        # If it is set, this implies that compute_res(...) will return this value.
        # If it is set without invoking compute_res(), this is an optimization, but should not
        # yield a different result.
        # In particular, res may be different than dst, even in ASSERT_EQ. In this case,
        # The ASSERT_EQ validation will fail in opcode_assertions().
        res: Optional[MaybeRelocatable] = None

        # Auto deduction rules.
        # Note: This may fail to deduce if 2 auto deduction rules are needed to be used in
        # a different order.
        if op0 is None:
            op0 = self.deduce_memory_cell(op0_addr)
        if op1 is None:
            op1 = self.deduce_memory_cell(op1_addr)

        should_update_dst = dst is None
        should_update_op0 = op0 is None
        should_update_op1 = op1 is None

        # Deduce op0 if needed.
        if op0 is None:
            op0, deduced_res = self.deduce_op0(instruction, dst, op1)
            if res is None:
                res = deduced_res

        # Deduce op1 if needed.
        if op1 is None:
            op1, deduced_res = self.deduce_op1(instruction, dst, op0)
            if res is None:
                res = deduced_res

        # Force pulling op0, op1 from memory for soundness test
        # and to get an informative error message if they were not computed.
        if op0 is None:
            op0 = self.validated_memory[op0_addr]
        if op1 is None:
            op1 = self.validated_memory[op1_addr]

        # Compute res if needed.
        if res is None:
            res = self.compute_res(instruction, op0, op1, op0_addr)

        # Deduce dst.
        if dst is None:
            if instruction.opcode is Instruction.Opcode.ASSERT_EQ and res is not None:
                dst = res
            elif instruction.opcode is Instruction.Opcode.CALL:
                dst = self.run_context.fp

        # Force pulling dst from memory for soundness.
        if dst is None:
            dst = self.validated_memory[dst_addr]

        # Write updated values.
        if should_update_dst:
            self.validated_memory[dst_addr] = dst
        if should_update_op0:
            self.validated_memory[op0_addr] = op0
        if should_update_op1:
            self.validated_memory[op1_addr] = op1

        return Operands(
            dst=dst,
            op0=op0,
            op1=op1,
            res=res), [dst_addr, op0_addr, op1_addr], [dst, op0, op1]

    def is_zero(self, value):
        """
        Returns True if value is zero (used for jnz instructions).
        This function can be overridden by subclasses.
        """
        if not isinstance(value, int):
            raise PureValueError('jmp != 0', value)
        return value == 0

    def is_integer_value(self, value):
        """
        Returns True if value is integer rather than relocatable.
        This function can be overridden by subclasses.
        """
        return isinstance(value, int)

    @staticmethod
    @lru_cache(None)
    def decode_instruction(encoded_inst: int, imm: Optional[int] = None):
        return decode_instruction(encoded_inst, imm)

    def decode_current_instruction(self):
        try:
            instruction_encoding, imm = self.run_context.get_instruction_encoding()
        except Exception as exc:
            raise self.as_vm_exception(exc) from None

        instruction = self.decode_instruction(instruction_encoding, imm)

        return instruction, instruction_encoding

    def opcode_assertions(self, instruction: Instruction, operands: Operands):
        if instruction.opcode is Instruction.Opcode.ASSERT_EQ:
            if operands.res is None:
                raise NotImplementedError(
                    'Res.UNCONSTRAINED cannot be used with Opcode.ASSERT_EQ')
            if operands.dst != operands.res and not self.check_eq(operands.dst, operands.res):
                raise Exception(
                    f'An ASSERT_EQ instruction failed: {operands.dst} != {operands.res}')
        elif instruction.opcode is Instruction.Opcode.CALL:
            next_pc = self.run_context.pc + instruction.size
            if operands.op0 != next_pc and not self.check_eq(operands.op0, next_pc):
                raise Exception(
                    'Call failed to write return-pc (inconsistent op0): ' +
                    f'{operands.op0} != {next_pc}. Did you forget to increment ap?')
            fp = self.run_context.fp
            if operands.dst != fp and not self.check_eq(operands.dst, fp):
                raise Exception(
                    'Call failed to write return-fp (inconsistent dst): ' +
                    f'{operands.dst} != {fp}. Did you forget to increment ap?')
        elif instruction.opcode in [Instruction.Opcode.RET, Instruction.Opcode.NOP]:
            # Nothing to check.
            pass
        else:
            raise NotImplementedError(f'Unsupported opcode {instruction.opcode}')

    def step(self):
        self.skip_instruction_execution = False
        # Execute hints.
        hint = self.hints.get(self.run_context.pc)

        if hint is not None:
            exec_locals = self.exec_scopes[-1]
            exec_locals['memory'] = memory = self.validated_memory
            exec_locals['ap'] = ap = self.run_context.ap
            exec_locals['fp'] = fp = self.run_context.fp
            exec_locals['pc'] = pc = self.run_context.pc
            exec_locals['current_step'] = self.current_step
            exec_locals['ids'] = hint.consts(pc, ap, fp, memory)

            exec_locals['vm_load_program'] = self.load_program
            exec_locals['vm_enter_scope'] = self.enter_scope
            exec_locals['vm_exit_scope'] = self.exit_scope
            exec_locals.update(self.static_locals)

            self.exec_hint(hint.compiled, exec_locals)

            # Clear ids (which will be rewritten by the next hint anyway) to make the VM instance
            # smaller and faster to copy.
            del exec_locals['ids']
            del exec_locals['memory']

            if self.skip_instruction_execution:
                return

        # Decode.
        instruction, instruction_encoding = self.decode_current_instruction()

        self.run_instruction(instruction, instruction_encoding)

    def compile_hint(self, source, filename):
        """
        Compiles the given python source code.
        This function can be overridden by subclasses.
        """
        return compile(source, filename, mode='exec')

    def exec_hint(self, code, globals_):
        """
        Executes the given code with the given globals.
        This function can be overridden by subclasses.
        """
        try:
            exec(code, globals_)
        except Exception:
            hint_exception = HintException(self, *sys.exc_info())
            raise self.as_vm_exception(
                hint_exception, notes=[hint_exception.exception_str], hint=True) from None

    def run_instruction(self, instruction, instruction_encoding):
        try:
            # Compute operands.
            operands, operands_mem_addresses, operands_mem_values = self.compute_operands(
                instruction)
        except Exception as exc:
            raise self.as_vm_exception(exc) from None

        try:
            # Opcode assertions.
            self.opcode_assertions(instruction, operands)
        except Exception as exc:
            raise self.as_vm_exception(exc) from None

        # Write to trace.
        self.trace.append(TraceEntry(
            pc=self.run_context.pc,
            ap=self.run_context.ap,
            fp=self.run_context.fp,
        ))

        try:
            # Update registers.
            self.update_registers(instruction, operands)
        except Exception as exc:
            raise self.as_vm_exception(exc) from None

        self.current_step += 1

    def check_eq(self, val0, val1):
        """
        Called when an instruction encounters an assertion that two values should be equal.
        This function can be overridden by subclasses.
        """
        return val0 == val1

    @property
    def last_pc(self):
        """
        Returns the value of the program counter for the last instruction that was execute.
        Note that this is different from self.run_context.pc which contains the value of the
        next instruction to be executed.
        """
        return self.trace[-1].pc

    def as_vm_exception(self, exc, pc=None, notes: Optional[List[str]] = None, hint: bool = False):
        """
        Wraps the exception with a VmException, adding to it location information. If pc is not
        given the current pc is used.
        """
        traceback = None
        if pc is None:
            pc = self.run_context.pc
            traceback = self.get_traceback()

        return VmException(
            pc=pc,
            inst_location=self.get_location(pc=pc),
            inner_exc=exc,
            traceback=traceback,
            notes=notes,
            hint=hint,
        )

    def get_location(self, pc) -> Optional[InstructionLocation]:
        return self.instruction_debug_info.get(pc)

    def get_traceback(self) -> Optional[str]:
        """
        Returns the traceback at the current pc.
        """
        traceback = ''
        for traceback_pc in self.run_context.get_traceback_entries():
            location = self.get_location(pc=traceback_pc)
            if location is None:
                traceback += f'Unknown location (pc={traceback_pc})\n'
                continue
            traceback += location.inst.to_string_with_content(message=f'(pc={traceback_pc})') + '\n'
        if len(traceback) == 0:
            return None
        return 'Cairo traceback (most recent call last):\n' + traceback

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
        assert len(self.exec_scopes) == 1, \
            'Every enter_scope() requires a corresponding exit_scope().'


def get_perm_range_check_limits(
        trace: List[TraceEntry[int]],
        memory: MemoryDict) -> Tuple[int, int]:
    """
    Returns the minimum value and maximum value in the perm_range_check component.
    """
    offsets: List[int] = []
    for entry in trace:
        encoded_instruction = memory[entry.pc]
        _, off0, off1, off2 = decode_instruction_values(encoded_instruction)
        offsets += [off0, off1, off2]
    return min(offsets), max(offsets)
