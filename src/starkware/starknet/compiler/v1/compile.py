import json
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starkware_utils.error_handling import StarkException

JsonObject = Dict[str, Any]

DEFAULT_ALLOWED_LIBFUNCS_ARG: List[str] = []


def get_allowed_libfuncs_list_file(file_name: str) -> str:
    main_dir_path = os.path.dirname(__file__)
    file_path = os.path.join(main_dir_path, file_name + ".json")

    return file_path


if "RUNFILES_DIR" in os.environ:
    from bazel_tools.tools.python.runfiles import runfiles

    r = runfiles.Create()

    STARKNET_SIERRA_COMPILE = r.Rlocation("cairo-lang-1.0.0/bin/starknet-sierra-compile")
    STARKNET_COMPILE = r.Rlocation("cairo-lang-1.0.0/bin/starknet-compile")
else:
    STARKNET_SIERRA_COMPILE = os.path.join(
        os.path.dirname(__file__), "bin", "starknet-sierra-compile"
    )
    STARKNET_COMPILE = os.path.join(os.path.dirname(__file__), "bin", "starknet-compile")


def build_allowed_libfuncs_args(
    allowed_libfuncs_list_name: Optional[str] = None,
    allowed_libfuncs_list_file: Optional[str] = None,
) -> List[str]:
    if allowed_libfuncs_list_name is None and allowed_libfuncs_list_file is None:
        return DEFAULT_ALLOWED_LIBFUNCS_ARG

    assert allowed_libfuncs_list_name is None or allowed_libfuncs_list_file is None, (
        "Received too many libfuncs list parameters."
        f"allowed_libfuncs_list_name = {allowed_libfuncs_list_name},"
        f"allowed_libfuncs_list_file = {allowed_libfuncs_list_file}."
    )

    if allowed_libfuncs_list_name is not None:
        return ["--allowed-libfuncs-list-name", allowed_libfuncs_list_name]

    assert allowed_libfuncs_list_file is not None
    return [
        "--allowed-libfuncs-list-file",
        get_allowed_libfuncs_list_file(allowed_libfuncs_list_file),
    ]


def compile_cairo_to_sierra(
    cairo_path: str,
    allowed_libfuncs_list_name: Optional[str] = None,
    allowed_libfuncs_list_file: Optional[str] = None,
) -> JsonObject:
    """
    Compiles a Starknet Cairo 1.0 contract; returns the resulting Sierra as json.
    """
    additional_args = build_allowed_libfuncs_args(
        allowed_libfuncs_list_name=allowed_libfuncs_list_name,
        allowed_libfuncs_list_file=allowed_libfuncs_list_file,
    )
    return run_compile_command(command=[STARKNET_COMPILE, cairo_path, *additional_args])


def compile_sierra_to_casm(
    sierra_path: str,
    allowed_libfuncs_list_name: Optional[str] = None,
    allowed_libfuncs_list_file: Optional[str] = None,
) -> JsonObject:
    """
    Compiles a Starknet Sierra contract; returns the resulting Casm as json.
    """
    additional_args = build_allowed_libfuncs_args(
        allowed_libfuncs_list_name=allowed_libfuncs_list_name,
        allowed_libfuncs_list_file=allowed_libfuncs_list_file,
    )
    return run_compile_command(
        command=[STARKNET_SIERRA_COMPILE, sierra_path, "--add-pythonic-hints", *additional_args]
    )


def compile_cairo_to_casm(
    cairo_path: str,
    allowed_libfuncs_list_name: Optional[str] = None,
    allowed_libfuncs_list_file: Optional[str] = None,
) -> JsonObject:
    """
    Compiles a Starknet Cairo 1.0 contract to Casm; returns the resulting Casm as json.
    """
    raw_sierra = compile_cairo_to_sierra(
        cairo_path=cairo_path,
        allowed_libfuncs_list_name=allowed_libfuncs_list_name,
        allowed_libfuncs_list_file=allowed_libfuncs_list_file,
    )
    with tempfile.NamedTemporaryFile(mode="w") as sierra_file:
        json.dump(obj=raw_sierra, fp=sierra_file, indent=2)
        sierra_file.flush()

        return compile_sierra_to_casm(
            sierra_path=sierra_file.name,
            allowed_libfuncs_list_name=allowed_libfuncs_list_name,
            allowed_libfuncs_list_file=allowed_libfuncs_list_file,
        )


def run_compile_command(command: List[str]) -> JsonObject:
    try:
        result: subprocess.CompletedProcess = subprocess.run(command, capture_output=True)
    except subprocess.CalledProcessError:
        # The inner command is responsible for printing the error message. No need to print the
        # stack trace of this script.
        raise StarkException(
            code=StarknetErrorCode.COMPILATION_FAILED,
            message="Compilation failed. Invalid file path input.",
        )

    if result is None:
        raise StarkException(
            code=StarknetErrorCode.COMPILATION_FAILED,
            message="Compilation failed.",
        )

    if result.returncode != 0:
        raise StarkException(
            code=StarknetErrorCode.COMPILATION_FAILED,
            message=f"Compilation failed. {result.stderr.decode()}",
        )

    # Read and return the compilation result from the output.
    return json.loads(result.stdout.decode())
