from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple, Type, TypeVar, Union

from starkware.cairo.lang.builtins.bitwise.bitwise_builtin_runner import BitwiseBuiltinRunner
from starkware.cairo.lang.builtins.hash.hash_builtin_runner import HashBuiltinRunner
from starkware.cairo.lang.builtins.range_check.range_check_builtin_runner import (
    RangeCheckBuiltinRunner,
)
from starkware.cairo.lang.builtins.signature.signature_builtin_runner import SignatureBuiltinRunner
from starkware.cairo.lang.compiler.cairo_compile import (
    compile_cairo,
    compile_cairo_files,
    get_module_reader,
)
from starkware.cairo.lang.compiler.debug_info import DebugInfo
from starkware.cairo.lang.compiler.expression_simplifier import to_field_element
from starkware.cairo.lang.compiler.preprocessor.default_pass_manager import default_pass_manager
from starkware.cairo.lang.compiler.preprocessor.preprocessor import Preprocessor
from starkware.cairo.lang.compiler.program import Program, ProgramBase
from starkware.cairo.lang.instances import LAYOUTS
from starkware.cairo.lang.vm.builtin_runner import BuiltinRunner, InsufficientAllocatedCells
from starkware.cairo.lang.vm.cairo_pie import (
    CairoPie,
    CairoPieMetadata,
    ExecutionResources,
    SegmentInfo,
)
from starkware.cairo.lang.vm.crypto import pedersen_hash, verify_ecdsa
from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.memory_segments import MemorySegmentManager
from starkware.cairo.lang.vm.output_builtin_runner import OutputBuiltinRunner
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue, relocate_value
from starkware.cairo.lang.vm.trace_entry import relocate_trace
from starkware.cairo.lang.vm.utils import (
    MemorySegmentAddresses,
    MemorySegmentRelocatableAddresses,
    ResourcesError,
    RunResources,
)
from starkware.cairo.lang.vm.vm import RunContext, VirtualMachine, get_perm_range_check_limits
from starkware.crypto.signature.signature import inv_mod_curve_size
from starkware.python.math_utils import next_power_of_2, safe_div
from starkware.python.utils import WriteOnceDict
from starkware.starkware_utils.subsequence import is_subsequence

TCairoRunner = TypeVar("TCairoRunner", bound="CairoRunner")


def verify_ecdsa_sig(public_key, msg, signature) -> bool:
    """
    Returns True if the given ECDSA signature is valid for the given public key and message hash.
    Signature is a pair (r, s).
    """
    r, s = signature
    return verify_ecdsa(msg, r, s, public_key)


def process_ecdsa(public_key, msg, signature):
    """
    Returns an (r, s) ECDSA signature in the {'r': hex(r), 'w': hex(s^-1)} format, as expected by
    the ECDSA component.
    """
    r, s = signature
    return {"r": hex(r), "w": hex(inv_mod_curve_size(s))}


class CairoRunner:
    def __init__(
        self,
        program: ProgramBase,
        layout: str = "plain",
        memory: MemoryDict = None,
        proof_mode: Optional[bool] = None,
        allow_missing_builtins: Optional[bool] = None,
    ):
        self.program = program
        self.layout = layout
        self.builtin_runners: Dict[str, BuiltinRunner] = {}
        self.original_steps = None
        self.proof_mode = False if proof_mode is None else proof_mode
        self.allow_missing_builtins = (
            False if allow_missing_builtins is None else allow_missing_builtins
        )

        instance = LAYOUTS[self.layout]

        if not allow_missing_builtins:
            non_existing_builtins = set(self.program.builtins) - set(instance.builtins.keys())
            assert (
                len(non_existing_builtins) == 0
            ), f'Builtins {non_existing_builtins} are not present in layout "{self.layout}"'

        builtin_factories = dict(
            output=lambda name, included: OutputBuiltinRunner(included=included),
            pedersen=lambda name, included: HashBuiltinRunner(
                name=name,
                included=included,
                ratio=instance.builtins["pedersen"].ratio,
                hash_func=pedersen_hash,
            ),
            range_check=lambda name, included: RangeCheckBuiltinRunner(
                included=included,
                ratio=instance.builtins["range_check"].ratio,
                inner_rc_bound=2 ** 16,
                n_parts=instance.builtins["range_check"].n_parts,
            ),
            ecdsa=lambda name, included: SignatureBuiltinRunner(
                name=name,
                included=included,
                ratio=instance.builtins["ecdsa"].ratio,
                process_signature=process_ecdsa,
                verify_signature=verify_ecdsa_sig,
            ),
            bitwise=lambda name, included: BitwiseBuiltinRunner(
                included=included, bitwise_builtin=instance.builtins["bitwise"]
            ),
        )

        for name in instance.builtins:
            factory = builtin_factories.get(name)
            assert factory is not None, f"The {name} builtin is not supported."
            included = name in self.program.builtins
            # In proof mode all the builtin_runners are required.
            if included or self.proof_mode:
                self.builtin_runners[f"{name}_builtin"] = factory(  # type: ignore
                    name=name, included=included
                )

        supported_builtin_list = list(builtin_factories.keys())
        err_msg = (
            f"The builtins specified by the %builtins directive must be subsequence of "
            f"{supported_builtin_list}. Got {self.program.builtins}."
        )
        assert is_subsequence(self.program.builtins, supported_builtin_list), err_msg

        self.memory = memory if memory is not None else MemoryDict()
        self.segments = MemorySegmentManager(memory=self.memory, prime=self.program.prime)
        self.segment_offsets: Optional[Dict[int, int]] = None
        self.final_pc: Optional[RelocatableValue] = None

        # Flags used to ensure a safe use.
        self._run_ended: bool = False
        self._segments_finalized: bool = False
        # A set of memory addresses accessed by the VM, after relocation of temporary segments into
        # real ones.
        self.accessed_addresses: Optional[Set[RelocatableValue]] = None

    @classmethod
    def from_file(
        cls: Type[TCairoRunner],
        filename: str,
        prime: int,
        layout: str = "plain",
        remove_hints: bool = False,
        remove_builtins: bool = False,
        memory: MemoryDict = None,
        preprocessor_cls: Type[Preprocessor] = Preprocessor,
        proof_mode: Optional[bool] = None,
    ) -> TCairoRunner:
        module_reader = get_module_reader(cairo_path=[])
        program = compile_cairo_files(
            files=[filename],
            debug_info=True,
            pass_manager=default_pass_manager(
                prime=prime, read_module=module_reader.read, preprocessor_cls=preprocessor_cls
            ),
        )
        if remove_hints:
            program.hints = {}
        if remove_builtins:
            program.builtins = []
        return cls(program, layout, memory=memory, proof_mode=proof_mode)

    # Functions for the running sequence.

    def initialize_segments(self, program_base=None):
        # Program segment.
        self.program_base = self.segments.add() if program_base is None else program_base

        # Execution segment.
        self.execution_base = self.segments.add()

        # Builtin segments.
        for builtin_runner in self.builtin_runners.values():
            builtin_runner.initialize_segments(self)

    def initialize_main_entrypoint(self):
        """
        Initializes state for running a program from the main() entrypoint.
        If self.proof_mode == True, the execution starts from the start label rather then
        the main() function.

        Returns the value of the program counter after returning from main.
        """
        self.execution_public_memory: List[int] = []

        stack: List[MaybeRelocatable] = []
        for builtin_name in self.program.builtins:
            builtin_runner = self.builtin_runners.get(f"{builtin_name}_builtin")
            if builtin_runner is None:
                assert self.allow_missing_builtins, "Missing builtin."
                stack += [0]
            else:
                stack += builtin_runner.initial_stack()

        if self.proof_mode:
            # Add the dummy last fp and pc to the public memory, so that the verifier can enforce
            # [fp - 2] = fp.
            stack_prefix: List[MaybeRelocatable] = [self.execution_base + 2, 0]
            stack = stack_prefix + stack
            self.execution_public_memory = list(range(len(stack)))

            assert isinstance(
                self.program, Program
            ), "--proof_mode cannot be used with a StrippedProgram."
            self.initialize_state(self.program.start, stack)
            self.initial_fp = self.initial_ap = self.execution_base + 2
            return self.program_base + self.program.get_label("__end__")
        else:
            return_fp = self.segments.add()

            main = self.program.main
            assert main is not None, "Missing main()."
            return self.initialize_function_entrypoint(main, stack, return_fp=return_fp)

    def initialize_function_entrypoint(
        self,
        entrypoint: Union[str, int],
        args: Sequence[MaybeRelocatable],
        return_fp: MaybeRelocatable = 0,
    ):
        end = self.segments.add()
        stack = list(args) + [return_fp, end]
        self.initialize_state(entrypoint, stack)
        self.initial_fp = self.initial_ap = self.execution_base + len(stack)
        self.final_pc = end
        return end

    def initialize_state(self, entrypoint: Union[str, int], stack: Sequence[MaybeRelocatable]):
        self.initial_pc = self.program_base + self._to_pc(entrypoint)
        # Load program.
        self.load_data(self.program_base, self.program.data)
        # Load stack.
        self.load_data(self.execution_base, stack)

    def initialize_vm(
        self, hint_locals, static_locals: Optional[Dict[str, Any]] = None, vm_class=VirtualMachine
    ):
        context = RunContext(
            pc=self.initial_pc,
            ap=self.initial_ap,
            fp=self.initial_fp,
            memory=self.memory,
            prime=self.program.prime,
        )

        if static_locals is None:
            static_locals = {}

        self.vm = vm_class(
            self.program,
            context,
            hint_locals=hint_locals,
            static_locals=dict(segments=self.segments, **static_locals),
            builtin_runners=self.builtin_runners,
            program_base=self.program_base,
        )

        for builtin_runner in self.builtin_runners.values():
            builtin_runner.add_validation_rules(self)
            builtin_runner.add_auto_deduction_rules(self)

        self.vm.validate_existing_memory()

    def run_until_label(
        self, label_or_pc: Union[str, int], run_resources: Optional[RunResources] = None
    ):
        """
        Runs the VM until label is reached, and stops right before that instruction is executed.
        'label_or_pc' should be either a label string or an integer offset from the program_base.
        """
        label = self._to_pc(label_or_pc)
        self.run_until_pc(self.program_base + label, run_resources=run_resources)

    def run_until_pc(self, addr: MaybeRelocatable, run_resources: Optional[RunResources] = None):
        """
        Runs the VM until pc reaches 'addr', and stop right before that instruction is executed.
        """
        if run_resources is None:
            run_resources = RunResources(n_steps=None)

        while self.vm.run_context.pc != addr and not run_resources.consumed:
            self.vm_step()
            run_resources.consume_step()

        if self.vm.run_context.pc != addr:
            raise self.vm.as_vm_exception(
                ResourcesError("Error: End of program was not reached"), with_traceback=False
            )

    def vm_step(self):
        if self.vm.run_context.pc == self.final_pc:
            raise self.vm.as_vm_exception(
                Exception("Error: Execution reached the end of the program."),
                with_traceback=False,
            )
        self.vm.step()

    def run_for_steps(self, steps: int):
        """
        Runs the VM for 'steps' steps.
        """
        for _ in range(steps):
            self.vm_step()

    def run_until_steps(self, steps: int):
        """
        Runs the VM (not necessarily from step 0) until 'steps' steps have been run.
        Does nothing if 'steps' steps or more have been run already.
        """
        self.run_for_steps(max(steps - self.vm.current_step, 0))

    def run_until_next_power_of_2(self):
        """
        Runs the VM until the step count reaches the next power of 2.
        """
        self.run_until_steps(next_power_of_2(self.vm.current_step))

    def end_run(self, disable_trace_padding: bool = True, disable_finalize_all: bool = False):
        assert not self._run_ended, "end_run called twice."

        self.accessed_addresses = {
            self.vm_memory.relocate_value(addr) for addr in self.vm.accessed_addresses
        }
        self.vm_memory.relocate_memory()
        self.vm.end_run()

        if disable_finalize_all:
            # For tests.
            return

        # Freeze to enable caching; No changes in memory should be made from now on.
        self.vm_memory.freeze()
        # Deduce the size of each segment from its usage.
        self.segments.compute_effective_sizes()

        if self.proof_mode and not disable_trace_padding:
            self.run_until_next_power_of_2()
            while not self.check_used_cells():
                self.run_for_steps(1)
                self.run_until_next_power_of_2()

        self._run_ended = True

    def read_return_values(self):
        """
        Reads builtin return values (end pointers) and adds them to the public memory.
        Note: end_run() must precede a call to this method.
        """
        assert self._run_ended, "Run must be ended before calling read_return_values."

        pointer = self.vm.run_context.ap
        for builtin_name in self.program.builtins[::-1]:
            builtin_runner = self.builtin_runners.get(f"{builtin_name}_builtin")
            if builtin_runner is None:
                assert self.allow_missing_builtins, "Missing builtin."
                pointer -= 1
                assert (
                    self.vm_memory[pointer] == 0
                ), f'The stop pointer of the missing builtin "{builtin_name}" must be 0.'
            else:
                pointer = builtin_runner.final_stack(self, pointer)

        assert (
            not self._segments_finalized
        ), "Cannot add the return values to the public memory after segment finalization."
        # Add return values to public memory.
        self.execution_public_memory += list(
            range(pointer - self.execution_base, self.vm.run_context.ap - self.execution_base)
        )

    def mark_as_accessed(self, address: RelocatableValue, size: int):
        """
        Marks the memory range [address, address + size) as accessed.

        This is useful when a memory range is not accessed in a partial scenario
        but is known to be accessed in the real use case.

        For example, a StarkNet contract entry point might not use all the information provided by
        the StarkNet OS.
        """
        assert self.accessed_addresses is not None
        for i in range(size):
            self.accessed_addresses.add(address + i)

    def check_used_cells(self):
        """
        Returns True if there are enough allocated cells for the builtins.
        If not, the number of steps should be increased or a different layout should be used.
        """
        try:
            for builtin_runner in self.builtin_runners.values():
                builtin_runner.get_used_cells_and_allocated_size(self)
            self.check_range_check_usage()
            self.check_memory_usage()
            self.check_diluted_check_usage()
        except InsufficientAllocatedCells as e:
            print(f"Warning: {e} Increasing number of steps.")
            return False
        return True

    def finalize_segments(self):
        """
        Finalizes the segments.
        Note:
        1.  end_run() must precede a call to this method.
        2.  Call read_return_values() *before* finalize_segments(), otherwise the return values
            will not be included in the public memory.
        """
        if self._segments_finalized:
            return

        assert self._run_ended, "Run must be ended before calling finalize_segments."
        self.segments.finalize(
            self.program_base.segment_index,
            size=len(self.program.data),
            public_memory=[(i, 0) for i in range(len(self.program.data))],
        )
        self.segments.finalize(
            self.execution_base.segment_index,
            public_memory=[
                (x + self.execution_base.offset, 0) for x in self.execution_public_memory
            ],
        )

        for builtin_runner in self.builtin_runners.values():
            builtin_runner.finalize_segments(self)

        self._segments_finalized = True

    def finalize_segments_by_cairo_pie(self, cairo_pie: CairoPie):
        for segment_info in cairo_pie.metadata.all_segments():
            self.segments.finalize(segment_info.index, segment_info.size)

    def get_air_private_input(self):
        return {
            name: value
            for builtin_runner in self.builtin_runners.values()
            for name, value in builtin_runner.air_private_input(self).items()
        }

    def get_perm_range_check_limits(self):
        rc_min, rc_max = get_perm_range_check_limits(self.vm.trace, self.vm_memory)
        for builtin_runner in self.builtin_runners.values():
            range_check_usage = builtin_runner.get_range_check_usage(self)
            if range_check_usage is None:
                continue
            rc_min = min(rc_min, range_check_usage[0])
            rc_max = max(rc_max, range_check_usage[1])
        return rc_min, rc_max

    def check_range_check_usage(self):
        """
        Checks that there are enough trace cells to fill the entire range checks range.
        """
        rc_min, rc_max = self.get_perm_range_check_limits()
        instance = LAYOUTS[self.layout]
        rc_units_used_by_builtins = sum(
            builtin_runner.get_used_perm_range_check_units(self)
            for builtin_runner in self.builtin_runners.values()
        )
        # Out of the range check units allowed per step three are used for the instruction.
        unused_rc_units = (instance.rc_units - 3) * self.vm.current_step - rc_units_used_by_builtins
        rc_usage_upper_bound = rc_max - rc_min
        if unused_rc_units < rc_usage_upper_bound:
            raise InsufficientAllocatedCells(
                f"There are only {unused_rc_units} cells to fill the range checks holes, but "
                f"potentially {rc_usage_upper_bound} are required."
            )

    def get_memory_holes(self):
        assert self.accessed_addresses is not None
        # Collect memory addresses that are accessed by the builtin (and therefore are not counted
        # as memory holes).
        builtin_accessed_addresses = {
            addr
            for builtin_runner in self.builtin_runners.values()
            for addr in builtin_runner.get_memory_accesses(self)
        }
        return self.segments.get_memory_holes(
            accessed_addresses=self.accessed_addresses | builtin_accessed_addresses
        )

    def check_memory_usage(self):
        """
        Checks that there are enough trace cells to fill the entire memory range.
        """
        instance = LAYOUTS[self.layout]
        builtins_memory_units = sum(
            builtin_runner.get_allocated_memory_units(self)
            for builtin_runner in self.builtin_runners.values()
        )
        # Out of the memory units available per step, a fraction is used for public memory, and
        # four are used for the instruction.
        total_memory_units = instance.memory_units_per_step * self.vm.current_step
        public_memory_units = safe_div(total_memory_units, instance.public_memory_fraction)
        instruction_memory_units = 4 * self.vm.current_step
        unused_memory_units = total_memory_units - (
            public_memory_units + instruction_memory_units + builtins_memory_units
        )
        memory_address_holes = self.get_memory_holes()
        if unused_memory_units < memory_address_holes:
            raise InsufficientAllocatedCells(
                f"There are only {unused_memory_units} cells to fill the memory address holes, but "
                f"{memory_address_holes} are required."
            )

    def check_diluted_check_usage(self):
        """
        Checks that there are enough trace cells to fill the entire diluted checks.
        """
        instance = LAYOUTS[self.layout]
        if instance.diluted_pool_instance_def is None:
            return

        diluted_units_used_by_builtins = sum(
            builtin_runner.get_used_diluted_check_units(
                diluted_spacing=instance.diluted_pool_instance_def.spacing,
                diluted_n_bits=instance.diluted_pool_instance_def.n_bits,
            )
            * safe_div(
                self.vm.current_step,
                getattr(builtin_runner, "ratio", 1),
            )
            for builtin_runner in self.builtin_runners.values()
        )

        diluted_units = instance.diluted_pool_instance_def.units_per_step * self.vm.current_step
        unused_diluted_units = diluted_units - diluted_units_used_by_builtins
        diluted_usage_upper_bound = 2 ** instance.diluted_pool_instance_def.n_bits
        if unused_diluted_units < diluted_usage_upper_bound:
            raise InsufficientAllocatedCells(
                f"There are only {unused_diluted_units} cells to fill the diluted check holes, but "
                f"potentially {diluted_usage_upper_bound} are required."
            )

    # Helper functions.

    @property
    def vm_memory(self) -> MemoryDict:
        return self.memory

    def _to_pc(self, label_or_pc: Union[str, int]) -> int:
        """
        If the input is a string, treat it as a label and converts it to a PC.
        Otherwise, return it unchanged.
        """
        if isinstance(label_or_pc, str):
            assert isinstance(
                self.program, Program
            ), "Label name cannot be used with a StrippedProgram."
            return self.program.get_label(label_or_pc)
        return label_or_pc

    def load_data(
        self, ptr: MaybeRelocatable, data: Sequence[MaybeRelocatable]
    ) -> MaybeRelocatable:
        """
        Writes data into the memory at address ptr and returns the first address after the data.
        """
        return self.segments.load_data(ptr, data)

    def gen_arg(self, arg, apply_modulo_to_args=True):
        """
        Converts args to Cairo-friendly ones.
        If an argument is Iterable it is replaced by a pointer to a new segment containing the items
        in the Iterable arg (recursively).
        If apply_modulo_to_args=True, all the integers are taken modulo the program's prime.
        """
        return self.segments.gen_arg(arg=arg, apply_modulo_to_args=apply_modulo_to_args)

    def relocate_value(self, value: MaybeRelocatable) -> int:
        assert self.segment_offsets is not None, "segment_offsets is not initialized."
        relocated = relocate_value(
            value=value, segment_offsets=self.segment_offsets, prime=self.program.prime
        )
        assert isinstance(relocated, int)
        return relocated

    def get_segment_offsets(self) -> Dict[int, int]:
        assert self.segment_offsets is not None, "segment_offsets is not initialized."
        return self.segment_offsets

    def relocate(self):
        self.segment_offsets = self.segments.relocate_segments()

        initializer: Mapping[MaybeRelocatable, MaybeRelocatable] = {
            self.relocate_value(addr): self.relocate_value(value)
            for addr, value in self.vm_memory.items()
        }
        self.relocated_memory = MemoryDict(initializer)
        self.relocated_trace = relocate_trace(
            self.vm.trace, self.segment_offsets, self.program.prime
        )
        for builtin_runner in self.builtin_runners.values():
            builtin_runner.relocate(self.relocate_value)

    def get_relocated_debug_info(self):
        return DebugInfo(
            instruction_locations={
                self.relocate_value(addr): location_info
                for addr, location_info in self.vm.instruction_debug_info.items()
            },
            file_contents=self.vm.debug_file_contents,
        )

    def get_memory_segment_addresses(self) -> Dict[str, MemorySegmentAddresses]:
        def get_segment_addresses(
            name: str, segment_addresses: MemorySegmentRelocatableAddresses
        ) -> MemorySegmentAddresses:
            stop_ptr = (
                segment_addresses.stop_ptr
                if name in self.program.builtins
                else segment_addresses.begin_addr
            )

            assert stop_ptr is not None, f"The {name} builtin stop pointer was not set."
            return MemorySegmentAddresses(
                begin_addr=self.relocate_value(segment_addresses.begin_addr),
                stop_ptr=self.relocate_value(stop_ptr),
            )

        return {
            name: get_segment_addresses(name, segment_addresses)
            for builtin_runner in self.builtin_runners.values()
            for name, segment_addresses in builtin_runner.get_memory_segment_addresses(self).items()
        }

    def print_memory(self, relocated: bool):
        print("Addr  Value")
        print("-----------")
        old_addr = -1
        memory = self.relocated_memory if relocated else self.vm_memory
        for addr in sorted(memory.keys()):
            val = memory[addr]
            if addr != old_addr + 1:
                print("\u22ee")
            if isinstance(val, int):
                val = to_field_element(val=val, prime=self.program.prime)
            print(f"{addr:<5} {val}")
            old_addr = addr
        print()

    def print_output(self, output_callback=to_field_element):
        if "output_builtin" not in self.builtin_runners:
            return

        output_runner = self.builtin_runners["output_builtin"]
        assert isinstance(output_runner, OutputBuiltinRunner)
        print("Program output:")
        _, size = output_runner.get_used_cells_and_allocated_size(self)
        for i in range(size):
            val = self.vm_memory.get(output_runner.base + i)
            if val is not None:
                print(f"  {output_callback(val=val, prime=self.program.prime)}")
            else:
                print("  <missing>")

        print()

    def print_info(self, relocated: bool):
        print(self.get_info(relocated=relocated))

    def get_info(self, relocated: bool) -> str:
        pc, ap, fp = self.vm.run_context.pc, self.vm.run_context.ap, self.vm.run_context.fp
        if relocated:
            pc = self.relocate_value(pc)
            ap = self.relocate_value(ap)
            fp = self.relocate_value(fp)

        info = f"""\
Number of steps: {len(self.vm.trace)} {
    '' if self.original_steps is None else f'(originally, {self.original_steps})'}
Used memory cells: {len(self.vm_memory)}
Register values after execution:
pc = {pc}
ap = {ap}
fp = {fp}
"""
        return info

    def print_segment_relocation_table(self):
        if self.segment_offsets is not None:
            print("Segment relocation table:")
            for segment_index in range(self.segments.n_segments):
                print(f"{segment_index:<5} {self.segment_offsets[segment_index]}")

    def get_builtin_usage(self) -> str:
        if len(self.builtin_runners) == 0:
            return ""

        builtin_usage_str = "\nBuiltin usage:\n"
        for name, builtin_runner in self.builtin_runners.items():
            used, size = builtin_runner.get_used_cells_and_allocated_size(self)
            percentage = f"{used / size * 100:.2f}%" if size > 0 else "100%"
            builtin_usage_str += f"{name:<30s} {percentage:>7s} (used {used} cells)\n"

        return builtin_usage_str

    def print_builtin_usage(self):
        print(self.get_builtin_usage())

    def get_builtin_segments_info(self):
        builtin_segments: Dict[str, SegmentInfo] = {}
        for builtin in self.builtin_runners.values():
            for name, segment_addresses in builtin.get_memory_segment_addresses(self).items():
                begin_addr = segment_addresses.begin_addr
                assert isinstance(
                    begin_addr, RelocatableValue
                ), f"{name} segment begin_addr is not a RelocatableValue {begin_addr}."
                assert (
                    begin_addr.offset == 0
                ), f"Unexpected {name} segment begin_addr {begin_addr.offset}."
                assert segment_addresses.stop_ptr is not None, f"{name} segment stop ptr is None."
                segment_index = begin_addr.segment_index
                segment_size = segment_addresses.stop_ptr - begin_addr
                assert isinstance(segment_size, int)
                assert name not in builtin_segments, f"Builtin segment name collision: {name}."
                builtin_segments[name] = SegmentInfo(index=segment_index, size=segment_size)
        return builtin_segments

    def get_execution_resources(self) -> ExecutionResources:
        n_steps = len(self.vm.trace) if self.original_steps is None else self.original_steps
        n_memory_holes = self.get_memory_holes()
        builtin_instance_counter = {
            builtin_name: builtin_runner.get_used_instances(self)
            for builtin_name, builtin_runner in self.builtin_runners.items()
        }
        return ExecutionResources(
            n_steps=n_steps,
            n_memory_holes=n_memory_holes,
            builtin_instance_counter=builtin_instance_counter,
        )

    def get_cairo_pie(self) -> CairoPie:
        """
        Constructs and returns a CairoPie representing the current VM run.
        """
        builtin_segments = self.get_builtin_segments_info()
        known_segment_indices = WriteOnceDict()
        for segment_info in builtin_segments.values():
            known_segment_indices[segment_info.index] = None

        # Note that n_used_builtins might be smaller then len(builtin_segments).
        n_used_builtins = len(self.program.builtins)
        ret_fp, ret_pc = (
            self.vm_memory[self.execution_base + n_used_builtins + i] for i in range(2)
        )

        assert isinstance(ret_fp, RelocatableValue), f"Expecting a relocatable value got {ret_fp}."
        assert isinstance(ret_pc, RelocatableValue), f"Expecting a relocatable value got {ret_pc}."

        assert self.segments.get_segment_size(ret_fp.segment_index) == 0, (
            "Unexpected ret_fp_segment size "
            f"{self.segments.get_segment_size(ret_fp.segment_index)}"
        )
        assert self.segments.get_segment_size(ret_pc.segment_index) == 0, (
            "Unexpected ret_pc_segment size "
            f"{self.segments.get_segment_size(ret_pc.segment_index)}"
        )

        for addr in self.program_base, self.execution_base, ret_fp, ret_pc:
            assert addr.offset == 0, "Expecting a 0 offset."
            known_segment_indices[addr.segment_index] = None

        # Put all the remaining segments in extra_segments.
        extra_segments = [
            SegmentInfo(index=index, size=self.segments.get_segment_size(index))
            for index in range(self.segments.n_segments)
            if index not in known_segment_indices
        ]

        execution_size = self.vm.run_context.ap - self.execution_base
        cairo_pie_metadata = CairoPieMetadata(
            program=self.program.stripped(),
            program_segment=SegmentInfo(
                index=self.program_base.segment_index, size=len(self.program.data)
            ),
            execution_segment=SegmentInfo(
                index=self.execution_base.segment_index, size=execution_size
            ),
            ret_fp_segment=SegmentInfo(ret_fp.segment_index, size=0),
            ret_pc_segment=SegmentInfo(ret_pc.segment_index, size=0),
            builtin_segments=builtin_segments,
            extra_segments=extra_segments,
        )

        execution_resources = self.get_execution_resources()

        return CairoPie(
            metadata=cairo_pie_metadata,
            memory=self.vm.run_context.memory,
            additional_data={
                name: builtin.get_additional_data()
                for name, builtin in self.builtin_runners.items()
            },
            execution_resources=execution_resources,
        )


def get_runner_from_code(
    code: Union[str, Sequence[Tuple[str, str]]], layout: str, prime: int
) -> CairoRunner:
    """
    Given a code with some compile and run parameters (prime, layout, etc.), runs the code using
    Cairo runner and returns the runner.
    """
    program = compile_cairo(code=code, prime=prime, debug_info=True)
    return get_main_runner(program=program, hint_locals={}, layout=layout)


def get_main_runner(program: Program, hint_locals: Dict[str, Any], layout: str):
    """
    Runs a main-entrypoint program using Cairo runner and returns the runner.
    """
    runner = CairoRunner(program, layout=layout)
    runner.initialize_segments()
    end = runner.initialize_main_entrypoint()
    runner.initialize_vm(hint_locals=hint_locals)
    runner.run_until_pc(end)
    runner.end_run()
    runner.read_return_values()
    return runner
