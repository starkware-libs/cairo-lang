#!/usr/bin/env python3

"""
A helper script for python.bzl.
Generates an executable file that runs a python module.
"""

from argparse import ArgumentParser


def main():
    parser = ArgumentParser(description="Generates an executable file for py_exe().")
    parser.add_argument("--name", help="The name of the target", required=True)
    parser.add_argument("--module", help="The name of the module to run", required=True)
    parser.add_argument(
        "--py_binary_path",
        help="Path where the py_binary is defined by Bazel. For rlocation",
        required=True,
    )
    parser.add_argument(
        "--output_py", help="Path for the output of the python module", required=True
    )
    parser.add_argument(
        "--output_sh",
        help="Path for the output of the shell binary that wraps the py_binary",
        required=True,
    )
    args = parser.parse_args()

    with open(args.output_py, "w") as f:
        f.write(
            f"""\
import os
import subprocess
import sys

cmd = [
    sys.executable, "-u", "-m", {args.module!r}
] + sys.argv[1:]
proc = subprocess.run(cmd)
sys.exit(proc.returncode)
"""
        )

    with open(args.output_sh, "w") as f:
        f.write(
            f"""\
#!/bin/bash

# --- begin runfiles.bash initialization v2 ---
# Copy-pasted from the Bazel Bash runfiles library v2.
set -uo pipefail; f=bazel_tools/tools/bash/runfiles/runfiles.bash
source "${{RUNFILES_DIR:-/dev/null}}/$f" 2>/dev/null || \
  source "$(grep -sm1 "^$f " "${{RUNFILES_MANIFEST_FILE:-/dev/null}}" | cut -f2- -d' ')" \
    2>/dev/null || \
  source "$0.runfiles/$f" 2>/dev/null || \
  source "$(grep -sm1 "^$f " "$0.runfiles_manifest" | cut -f2- -d' ')" 2>/dev/null || \
  source "$(grep -sm1 "^$f " "$0.exe.runfiles_manifest" | cut -f2- -d' ')" 2>/dev/null || \
  {{ echo>&2 "ERROR: cannot find $f"; exit 1; }}; f=; set -e
# --- end runfiles.bash initialization v2 ---

unset PYTHONPATH
exec $(rlocation {args.py_binary_path}) "$@"
"""
        )


if __name__ == "__main__":
    main()
