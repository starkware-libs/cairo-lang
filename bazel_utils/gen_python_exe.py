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
    args = parser.parse_args()

    print(
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


if __name__ == "__main__":
    main()
