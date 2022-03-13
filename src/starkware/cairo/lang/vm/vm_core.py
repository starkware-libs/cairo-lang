import copy
import dataclasses
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set, Tuple

from starkware.cairo.lang.compiler.encode import decode_instruction
from starkware.cairo.lang.compiler.instruction import Instruction, Register
from starkware.cairo.lang.compiler.program import ProgramBase
from starkware.cairo.lang.vm.builtin_runner import BuiltinRunner
from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.cairo.lang.vm.trace_entry import TraceEntry
from starkware.cairo.lang.vm.virtual_machine_base import RunContextBase, VirtualMachineBase
from starkware.cairo.lang.vm.vm_exceptions import PureValueError
from starkware.python.math_utils import div_mod


@dataclasses.dataclass
class Operands:
    """
    Values of the operands.
    """

    dst: MaybeRelocatable
    res: Optional[MaybeRelocatable]
    op0: MaybeRelocatable
    op1: MaybeRelocatable


@dataclasses.dataclass
class RunContext(RunContextBase):
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

        assert isinstance(
            instruction_encoding, int
        ), f"Instruction should be an int. Found: {instruction_encoding}"

        imm_addr = (self.pc + 1) % self.prime
        optional_imm = self.memory.get(imm_addr)
        if not isinstance(optional_imm, int):
            optional_imm = None
        return instruction_encoding, optional_imm

    def compute_dst_addr(self, instruction: Instruction):
        base_addr: MaybeRelocatable
        if instruction.dst_register is Register.AP:
            base_addr = self.ap
        elif instruction.dst_register is Register.FP:
            base_addr = self.fp
        else:
            raise NotImplementedError("Invalid dst_register value")
        return (base_addr + instruction.off0) % self.prime

    def compute_op0_addr(self, instruction: Instruction):
        base_addr: MaybeRelocatable
        if instruction.op0_register is Register.AP:
            base_addr = self.ap
        elif instruction.op0_register is Register.FP:
            base_addr = self.fp
        else:
            raise NotImplementedError("Invalid op0_register value")
        return (base_addr + instruction.off1) % self.prime

    def compute_op1_addr(self, instruction: Instruction, op0: Optional[MaybeRelocatable]):
        base_addr: MaybeRelocatable
        if instruction.op1_addr is Instruction.Op1Addr.FP:
            base_addr = self.fp
        elif instruction.op1_addr is Instruction.Op1Addr.AP:
            base_addr = self.ap
        elif instruction.op1_addr is Instruction.Op1Addr.IMM:
            assert instruction.off2 == 1, "In immediate mode, off2 should be 1."
            base_addr = self.pc
        elif instruction.op1_addr is Instruction.Op1Addr.OP0:
            assert op0 is not None, "op0 must be known in double dereference."
            base_addr = op0
        else:
            raise NotImplementedError("Invalid op1_register value")
        return (base_addr + instruction.off2) % self.prime


class VirtualMachine(VirtualMachineBase):
    run_context: RunContext

    def __init__(
        self,
        program: ProgramBase,
        run_context: RunContext,
        hint_locals: Dict[str, Any],
        static_locals: Optional[Dict[str, Any]] = None,
        builtin_runners: Optional[Dict[str, BuiltinRunner]] = None,
        program_base: Optional[MaybeRelocatable] = None,
    ):
        """
        See documentation in VirtualMachineBase.

        program_base - The pc of the first instruction in program (default is run_context.pc).
        """
        self.run_context = copy.copy(run_context)  # Shallow copy.
        if program_base is None:
            program_base = run_context.pc
        if builtin_runners is None:
            builtin_runners = {}

        super().__init__(
            program=program,
            run_context=self.run_context,
            hint_locals=hint_locals,
            static_locals=static_locals,
            builtin_runners=builtin_runners,
            program_base=program_base,
        )

        # A set to track the memory addresses accessed by actual Cairo instructions (as opposed to
        # hints), necessary for accurate counting of memory holes.
        self.accessed_addresses: Set[MaybeRelocatable] = {
            program_base + i for i in range(len(self.program.data))
        }

        self.trace: List[TraceEntry[MaybeRelocatable]] = []

        # Current step.
        self.current_step = 0

        # This flag can be set to true by hints to avoid the execution of the current step in
        # step() (so that only the hint will be performed, but nothing else will happen).
        self.skip_instruction_execution = False

    def update_registers(self, instruction: Instruction, operands: Operands):
        # Update fp.
        if instruction.fp_update is Instruction.FpUpdate.AP_PLUS2:
            self.run_context.fp = self.run_context.ap + 2
        elif instruction.fp_update is Instruction.FpUpdate.DST:
            self.run_context.fp = operands.dst
        elif instruction.fp_update is not Instruction.FpUpdate.REGULAR:
            raise NotImplementedError("Invalid fp_update value")

        # Update ap.
        if instruction.ap_update is Instruction.ApUpdate.ADD:
            if operands.res is None:
                raise NotImplementedError("Res.UNCONSTRAINED cannot be used with ApUpdate.ADD")
            self.run_context.ap += operands.res % self.prime
        elif instruction.ap_update is Instruction.ApUpdate.ADD1:
            self.run_context.ap += 1
        elif instruction.ap_update is Instruction.ApUpdate.ADD2:
            self.run_context.ap += 2
        elif instruction.ap_update is not Instruction.ApUpdate.REGULAR:
            raise NotImplementedError("Invalid ap_update value")
        self.run_context.ap = self.run_context.ap % self.prime

        # Update pc.
        # The pc update should be done last so that we will have the correct pc in case of an
        # exception during one of the updates above.
        if instruction.pc_update is Instruction.PcUpdate.REGULAR:
            self.run_context.pc += instruction.size
        elif instruction.pc_update is Instruction.PcUpdate.JUMP:
            if operands.res is None:
                raise NotImplementedError("Res.UNCONSTRAINED cannot be used with PcUpdate.JUMP")
            self.run_context.pc = operands.res
        elif instruction.pc_update is Instruction.PcUpdate.JUMP_REL:
            if operands.res is None:
                raise NotImplementedError("Res.UNCONSTRAINED cannot be used with PcUpdate.JUMP_REL")
            if not isinstance(operands.res, int):
                raise PureValueError("jmp rel", operands.res)
            self.run_context.pc += operands.res
        elif instruction.pc_update is Instruction.PcUpdate.JNZ:
            if self.is_zero(operands.dst):
                self.run_context.pc += instruction.size
            else:
                self.run_context.pc += operands.op1
        else:
            raise NotImplementedError("Invalid pc_update value")
        self.run_context.pc = self.run_context.pc % self.prime

    def deduce_op0(
        self,
        instruction: Instruction,
        dst: Optional[MaybeRelocatable],
        op1: Optional[MaybeRelocatable],
    ) -> Tuple[Optional[MaybeRelocatable], Optional[MaybeRelocatable]]:
        """
        Returns a tuple (deduced_op0, deduced_res).
        Deduces the value of op0 if possible (based on dst and op1). Otherwise, returns None.
        If res was already deduced, returns its deduced value as well.
        """
        if instruction.opcode is Instruction.Opcode.CALL:
            return self.run_context.pc + instruction.size, None
        elif instruction.opcode is Instruction.Opcode.ASSERT_EQ:
            if (instruction.res is Instruction.Res.ADD) and (dst is not None) and (op1 is not None):
                return (dst - op1) % self.prime, dst  # type: ignore
            elif (
                (instruction.res is Instruction.Res.MUL)
                and isinstance(dst, int)
                and isinstance(op1, int)
                and op1 != 0
            ):
                return div_mod(dst, op1, self.prime), dst
        return None, None

    def deduce_op1(
        self,
        instruction: Instruction,
        dst: Optional[MaybeRelocatable],
        op0: Optional[MaybeRelocatable],
    ) -> Tuple[Optional[MaybeRelocatable], Optional[MaybeRelocatable]]:
        """
        Returns a tuple (deduced_op1, deduced_res).
        Deduces the value of op1 if possible (based on dst and op0). Otherwise, returns None.
        If res was already deduced, returns its deduced value as well.
        """
        if instruction.opcode is Instruction.Opcode.ASSERT_EQ:
            if (instruction.res is Instruction.Res.OP1) and (dst is not None):
                return dst, dst
            elif (
                (instruction.res is Instruction.Res.ADD) and (dst is not None) and (op0 is not None)
            ):
                return (dst - op0) % self.prime, dst  # type: ignore
            elif (
                (instruction.res is Instruction.Res.MUL)
                and isinstance(dst, int)
                and isinstance(op0, int)
                and op0 != 0
            ):
                return div_mod(dst, op0, self.prime), dst
        return None, None

    def compute_res(
        self,
        instruction: Instruction,
        op0: MaybeRelocatable,
        op1: MaybeRelocatable,
    ) -> Optional[MaybeRelocatable]:
        """
        Computes the value of res if possible.
        """
        if instruction.res is Instruction.Res.OP1:
            return op1
        elif instruction.res is Instruction.Res.ADD:
            return (op0 + op1) % self.prime
        elif instruction.res is Instruction.Res.MUL:
            if isinstance(op0, RelocatableValue) or isinstance(op1, RelocatableValue):
                raise PureValueError("*", op0, op1)
            return (op0 * op1) % self.prime
        elif instruction.res is Instruction.Res.UNCONSTRAINED:
            # In this case res should be the inverse of dst.
            # For efficiency, we do not compute it here.
            return None
        else:
            raise NotImplementedError("Invalid res value")

    def compute_operands(self, instruction: Instruction) -> Tuple[Operands, List[int]]:
        """
        Computes the values of the operands. Deduces dst if needed.
        Returns:
          operands - an Operands instance with the values of the operands.
          mem_addresses - the memory addresses for the 3 memory units used (dst, op0, op1).
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
            res = self.compute_res(instruction, op0, op1)

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

        return (
            Operands(dst=dst, op0=op0, op1=op1, res=res),
            [dst_addr, op0_addr, op1_addr],
        )

    def is_zero(self, value):
        """
        Returns True if value is zero (used for jnz instructions).
        This function can be overridden by subclasses.
        """
        if isinstance(value, int):
            return value == 0

        if isinstance(value, RelocatableValue) and value.offset >= 0:
            return False
        raise PureValueError("jmp != 0", value)

    def is_integer_value(self, value):
        """
        Returns True if value is integer rather than relocatable.
        This function can be overridden by subclasses.
        """
        return isinstance(value, int)

    @staticmethod
    @lru_cache(None)
    def decode_instruction(encoded_inst: int, imm: Optional[int] = None) -> Instruction:
        return decode_instruction(encoded_inst, imm)

    def decode_current_instruction(self) -> Instruction:
        try:
            instruction_encoding, imm = self.run_context.get_instruction_encoding()
            instruction = self.decode_instruction(instruction_encoding, imm)
        except Exception as exc:
            raise self.as_vm_exception(exc) from None

        return instruction

    def opcode_assertions(self, instruction: Instruction, operands: Operands):
        if instruction.opcode is Instruction.Opcode.ASSERT_EQ:
            if operands.res is None:
                raise NotImplementedError("Res.UNCONSTRAINED cannot be used with Opcode.ASSERT_EQ")
            if operands.dst != operands.res and not self.check_eq(operands.dst, operands.res):
                raise Exception(
                    f"An ASSERT_EQ instruction failed: {operands.dst} != {operands.res}."
                )
        elif instruction.opcode is Instruction.Opcode.CALL:
            return_pc = self.run_context.pc + instruction.size
            if operands.op0 != return_pc and not self.check_eq(operands.op0, return_pc):
                raise Exception(
                    "Call failed to write return-pc (inconsistent op0): "
                    + f"{operands.op0} != {return_pc}. Did you forget to increment ap?"
                )
            return_fp = self.run_context.fp
            if operands.dst != return_fp and not self.check_eq(operands.dst, return_fp):
                raise Exception(
                    "Call failed to write return-fp (inconsistent dst): "
                    + f"{operands.dst} != {return_fp}. Did you forget to increment ap?"
                )
        elif instruction.opcode in [Instruction.Opcode.RET, Instruction.Opcode.NOP]:
            # Nothing to check.
            pass
        else:
            raise NotImplementedError(f"Unsupported opcode {instruction.opcode}.")

    def run_instruction(self, instruction):
        try:
            # Compute operands.
            operands, operands_mem_addresses = self.compute_operands(instruction)
        except Exception as exc:
            raise self.as_vm_exception(exc) from None

        try:
            # Opcode assertions.
            self.opcode_assertions(instruction, operands)
        except Exception as exc:
            raise self.as_vm_exception(exc) from None

        # Write to trace.
        self.trace.append(
            TraceEntry(
                pc=self.run_context.pc,
                ap=self.run_context.ap,
                fp=self.run_context.fp,
            )
        )

        self.accessed_addresses.update(operands_mem_addresses)
        self.accessed_addresses.add(self.run_context.pc)

        try:
            # Update registers.
            self.update_registers(instruction, operands)
        except Exception as exc:
            raise self.as_vm_exception(exc) from None

        self.current_step += 1

    def step(self):
        self.skip_instruction_execution = False
        # Execute hints.
        for hint_index, hint in enumerate(self.hints.get(self.run_context.pc, [])):
            exec_locals = self.exec_scopes[-1]
            exec_locals["memory"] = memory = self.validated_memory
            exec_locals["ap"] = ap = self.run_context.ap
            exec_locals["fp"] = fp = self.run_context.fp
            exec_locals["pc"] = pc = self.run_context.pc
            exec_locals["current_step"] = self.current_step
            exec_locals["ids"] = hint.consts(pc, ap, fp, memory)

            exec_locals["vm_load_program"] = self.load_program
            exec_locals["vm_enter_scope"] = self.enter_scope
            exec_locals["vm_exit_scope"] = self.exit_scope
            exec_locals.update(self.static_locals)

            self.exec_hint(hint.compiled, exec_locals, hint_index=hint_index)

            # Clear ids (which will be rewritten by the next hint anyway) to make the VM instance
            # smaller and faster to copy.
            del exec_locals["ids"]
            del exec_locals["memory"]

            if self.skip_instruction_execution:
                return

        # Decode.
        instruction = self.decode_current_instruction()

        # Run.
        self.run_instruction(instruction)
