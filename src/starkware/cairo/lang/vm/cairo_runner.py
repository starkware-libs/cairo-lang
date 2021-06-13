import functools
from typing import Any, Dict, List, Optional, Sequence, Tuple, Type, Union

from starkware.cairo.lang.builtins.hash.hash_builtin_runner import HashBuiltinRunner
from starkware.cairo.lang.builtins.range_check.range_check_builtin_runner import (
    RangeCheckBuiltinRunner)
from starkware.cairo.lang.builtins.signature.signature_builtin_runner import SignatureBuiltinRunner
from starkware.cairo.lang.compiler.cairo_compile import (
    compile_cairo, compile_cairo_files, get_module_reader)
from starkware.cairo.lang.compiler.debug_info import DebugInfo
from starkware.cairo.lang.compiler.expression_simplifier import to_field_element
from starkware.cairo.lang.compiler.preprocessor.default_pass_manager import default_pass_manager
from starkware.cairo.lang.compiler.preprocessor.preprocessor import Preprocessor
from starkware.cairo.lang.compiler.program import Program, ProgramBase
from starkware.cairo.lang.instances import LAYOUTS
from starkware.cairo.lang.vm.builtin_runner import BuiltinRunner, InsufficientAllocatedCells
from starkware.cairo.lang.vm.cairo_pie import (
    CairoPie, CairoPieMetadata, ExecutionResources, SegmentInfo)
from starkware.cairo.lang.vm.crypto import pedersen_hash, verify_ecdsa
from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.memory_segments import MemorySegmentManager, get_segment_used_size
from starkware.cairo.lang.vm.output_builtin_runner import OutputBuiltinRunner
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue, relocate_value
from starkware.cairo.lang.vm.trace_entry import relocate_trace
from starkware.cairo.lang.vm.utils import MemorySegmentAddresses
from starkware.cairo.lang.vm.vm import RunContext, VirtualMachine, get_perm_range_check_limits
from starkware.crypto.signature.signature import inv_mod_curve_size
from starkware.python.math_utils import next_power_of_2, safe_div
from starkware.python.utils import WriteOnceDict


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
    return {'r': hex(r), 'w': hex(inv_mod_curve_size(s))}


class CairoRunner:
    def __init__(
            self, program: ProgramBase, layout: str, memory: MemoryDict = None,
            proof_mode: Optional[bool] = None):
        self.program = program
        self.layout = layout
        self.builtin_runners: Dict[str, BuiltinRunner] = {}
        self.original_steps = None
        self.proof_mode = False if proof_mode is None else proof_mode

        # Reconstruct the builtin list to make sure there's no unexpected builtin and that builtins
        # appears in order.
        expected_builtin_list = []

        instance = LAYOUTS[self.layout]
        non_existing_builtins = set(self.program.builtins) - set(instance.builtins.keys())
        assert len(non_existing_builtins) == 0, \
            f'Builtins {non_existing_builtins} are not present in layout "{self.layout}"'

        if self.layout != 'plain':
            builtin_factories = {
                'output': lambda name, included: OutputBuiltinRunner(included=included),
                'pedersen': functools.partial(
                    HashBuiltinRunner, ratio=instance.builtins['pedersen'].ratio,
                    hash_func=pedersen_hash),
                'range_check': lambda name, included:
                    RangeCheckBuiltinRunner(
                        included=included, ratio=instance.builtins['range_check'].ratio,
                        inner_rc_bound=2 ** 16, n_parts=instance.builtins['range_check'].n_parts),
                'ecdsa': functools.partial(
                    SignatureBuiltinRunner, ratio=instance.builtins['ecdsa'].ratio,
                    process_signature=process_ecdsa, verify_signature=verify_ecdsa_sig),
            }

            for name, factory in builtin_factories.items():
                included = name in self.program.builtins
                # In proof mode all the builtin_runners are required.
                if included or self.proof_mode:
                    self.builtin_runners[f'{name}_builtin'] = factory(  # type: ignore
                        name=name, included=included)
                if included:
                    expected_builtin_list.append(name)

        assert expected_builtin_list == self.program.builtins, \
            f'Expected builtin list {expected_builtin_list} does not match {self.program.builtins}.'

        self.memory = memory if memory is not None else MemoryDict()
        self.segments = MemorySegmentManager(memory=self.memory, prime=self.program.prime)
        self.segment_offsets = None
        self.final_pc: Optional[RelocatableValue] = None

    @classmethod
    def from_file(
            cls, filename: str, prime: int, layout: str = 'plain',
            remove_hints: bool = False, remove_builtins: bool = False, memory: MemoryDict = None,
            preprocessor_cls: Type[Preprocessor] = Preprocessor,
            proof_mode: Optional[bool] = None) -> 'CairoRunner':
        module_reader = get_module_reader(cairo_path=[])
        program = compile_cairo_files(
            files=[filename],
            debug_info=True,
            pass_manager=default_pass_manager(
                prime=prime,
                read_module=module_reader.read,
                preprocessor_cls=preprocessor_cls))
        if remove_hints:
            program.hints = {}
        if remove_builtins:
            program.builtins = []
        return CairoRunner(program, layout, memory=memory, proof_mode=proof_mode)

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
        for builtin_runner in self.builtin_runners.values():
            stack += builtin_runner.initial_stack()

        if self.proof_mode:
            # Add the dummy last fp and pc to the public memory, so that the verifier can enforce
            # [fp - 2] = fp.
            stack = [self.execution_base + 2, 0] + stack
            self.execution_public_memory = list(range(len(stack)))

            assert isinstance(self.program, Program), \
                '--proof_mode cannot be used with a StrippedProgram.'
            self.initialize_state(self.program.start, stack)
            self.initial_fp = self.initial_ap = self.execution_base + 2
            return self.program_base + self.program.get_label('__end__')
        else:
            return_fp = self.segments.add()

            main = self.program.main
            assert main is not None, 'Missing main().'
            return self.initialize_function_entrypoint(
                main, stack, return_fp=return_fp)

    def initialize_function_entrypoint(
            self, entrypoint: Union[str, int], args: Sequence[MaybeRelocatable],
            return_fp: MaybeRelocatable = 0):
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
            self, hint_locals, static_locals: Optional[Dict[str, Any]] = None,
            vm_class=VirtualMachine):
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
            self.program, context, hint_locals=hint_locals,
            static_locals=dict(segments=self.segments, **static_locals),
            builtin_runners=self.builtin_runners,
            program_base=self.program_base,
        )

        for builtin_runner in self.builtin_runners.values():
            builtin_runner.add_validation_rules(self)
            builtin_runner.add_auto_deduction_rules(self)

        self.vm.validate_existing_memory()

    def run_until_label(self, label_or_pc: Union[str, int], max_steps: Optional[int] = None):
        """
        Runs the VM until label is reached, and stops right before that instruction is executed.
        'label_or_pc' should be either a label string or an integer offset from the program_base.
        """
        label = self._to_pc(label_or_pc)
        self.run_until_pc(self.program_base + label, max_steps=max_steps)

    def run_until_pc(self, addr: MaybeRelocatable, max_steps: Optional[int] = None):
        """
        Runs the VM until pc reaches 'addr', and stop right before that instruction is executed.
        """
        i = 0
        while self.vm.run_context.pc != addr and (max_steps is None or i < max_steps):
            self.vm_step()
            i += 1
        if self.vm.run_context.pc != addr:
            raise self.vm.as_vm_exception(
                Exception('Error: End of program was not reached'),
                self.vm.run_context.pc)

    def vm_step(self):
        if self.vm.run_context.pc == self.final_pc:
            raise self.vm.as_vm_exception(
                Exception('Error: Execution reached the end of the program.'),
                self.vm.run_context.pc)
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

    def end_run(self):
        self.vm_memory.relocate_memory()
        self.vm.end_run()

    def read_return_values(self):
        """
        Reads builtin return values (end pointers) and adds them to the public memory.
        """
        pointer = self.vm.run_context.ap
        for builtin_runner in list(self.builtin_runners.values())[::-1]:
            pointer = builtin_runner.final_stack(self, pointer)
        # Add return values to public memory.
        self.execution_public_memory += list(range(
            pointer - self.execution_base, self.vm.run_context.ap - self.execution_base))

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
        except InsufficientAllocatedCells as e:
            print(f'Warning: {e} Increasing number of steps.')
            return False
        return True

    def finalize_segments(self):
        self.segments.finalize(
            self.program_base.segment_index, size=len(self.program.data),
            public_memory=[(i, 0) for i in range(len(self.program.data))])
        self.segments.finalize(
            self.execution_base.segment_index,
            size=get_segment_used_size(self.execution_base.segment_index, self.vm_memory),
            public_memory=[
                (x + self.execution_base.offset, 0) for x in self.execution_public_memory])

        for builtin_runner in self.builtin_runners.values():
            builtin_runner.finalize_segments(self)

    def finalize_segments_by_effective_size(self):
        """
        Similar to finalize_segments, except the size of each segment is simply deduced from its
        usage, ignoring proof considerations.
        """
        self.segments.finalize_all_by_effective_size()

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
            for builtin_runner in self.builtin_runners.values())
        # Out of the range check units allowed per step three are used for the instruction.
        unused_rc_units = (instance.rc_units - 3) * self.vm.current_step - rc_units_used_by_builtins
        rc_usage_upper_bound = (rc_max - rc_min)
        if unused_rc_units < rc_usage_upper_bound:
            raise InsufficientAllocatedCells(
                f'There are only {unused_rc_units} cells to fill the range checks holes, but '
                f'potentially {rc_usage_upper_bound} are required.')

    def check_memory_usage(self):
        """
        Checks that there are enough trace cells to fill the entire memory range.
        """
        instance = LAYOUTS[self.layout]
        builtins_memory_units = sum(
            builtin_runner.get_allocated_memory_units(self)
            for builtin_runner in self.builtin_runners.values())
        # Out of the memory units available per step, a fraction is used for public memory, and
        # four are used for the instruction.
        total_memory_units = instance.memory_units_per_step * self.vm.current_step
        public_memory_units = safe_div(total_memory_units, instance.public_memory_fraction)
        instruction_memory_units = 4 * self.vm.current_step
        unused_memory_units = total_memory_units - \
            (public_memory_units + instruction_memory_units + builtins_memory_units)
        memory_address_holes = self.segments.get_memory_holes()
        if unused_memory_units < memory_address_holes:
            raise InsufficientAllocatedCells(
                f'There are only {unused_memory_units} cells to fill the memory address holes, but '
                f'{memory_address_holes} are required.')

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
            assert isinstance(self.program, Program), \
                'Label name cannot be used with a StrippedProgram.'
            return self.program.get_label(label_or_pc)
        return label_or_pc

    def load_data(self, ptr: MaybeRelocatable, data: Sequence[MaybeRelocatable]) -> \
            MaybeRelocatable:
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

    def relocate_value(self, value):
        return relocate_value(value, self.segment_offsets, self.program.prime)

    def relocate(self):
        self.segment_offsets = self.segments.relocate_segments()

        self.relocated_memory = MemoryDict({
            self.relocate_value(addr): self.relocate_value(value)
            for addr, value in self.vm_memory.items()})
        self.relocated_trace = relocate_trace(
            self.vm.trace, self.segment_offsets, self.program.prime)
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
        return {
            name: MemorySegmentAddresses(
                begin_addr=self.relocate_value(segment_addresses.begin_addr),
                stop_ptr=(
                    self.relocate_value(segment_addresses.stop_ptr)
                    if segment_addresses.stop_ptr is not None else None))
            for builtin_runner in self.builtin_runners.values()
            for name, segment_addresses in builtin_runner.get_memory_segment_addresses(self).items()
        }

    def print_memory(self, relocated: bool):
        print('Addr  Value')
        print('-----------')
        old_addr = -1
        memory = self.relocated_memory if relocated else self.vm_memory
        for addr in sorted(memory.keys()):
            val = memory[addr]
            if addr != old_addr + 1:
                print('\u22ee')
            print(f'{addr:<5} {to_field_element(val=val, prime=self.program.prime)}')
            old_addr = addr
        print()

    def print_output(self, output_callback=to_field_element):
        if 'output_builtin' not in self.builtin_runners:
            return

        output_runner = self.builtin_runners['output_builtin']
        print('Program output:')
        _, size = output_runner.get_used_cells_and_allocated_size(self)
        for i in range(size):
            val = self.vm_memory.get(output_runner.base + i)
            if val is not None:
                print(f'  {output_callback(val=val, prime=self.program.prime)}')
            else:
                print('  <missing>')

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
        if self.segment_offsets is not None:
            info += 'Segment relocation table:\n'
            for segment_index in range(self.segments.n_segments):
                info += f'{segment_index:<5} {self.segment_offsets[segment_index]}\n'

        return info

    def get_builtin_usage(self) -> str:
        if len(self.builtin_runners) == 0:
            return ''

        builtin_usage_str = '\nBuiltin usage:\n'
        for name, builtin_runner in self.builtin_runners.items():
            used, size = builtin_runner.get_used_cells_and_allocated_size(self)
            percentage = f'{used / size * 100:.2f}%' if size > 0 else '100%'
            builtin_usage_str += f'{name:<30s} {percentage:>7s} (used {used} cells)\n'

        return builtin_usage_str

    def print_builtin_usage(self):
        print(self.get_builtin_usage())

    def get_builtin_segments_info(self):
        builtin_segments: Dict[str, SegmentInfo] = {}
        for builtin in self.builtin_runners.values():
            for name, segment_addresses in builtin.get_memory_segment_addresses(self).items():
                begin_addr = segment_addresses.begin_addr
                assert isinstance(begin_addr, RelocatableValue), \
                    f'{name} segment begin_addr is not a RelocatableValue {begin_addr}.'
                assert begin_addr.offset == 0, \
                    f'Unexpected {name} segment begin_addr {begin_addr.offset}.'
                assert segment_addresses.stop_ptr is not None, f'{name} segment stop ptr is None.'
                segment_index = begin_addr.segment_index
                segment_size = segment_addresses.stop_ptr - begin_addr
                assert name not in builtin_segments, f'Builtin segment name collision: {name}.'
                builtin_segments[name] = SegmentInfo(index=segment_index, size=segment_size)
        return builtin_segments

    def get_execution_resources(self) -> ExecutionResources:
        n_steps = len(self.vm.trace) if self.original_steps is None else self.original_steps
        n_memory_holes = self.segments.get_memory_holes()
        builtin_instance_counter = {
            builtin_name: builtin_runner.get_used_instances(self)
            for builtin_name, builtin_runner in self.builtin_runners.items()
        }
        return ExecutionResources(
            n_steps=n_steps,
            n_memory_holes=n_memory_holes,
            builtin_instance_counter=builtin_instance_counter)

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
            self.vm_memory[self.execution_base + n_used_builtins + i] for i in range(2))

        assert isinstance(ret_fp, RelocatableValue), f'Expecting a relocatable value got {ret_fp}.'
        assert isinstance(ret_pc, RelocatableValue), f'Expecting a relocatable value got {ret_pc}.'

        assert self.segments.segment_sizes[ret_fp.segment_index] == 0, \
            f'Unexpected ret_fp_segment size {self.segments.segment_sizes[ret_fp.segment_index]}'
        assert self.segments.segment_sizes[ret_pc.segment_index] == 0, \
            f'Unexpected ret_pc_segment size {self.segments.segment_sizes[ret_pc.segment_index]}'

        for addr in self.program_base, self.execution_base, ret_fp, ret_pc:
            assert addr.offset == 0, 'Expecting a 0 offset.'
            known_segment_indices[addr.segment_index] = None

        # Put all the remaining segments in extra_segments.
        extra_segments = [
            SegmentInfo(idx, size)
            for idx, size in sorted(self.segments.segment_sizes.items())
            if idx not in known_segment_indices
        ]

        execution_size = self.vm.run_context.ap - self.execution_base
        cairo_pie_metadata = CairoPieMetadata(
            program=self.program.stripped(),
            program_segment=SegmentInfo(
                index=self.program_base.segment_index, size=len(self.program.data)),
            execution_segment=SegmentInfo(
                index=self.execution_base.segment_index, size=execution_size),
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
        code: Union[str, Sequence[Tuple[str, str]]], layout: str, prime: int) -> CairoRunner:
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
    runner.read_return_values()
    runner.finalize_segments_by_effective_size()
    runner.end_run()
    return runner
