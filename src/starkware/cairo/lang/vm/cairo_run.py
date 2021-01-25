import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from typing import BinaryIO, Dict, List, Tuple

import starkware.python.python_dependencies as python_dependencies
from starkware.cairo.lang.compiler.debug_info import DebugInfo
from starkware.cairo.lang.compiler.program import Program, ProgramBase
from starkware.cairo.lang.instances import LAYOUTS
from starkware.cairo.lang.version import __version__
from starkware.cairo.lang.vm.air_public_input import PublicInput, PublicMemoryEntry
from starkware.cairo.lang.vm.cairo_pie import CairoPie
from starkware.cairo.lang.vm.cairo_runner import CairoRunner
from starkware.cairo.lang.vm.crypto import get_crypto_lib_context_manager
from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.security import verify_secure_runner
from starkware.cairo.lang.vm.trace_entry import TraceEntry
from starkware.cairo.lang.vm.utils import MemorySegmentAddresses
from starkware.cairo.lang.vm.vm import VmException


def main():
    start_time = time.time()

    parser = argparse.ArgumentParser(
        description='A tool to run Cairo programs.')
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument(
        '--program', type=argparse.FileType('r'), help='The name of the program json file.')
    parser.add_argument(
        '--program_input', type=argparse.FileType('r'),
        help='Path to a json file representing the (private) input of the program.')
    parser.add_argument(
        '--steps', type=int,
        help='The number of instructions to perform. If steps is not given, runs the program until '
        'the __end__ instruction, and then continues until the number of steps is a power of 2.')
    parser.add_argument(
        '--min_steps', type=int,
        help='The minimal number of instructions to perform. This can be used to guarantee that '
        'there will be enough builtin instances for the program.')
    parser.add_argument(
        '--debug_error', action='store_true',
        help='If there is an error during the execution, stop the execution, but produce the '
        'partial outputs.')
    parser.add_argument(
        '--no_end', action='store_true',
        help="Don't check that the program ended successfully.")
    parser.add_argument(
        '--print_memory', action='store_true',
        help='Show the values on the memory after the execution.')
    parser.add_argument(
        '--relocate_prints', action='store_true',
        help='Print memory and info after memory relocation.')
    parser.add_argument(
        '--secure_run', action='store_true',
        help='Verify the run is secure and can be run safely using the bootloader.')
    parser.add_argument(
        '--print_info', action='store_true',
        help='Print information on the execution of the program.')
    parser.add_argument(
        '--print_output', action='store_true',
        help='Prints the program output (if the output builtin is used).')
    parser.add_argument(
        '--memory_file', type=argparse.FileType('wb'),
        help='Output file name for the memory.')
    parser.add_argument(
        '--trace_file', type=argparse.FileType('wb'),
        help='Output file name for the execution trace.')
    parser.add_argument(
        '--run_from_cairo_pie', type=argparse.FileType('rb'),
        help='Runs a Cairo PIE file, instead of a program. '
        'This flag can be used with --secure_run to verify the correctness of a Cairo PIE file.')
    parser.add_argument(
        '--cairo_pie_output', type=argparse.FileType('wb'),
        help='Output file name for the CairoPIE object.')
    parser.add_argument(
        '--debug_info_file', type=argparse.FileType('w'),
        help='Output file name for debug information created at run time.')
    parser.add_argument(
        '--air_public_input', type=argparse.FileType('w'),
        help='Output file name for the public input json file of the Cairo AIR.')
    parser.add_argument(
        '--air_private_input', type=argparse.FileType('w'),
        help='Output file name for the private input json file of the Cairo AIR.')
    parser.add_argument(
        '--layout', choices=LAYOUTS.keys(), default='plain',
        help='The layout of the Cairo AIR.')
    parser.add_argument(
        '--tracer', action='store_true', help='Run the tracer.')
    parser.add_argument(
        '--proof_mode', action='store_true', help='Prepare a provable execution trace.')
    parser.add_argument(
        '--flavor', type=str, choices=['Debug', 'Release', 'RelWithDebInfo'], help='Build flavor.')
    python_dependencies.add_argparse_argument(parser)

    args = parser.parse_args()

    assert int(args.program is not None) + int(args.run_from_cairo_pie is not None) == 1, \
        'Exactly one of --program, --run_from_cairo_pie must be specified.'
    assert not (args.proof_mode and args.run_from_cairo_pie), \
        '--proof_mode cannot be used with --run_from_cairo_pie.'
    assert not (args.steps and args.min_steps), '--steps and --min_steps cannot be both specified.'
    assert not (args.cairo_pie_output and args.no_end), \
        '--no_end and --cairo_pie_output cannot be both specified.'
    if args.air_public_input:
        assert args.proof_mode, '--air_public_input can only be used in proof_mode.'
    if args.air_private_input:
        assert args.proof_mode, '--air_private_input can only be used in proof_mode.'

    with get_crypto_lib_context_manager(args.flavor):
        try:
            res = cairo_run(args)
        except VmException as err:
            print(err, file=sys.stderr)
            res = 1
        except AssertionError as err:
            print(f'Error: {err}', file=sys.stderr)
            res = 1

    # Generate python dependencies.
    python_dependencies.process_args(args, start_time)

    return res


def cairo_run(args):
    trace_file = args.trace_file
    if trace_file is None and args.tracer:
        # If --tracer is used, use a temporary file as trace_file.
        trace_file = tempfile.NamedTemporaryFile(mode='wb')

    memory_file = args.memory_file
    if memory_file is None and args.tracer:
        # If --tracer is used, use a temporary file as memory_file.
        memory_file = tempfile.NamedTemporaryFile(mode='wb')

    debug_info_file = args.debug_info_file
    if debug_info_file is None and args.tracer:
        # If --tracer is used, use a temporary file as debug_info_file.
        debug_info_file = tempfile.NamedTemporaryFile(mode='w')

    ret_code = 0
    if args.program is not None:
        program: ProgramBase = Program.Schema().load(json.load(args.program))
        initial_memory = MemoryDict()
        steps_input = args.steps
    else:
        raise NotImplementedError('--run_from_cairo_pie is not supported.')

    runner = CairoRunner(
        program=program, layout=args.layout, memory=initial_memory, proof_mode=args.proof_mode)

    runner.initialize_segments()
    end = runner.initialize_main_entrypoint()

    if args.run_from_cairo_pie is not None:
        # Add extra_segments.
        for segment_info in cairo_pie_input.metadata.extra_segments:
            runner.segments.add(size=segment_info.size)

    program_input = json.load(args.program_input) if args.program_input else {}
    runner.initialize_vm(hint_locals={'program_input': program_input})

    try:
        if args.no_end:
            assert args.steps is not None, '--steps must specified when running with --no-end.'
        else:
            additional_steps = 1 if args.proof_mode else 0
            max_steps = steps_input - additional_steps if steps_input is not None else None
            runner.run_until_pc(end, max_steps=max_steps)
            if args.proof_mode:
                # Run one more step to make sure the last pc that was executed (rather than the pc
                # after it) is __end__.
                runner.run_for_steps(1)
            runner.original_steps = runner.vm.current_step

        if args.min_steps:
            runner.run_until_steps(args.min_steps)

        if steps_input is not None:
            runner.run_until_steps(steps_input)
        elif args.proof_mode:
            runner.run_until_next_power_of_2()
            while not runner.check_used_cells():
                runner.run_for_steps(1)
                runner.run_until_next_power_of_2()
        runner.end_run()
    except (VmException, AssertionError) as exc:
        if args.debug_error:
            print(f'Got an error:\n{exc}')
            ret_code = 1
        else:
            raise exc

    if not args.no_end:
        runner.read_return_values()

    if args.no_end or not args.proof_mode:
        runner.finalize_segments_by_effective_size()
    else:
        # Finalize important segments by correct size.
        runner.finalize_segments()
        # Finalize all user segments by effective size.
        runner.finalize_segments_by_effective_size()

    if args.secure_run:
        verify_secure_runner(runner)

    if args.cairo_pie_output:
        runner.get_cairo_pie().to_file(args.cairo_pie_output)

    runner.relocate()

    if args.print_memory:
        runner.print_memory(relocated=args.relocate_prints)

    if args.print_output:
        runner.print_output()

    if args.print_info:
        runner.print_info(relocated=args.relocate_prints)
        # Skip builtin usage calculation if the execution stopped before reaching the end symbol.
        # Trying to calculate the builtin usage is likely to raise an exception and prevent the user
        # from opening the tracer.
        if args.proof_mode and not args.no_end:
            runner.print_builtin_usage()

    if trace_file is not None:
        field_bytes = math.ceil(program.prime.bit_length() / 8)
        write_binary_trace(trace_file, runner.relocated_trace)

    if memory_file is not None:
        field_bytes = math.ceil(program.prime.bit_length() / 8)
        write_binary_memory(memory_file, runner.relocated_memory, field_bytes)

    if args.air_public_input is not None:
        rc_min, rc_max = runner.get_perm_range_check_limits()
        write_air_public_input(
            layout=args.layout,
            public_input_file=args.air_public_input,
            memory=runner.relocated_memory,
            public_memory_addresses=runner.segments.get_public_memory_addresses(
                runner.segment_offsets),
            memory_segment_addresses=runner.get_memory_segment_addresses(),
            trace=runner.relocated_trace,
            rc_min=rc_min,
            rc_max=rc_max)

    if args.air_private_input is not None:
        assert args.trace_file is not None, \
            '--trace_file must be set when --air_private_input is set.'
        assert args.memory_file is not None, \
            '--memory_file must be set when --air_private_input is set.'
        json.dump({
            'trace_path': f'{os.path.abspath(trace_file.name)}',
            'memory_path': f'{os.path.abspath(memory_file.name)}',
            **runner.get_air_private_input(),
        }, args.air_private_input, indent=4)
        print(file=args.air_private_input)
        args.air_private_input.flush()

    if debug_info_file is not None:
        json.dump(
            DebugInfo.Schema().dump(runner.get_relocated_debug_info()),
            debug_info_file)
        debug_info_file.flush()

    if args.tracer:
        CAIRO_TRACER = 'starkware.cairo.lang.tracer.tracer'
        subprocess.call(list(filter(None, [
            sys.executable,
            '-m',
            CAIRO_TRACER,
            f'--program={args.program.name}',
            f'--trace={trace_file.name}',
            f'--memory={memory_file.name}',
            f'--air_public_input={args.air_public_input.name}' if args.air_public_input else None,
            f'--debug_info={debug_info_file.name}',
        ])))

    return ret_code


def write_binary_trace(trace_file, trace: List[TraceEntry[int]]):
    for trace_entry in trace:
        trace_file.write(trace_entry.serialize())
    trace_file.flush()


def write_binary_memory(memory_file: BinaryIO, memory: MemoryDict, field_bytes: int):
    """
    Dumps the memory file.
    """
    memory_file.write(memory.serialize(field_bytes))
    memory_file.flush()


def write_air_public_input(
        public_input_file, memory: MemoryDict, layout: str,
        public_memory_addresses: List[Tuple[int, int]],
        memory_segment_addresses: Dict[str, MemorySegmentAddresses],
        trace: List[TraceEntry[int]],
        rc_min: int,
        rc_max: int):
    public_memory = [
        PublicMemoryEntry(address=addr, value=memory[addr], page=page)  # type: ignore
        for addr, page in public_memory_addresses]
    initial_pc = trace[0].pc
    assert isinstance(initial_pc, int)
    public_input = PublicInput(  # type: ignore
        layout=layout,
        rc_min=rc_min,
        rc_max=rc_max,
        n_steps=len(trace),
        memory_segments={
            'program': MemorySegmentAddresses(  # type: ignore
                begin_addr=trace[0].pc,
                stop_ptr=trace[-1].pc
            ),
            'execution': MemorySegmentAddresses(  # type: ignore
                begin_addr=trace[0].ap,
                stop_ptr=trace[-1].ap
            ),
            **memory_segment_addresses,
        },
        public_memory=public_memory,
    )
    public_input_file.write(PublicInput.Schema().dumps(public_input, indent=4))
    public_input_file.write('\n')
    public_input_file.flush()


if __name__ == '__main__':
    sys.exit(main())
