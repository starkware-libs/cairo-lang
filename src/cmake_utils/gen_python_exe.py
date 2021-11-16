#!/usr/bin/env python3

"""
A helper script for python_rules.cmake.
Generates an executable file that runs a python module in a specific python virtual environment.
"""

import json
import os
import stat
from argparse import ArgumentParser


def main():
    parser = ArgumentParser(description="Generates an executable file for python_exe().")
    parser.add_argument("--name", help="The name of the target", required=True)
    parser.add_argument("--exe_path", help="The path to the output script file", required=True)
    parser.add_argument(
        "--venv", help="The python virtual environment that will run the module", required=True
    )
    parser.add_argument("--module", help="The name of the module to run", required=True)
    parser.add_argument("--args", help="Additional arguments to pass to the module")
    parser.add_argument("--info_dir", help="Directory for all libraries info files", required=True)
    parser.add_argument(
        "--cmake_binary_dir", help="The path to the CMake binary root dir", required=True
    )
    parser.add_argument("--working_dir", help="Working directory to run the executable from.")
    parser.add_argument(
        "--environment_variables", help="Environments variables for the executable."
    )
    args = parser.parse_args()

    venv_info = json.load(open(os.path.join(args.info_dir, f"{args.venv}.info")))
    # Fetch the location of the venv dir, relative to the executable script.
    build_path_bash = os.path.relpath(args.cmake_binary_dir, os.path.dirname(args.exe_path))
    assert (
        "venv_dir" in venv_info
    ), f'venv_dir not found, make sure "{args.venv}" is a valid virtual environment.'
    venv_dir_rel = os.path.relpath(venv_info["venv_dir"], args.cmake_binary_dir)
    cd_command = f"cd {args.working_dir}" if args.working_dir else ""

    exe_args = args.args.replace(
        "{VENV_SITE_DIR}",
        "${BUILD_ROOT}/" + os.path.relpath(venv_info["site_dir"], args.cmake_binary_dir),
    )

    with open(args.exe_path, "w") as fp:
        fp.write(
            f"""\
#!/bin/bash
# Find the directory of the executable using $(dirname $0), convert it to absolute path using
# realpath, and use it to find build directory (e.g., .../build/Debug or /app/).
export BUILD_ROOT=$(realpath $(dirname $0)/{build_path_bash})

{cd_command}
source ${{BUILD_ROOT}}/{venv_dir_rel}/bin/activate
{args.environment_variables} \
CMAKE_TARGET_NAME={args.name} \
${{BUILD_ROOT}}/{venv_dir_rel}/bin/python -u -m {args.module} {exe_args} "$@"
"""
        )

    os.chmod(
        args.exe_path,
        stat.S_IXUSR
        | stat.S_IRUSR
        | stat.S_IWUSR
        | stat.S_IXGRP
        | stat.S_IRGRP
        | stat.S_IXOTH
        | stat.S_IROTH,
    )

    # Generate info file.
    with open(os.path.join(args.info_dir, f"{args.name}.info"), "w") as fp:
        json.dump(
            {
                "exe_path": args.exe_path,
                "venv": args.venv,
            },
            fp,
            indent=4,
        )
        fp.write("\n")


if __name__ == "__main__":
    main()
