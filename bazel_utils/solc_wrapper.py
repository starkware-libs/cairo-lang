import os
import shutil
import subprocess
import sys
import tempfile
from argparse import ArgumentParser


def main():
    parser = ArgumentParser()

    parser.add_argument(
        "--solc",
        type=str,
        help="Solidity compiler path.",
        required=True,
    )
    parser.add_argument(
        "--optimize_runs",
        type=str,
        help=(
            "Set for how many contract runs to optimize. Lower values will optimize more for "
            "initial deployment cost, higher values will optimize more for high-frequency usage."
        ),
        required=True,
    )
    parser.add_argument(
        "--base_path",
        type=str,
        help=(
            "Use the given path as the root of the source tree instead of the root of the "
            "filesystem."
        ),
        required=True,
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output path for combined.json.",
        required=True,
    )
    parser.add_argument(
        "--srcs",
        type=str,
        help="Paths of the solidity source files.",
        required=True,
        nargs="+",
    )
    args = parser.parse_args()

    files_to_compile = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        for src in args.srcs:
            if src.startswith("external/cairo-lang"):
                dest_path = src.replace("external/cairo-lang/", "")
            else:
                dest_path = src
            files_to_compile.append(dest_path)
            os.makedirs(os.path.dirname(tmp_dir + "/" + dest_path), exist_ok=True)
            shutil.copyfile(src, tmp_dir + "/" + dest_path)

        subprocess.check_call(
            [
                os.path.join(os.getcwd(), args.solc),
                "--optimize",
                "--optimize-runs",
                args.optimize_runs,
                "--combined-json",
                "abi,bin",
                "--base-path",
                args.base_path,
                "-o",
                os.path.join(os.getcwd(), args.output),
            ]
            + files_to_compile,
            cwd=tmp_dir,
            stdout=subprocess.DEVNULL,
        )


if __name__ == "__main__":
    sys.exit(main())
