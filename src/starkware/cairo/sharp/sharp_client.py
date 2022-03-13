#!/usr/bin/env python3

import argparse
import json
import os
import subprocess
import sys
import tempfile
from typing import List, Optional

from starkware.cairo.bootloaders.generate_fact import get_cairo_pie_fact_info
from starkware.cairo.bootloaders.hash_program import compute_program_hash_chain
from starkware.cairo.lang.compiler.assembler import Program
from starkware.cairo.lang.vm.crypto import get_crypto_lib_context_manager
from starkware.cairo.sharp.client_lib import CairoPie, ClientLib
from starkware.cairo.sharp.fact_checker import FactChecker


class SharpClient:
    """
    Encapsulates communication with the SHARP and related tasks.
    """

    def __init__(
        self,
        service_client: ClientLib,
        contract_client: FactChecker,
        steps_limit: int,
        cairo_compiler_path: str,
        cairo_run_path: str,
    ):
        """
        service_client: a client to communicate with the proving service.
        contract_client: a client to inspect verified statements.
        steps_limit: maximal number of execution steps allowed to send to the SHARP.
        cairo_compiler_path: the path of the cairo compiler.
        cairo_run_path: the path of the cairo vm executor.
        """
        self.service_client = service_client
        self.contract_client = contract_client
        self.steps_limit = steps_limit
        self.cairo_compiler_path = cairo_compiler_path
        self.cairo_run_path = cairo_run_path

    def compile_cairo(self, source_code_path: str, flags: Optional[List[str]] = None) -> Program:
        """
        Compiles the cairo source code at the provided path,
        and returns the compiled program.
        """
        used_flags = [] if flags is None else flags
        with tempfile.NamedTemporaryFile("w") as compiled_program_file:
            # Compile the program.
            subprocess.check_call(
                [
                    self.cairo_compiler_path,
                    source_code_path,
                    f"--output={compiled_program_file.name}",
                ]
                + used_flags
            )
            program = Program.load(data=json.load(open(compiled_program_file.name, "r")))
        return program

    def run_program(self, program: Program, program_input_path: Optional[str]) -> CairoPie:
        """
        Runs the program, with the provided input,
        and returns the Cairo PIE (Position Independent Execution).
        """
        with tempfile.NamedTemporaryFile("w") as cairo_pie_file, tempfile.NamedTemporaryFile(
            "w"
        ) as program_file:
            json.dump(program.dump(), program_file, indent=4, sort_keys=True)
            program_file.flush()
            cairo_run_cmd = list(
                filter(
                    None,
                    [
                        self.cairo_run_path,
                        "--layout=all",
                        f"--program={program_file.name}",
                        f"--program_input={program_input_path}"
                        if program_input_path is not None
                        else None,
                        f"--cairo_pie_output={cairo_pie_file.name}",
                    ],
                )
            )
            subprocess.check_call(cairo_run_cmd)
            cairo_pie = CairoPie.from_file(cairo_pie_file.name)
        return cairo_pie

    def get_fact(self, cairo_pie: CairoPie) -> str:
        """
        Returns the fact that uniquely representing the statement.
        The verification is trust worthy when this fact is registered
        on the Verifier Fact-Registry.
        """
        program_hash = compute_program_hash_chain(cairo_pie.program)
        return get_cairo_pie_fact_info(cairo_pie, program_hash).fact

    def fact_registered(self, fact: str) -> bool:
        """
        Returns true if and only if the fact is registered on the verifier contract.
        """
        return self.contract_client.is_valid(fact)

    def submit_cairo_pie(self, cairo_pie: CairoPie) -> str:
        """
        Submits a job to the SHARP, and returns a job identifier.
        Asserts that the number of execution steps does not exceed the allowed limit.
        """
        n_steps = cairo_pie.execution_resources.n_steps
        assert n_steps < self.steps_limit, (
            f"Execution trace length exceeds limit. The execution length is {n_steps} "
            f"and the limit is {self.steps_limit}."
        )

        return self.service_client.add_job(cairo_pie=cairo_pie)

    def job_failed(self, job_key: str) -> bool:
        """
        Returns True if and only if the job has failed, thus is not expected to be proven.
        """
        return self.service_client.get_status(job_key) in ["INVALID", "FAILED"]

    def get_job_status(self, job_key: str) -> str:
        """
        Returns a string representing the status of the job.
        If the job failed, the string includes the failure reason.
        """
        try:
            status = self.service_client.get_status(job_key)
        except AssertionError as ex:
            # Get the assertion message.
            status = str(ex)

        return status


def init_client(bin_dir: str, node_rpc_url: Optional[str] = None) -> SharpClient:
    """
    Initialized a SharpClient instance, with or without node access.
    """
    # Load configuration file.
    CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
    with open(CONFIG_PATH, "r") as config_file:
        config = json.load(config_file)

    # Get Cairo toolchain executable paths.
    CAIRO_COMPILE_EXE = os.path.join(os.path.join(bin_dir, "cairo-compile"))
    CAIRO_RUN_EXE = os.path.join(os.path.join(bin_dir, "cairo-run"))

    # Initialize the SharpClient.
    client = SharpClient(
        service_client=ClientLib(config["prover_url"]),
        contract_client=FactChecker(
            fact_registry_address=config["verifier_address"],
            node_rpc_url=node_rpc_url if node_rpc_url is not None else "",
        ),
        steps_limit=config["steps_limit"],
        cairo_compiler_path=CAIRO_COMPILE_EXE,
        cairo_run_path=CAIRO_RUN_EXE,
    )

    return client


def submit(args, command_args):
    parser = argparse.ArgumentParser(
        description="Submits a Cairo job to SHARP. "
        "You can provide (1) the source code and the program input OR (2) the compiled program and "
        "the program input OR (3) the Cairo PIE."
    )

    parser.add_argument(
        "--source", type=str, required=False, help="A path to the Cairo source code."
    )
    parser.add_argument(
        "--program", type=str, required=False, help="A path to the compiled program."
    )
    parser.add_argument(
        "--program_input", type=str, required=False, help="A path to the program input."
    )
    parser.add_argument("--cairo_pie", type=str, required=False, help="A path to the Cairo PIE.")

    parser.parse_args(command_args, namespace=args)

    is_not_none = lambda x: 1 if x is not None else 0
    assert (
        is_not_none(args.source) + is_not_none(args.program) + is_not_none(args.cairo_pie) == 1
    ), "Exactly one of --source, --program, --cairo_pie must be specified."

    client = init_client(bin_dir=args.bin_dir)

    if args.cairo_pie is not None:
        assert (
            args.program_input is None
        ), "Error: --program_input cannot be specified with --cairo_pie."
        cairo_pie = CairoPie.from_file(args.cairo_pie)
    else:
        if args.program is not None:
            program = Program.load(data=json.load(open(args.program)))
        else:
            assert args.source is not None
            print("Compiling...", file=sys.stderr)
            program = client.compile_cairo(source_code_path=args.source)

        print("Running...", file=sys.stderr)
        cairo_pie = client.run_program(program=program, program_input_path=args.program_input)

    fact = client.get_fact(cairo_pie)
    print("Submitting to SHARP...", file=sys.stderr)
    job_key = client.submit_cairo_pie(cairo_pie=cairo_pie)

    print("Job sent.", file=sys.stderr)

    print(f"Job key: {job_key}")
    print(f"Fact: {fact}")

    return 0


def get_job_status(args, command_args):
    parser = argparse.ArgumentParser(description="Retreive the status of a SHARP Cairo job.")
    parser.add_argument("job_key", type=str, help="The key identifying the job.")

    parser.parse_args(command_args, namespace=args)

    client = init_client(bin_dir=args.bin_dir)
    print(client.get_job_status(args.job_key))

    return 0


def is_verified(args, command_args):
    """
    Verifies a fact is registered on-chain.
    The fact is provided in the command args.
    """
    parser = argparse.ArgumentParser(
        description="Verify a fact is registered on the SHARP fact-registry."
    )
    parser.add_argument("fact", type=str, help="The fact to verify if registered.")
    parser.add_argument(
        "--node_url", required=True, type=str, help="URL for a Goerli Ethereum node RPC API."
    )

    parser.parse_args(command_args, namespace=args)

    client = init_client(bin_dir=args.bin_dir, node_rpc_url=args.node_url)
    print(client.fact_registered(args.fact))

    return 0


def main():
    subparsers = {
        "submit": submit,
        "status": get_job_status,
        "is_verified": is_verified,
    }

    parser = argparse.ArgumentParser(description="A tool to communicate with SHARP.")
    parser.add_argument("command", choices=subparsers.keys())
    parser.add_argument(
        "--bin_dir",
        type=str,
        default="",
        help="The path to a directory that contains the cairo-compile and cairo-run scripts. "
        "If not specified, files are assumed to be in the system's PATH.",
    )
    parser.add_argument(
        "--flavor",
        type=str,
        default="Release",
        choices=["Debug", "Release", "RelWithDebInfo"],
        help="Build flavor",
    )

    args, unknown = parser.parse_known_args()

    with get_crypto_lib_context_manager(args.flavor):
        try:
            # Invoke the requested command.
            return subparsers[args.command](args, unknown)
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
