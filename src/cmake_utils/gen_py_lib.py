#!/usr/bin/env python3

"""
A helper script for python_rules.cmake.
Generates a json file that holds all the information for a python library target.
Output is of the form:
  {
      "files": [
          "starkware/crypto/__init__.py",
          "starkware/crypto/signature/__init__.py",
          "starkware/crypto/signature/fast_pedersen_hash.py",
          "starkware/crypto/signature/math_utils.py",
          "starkware/crypto/signature/nothing_up_my_sleeve_gen.py",
          "starkware/crypto/signature/pedersen_params.json",
          "starkware/crypto/signature/signature.py"
      ],
      "import_path": null,
      "lib_deps": [
          "pip_mpmath",
          "pip_sympy"
      ],
      "lib_dir": "<full path to build dir of the library>",
      "name": "starkware_crypto_lib"
  }
"""

import glob
import json
import os
from argparse import ArgumentParser
from typing import List


def extract_licenses(filename: str) -> List[str]:
    prefix = "License: "
    if os.path.isfile(filename):
        with open(filename, encoding="utf8") as fp:
            for line in fp.readlines():
                if line.startswith(prefix):
                    return line.strip()[len(prefix) :].split(",")
    return []


def main():
    parser = ArgumentParser(
        description="Generates a json file that holds all the information for a python library "
        "target."
    )
    parser.add_argument("--name", type=str, help="Python library target name", required=True)
    parser.add_argument(
        "--interpreters", type=str, nargs="*", help="Supported interpreters", default=["python3.7"]
    )
    parser.add_argument("--lib_dir", type=str, nargs="*", help="Library directory", required=True)
    parser.add_argument(
        "--import_paths", type=str, nargs="*", default=[], help="Path to add to sys.path"
    )
    parser.add_argument("--files", type=str, nargs="*", help="Library file list")
    parser.add_argument(
        "--lib_deps", type=str, nargs="*", help="Dependency libraries list", required=True
    )
    parser.add_argument("--output", type=str, help="Output info file", required=True)
    parser.add_argument(
        "--py_exe_deps", type=str, nargs="*", required=True, help="List of executable dependencies"
    )
    parser.add_argument(
        "--cmake_dir", type=str, nargs="?", help="Directory of this CMake target", required=False
    )
    parser.add_argument(
        "--prefix", type=str, nargs="?", help="Prefix of this CMake target", required=False
    )
    args = parser.parse_args()

    # Try to extract license if possible.
    licenses = []
    for d in args.lib_dir:
        # Remove filters if exist (like 'pypy:<path>').
        d = d.split(":")[-1]
        metadata_files = glob.glob(os.path.join(d, "*/METADATA"))
        for filename in metadata_files:
            licenses += extract_licenses(filename)
    licenses = sorted(set(licenses))

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as fp:
        json.dump(
            dict(
                name=args.name,
                lib_dir=args.lib_dir,
                interpreters=args.interpreters,
                import_paths=args.import_paths,
                files=args.files if args.files is not None else [],
                lib_deps=args.lib_deps,
                py_exe_deps=args.py_exe_deps,
                licenses=licenses,
                cmake_dir=args.cmake_dir,
                prefix=args.prefix,
            ),
            fp,
            sort_keys=True,
            indent=4,
        )
        fp.write("\n")


if __name__ == "__main__":
    main()
