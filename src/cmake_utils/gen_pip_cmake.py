#!/usr/bin/env python3

"""
A helper for pip_rules.cmake.
Generates a CMake file with all pip rules.
Output is of the form:
  python_pip(pip_<package_name> <package_name>==1.2.3 pip_dep0 pip_dep1 ...)
  ...
Needs a dependency json file coming from pipdeptree.
"""

import json
import os
from argparse import ArgumentParser
from collections import defaultdict


def main():
    parser = ArgumentParser(description="Generates a CMake file declaring all pip targets.")
    parser.add_argument(
        "--interpreter_deps",
        type=str,
        nargs="*",
        required=True,
        help="Interpreters and dependency output JSON files. "
        "Example: python3.7:python_deps.json ...",
    )
    parser.add_argument("--output", type=str, help="Output cmake file", required=True)
    args = parser.parse_args()

    res = ""
    package_libs = defaultdict(list)
    package_versions = defaultdict(list)

    # Load dependency files for each interpreter.
    for interpreter_dep in args.interpreter_deps:
        interpreter, dep_file = interpreter_dep.split(":")
        with open(dep_file, "r") as fp:
            for package in json.load(fp):
                # Extract name of package.
                name = package["package"]["key"].replace("-", "_").lower()
                # Build a requirement line for current interpreter.
                req = (
                    package["package"]["package_name"]
                    + "=="
                    + package["package"]["installed_version"]
                )
                package_versions[name].append(f'"{interpreter} {req}"')
                # Append dependency libraries.
                dep_names = [
                    dep["key"].replace("-", "_").lower() for dep in package["dependencies"]
                ]
                package_libs[name] += [f"{interpreter}:pip_{name}" for name in dep_names]

    # Create a united rule for each pip package.
    for package_name in sorted(package_versions.keys()):
        res += f"""
python_pip(pip_{package_name}
  VERSIONS {' '.join(package_versions[package_name])}
  LIBS {' '.join(package_libs[package_name])}
)
"""

    # Write the output file, only if it is changed, so that the timestamp will not be updated
    # otherwise.
    if not os.path.exists(args.output) or open(args.output, "r").read() != res:
        open(args.output, "w").write(res)


if __name__ == "__main__":
    main()
