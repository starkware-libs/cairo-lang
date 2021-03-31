#!/usr/bin/env python3

import argparse
import sys

from starkware.cairo.lang.tracer.profile import profile_from_tracer_data
from starkware.cairo.lang.tracer.tracer_data import TracerData


def main():
    parser = argparse.ArgumentParser(
        description='A tool to generate pprof-style profiling data from a Cairo trace.')
    parser.add_argument(
        '--program', type=str, required=True, help='A path to the program json file.')
    parser.add_argument(
        '--memory', type=str, required=True, help='A path to the memory file.')
    parser.add_argument(
        '--trace', type=str, required=True, help='A path to the trace file.')
    parser.add_argument(
        '--debug_info', type=str, required=True, help='A path to the run time debug info file.')
    parser.add_argument(
        '--profile_output', type=str, default='profile.pb.gz',
        help='A path to an output file to write profile data to. Can be opened in pprof.')

    args = parser.parse_args()

    tracer_data = TracerData.from_files(
        program_path=args.program,
        memory_path=args.memory,
        trace_path=args.trace,
        air_public_input=None,
        debug_info_path=args.debug_info,
    )

    data = profile_from_tracer_data(tracer_data)
    with open(args.profile_output, 'wb') as fp:
        fp.write(data)
    return 0


if __name__ == '__main__':
    sys.exit(main())
