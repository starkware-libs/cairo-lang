#!/usr/bin/env python3

import argparse
import json
import re
import sys

from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.lang.version import __version__


def reconstruct_traceback(program: Program, traceback_txt: str):
    def location_replacer(match: re.Match, keep_original_line: bool) -> str:
        assert program.debug_info is not None, "Missing debug information in the compiled program."
        pc = int(match.group("pc"))
        instruction_location = program.debug_info.instruction_locations.get(pc)
        if instruction_location is None:
            # Return the text unchanged.
            return match.group(0)
        res = instruction_location.inst.to_string_with_content(
            match.group(0) if keep_original_line else ""
        )
        return res

    traceback_txt = re.sub(
        r"Unknown location \(pc=0:(?P<pc>\d+)\)",
        lambda match: location_replacer(match=match, keep_original_line=False),
        traceback_txt,
    )
    traceback_txt = re.sub(
        r"Error at pc=0:(?P<pc>\d+):",
        lambda match: location_replacer(match=match, keep_original_line=True),
        traceback_txt,
    )
    return traceback_txt


def main():
    parser = argparse.ArgumentParser(
        description="A tool to reconstruct Cairo traceback given a compiled program with debug "
        "information."
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--program", type=str, help="A path to the Cairo program.")
    parser.add_argument("--contract", type=str, help="A path to the StarkNet contract.")
    parser.add_argument(
        "--traceback",
        type=str,
        required=True,
        help="A path to the traceback file with the missing location information. "
        'Use "-" to read the traceback from stdin.',
    )

    args = parser.parse_args()
    assert (0 if args.program is None else 1) + (
        0 if args.contract is None else 1
    ) == 1, "Exactly one of --program, --contract must be specified."
    if args.program is not None:
        program_json = json.load(open(args.program))
    else:
        assert args.contract is not None
        program_json = json.load(open(args.contract))["program"]

    program = Program.load(program_json)
    traceback = (open(args.traceback) if args.traceback != "-" else sys.stdin).read()

    print(reconstruct_traceback(program, traceback))
    return 0


if __name__ == "__main__":
    sys.exit(main())
