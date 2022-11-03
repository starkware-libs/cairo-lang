import json
import os
import tempfile

from pytest import MonkeyPatch

import starkware.cairo.sharp.sharp_client as sharp_client
from starkware.cairo.bootloaders.fact_topology import FactInfo
from starkware.cairo.bootloaders.generate_fact import get_program_output
from starkware.cairo.sharp.sharp_client import SharpClient

DIR = os.path.dirname(__file__)
CAIRO_SCRIPTS_DIR = os.path.join(DIR, "../lang/scripts")
CAIRO_COMPILE_EXE = os.path.join(CAIRO_SCRIPTS_DIR, "cairo-compile")
CAIRO_RUN_EXE = os.path.join(CAIRO_SCRIPTS_DIR, "cairo-run")


def test_compile_and_run():
    """
    Compiles and runs a simple cairo program.
    Verifies the output of the execution is as expected.
    """
    client = SharpClient(
        service_client=None,
        contract_client=None,
        steps_limit=0,
        cairo_compiler_path=CAIRO_COMPILE_EXE,
        cairo_run_path=CAIRO_RUN_EXE,
    )

    cairo_program = """
%builtins output
func main(output_ptr: felt*) -> (output_ptr: felt*) {
    %{ memory[ids.output_ptr] = program_input['x'] ** 2 %}
    return (output_ptr=output_ptr + 1);
}
"""
    program_input = {"x": 3}

    with tempfile.NamedTemporaryFile("w") as cairo_prog_file:
        cairo_prog_file.write(cairo_program)
        cairo_prog_file.flush()
        compiled_program = client.compile_cairo(cairo_prog_file.name)
        with tempfile.NamedTemporaryFile("w") as prog_input_file:
            prog_input_file.write(json.dumps(program_input))
            prog_input_file.flush()
            cairo_pie = client.run_program(compiled_program, prog_input_file.name)

    assert get_program_output(cairo_pie) == [3**2]


def test_get_fact(monkeypatch: MonkeyPatch):
    """
    Tests that get_fact() command computes the fact correctly.
    """

    class CairoPieStub:
        def __init__(self, program: str, output: str):
            self.program = program
            self.output = output

    client = SharpClient(
        service_client=None,
        contract_client=None,
        steps_limit=0,
        cairo_compiler_path="",
        cairo_run_path="",
    )

    monkeypatch.setattr(
        sharp_client, "compute_program_hash_chain", lambda program: f"hash({program})"
    )

    monkeypatch.setattr(
        sharp_client,
        "get_cairo_pie_fact_info",
        lambda cairo_pie, program_hash: FactInfo(
            fact=f"hash({program_hash}, hash({cairo_pie.output}))",
            program_output=None,
            fact_topology=None,
        ),
    )

    assert client.get_fact(CairoPieStub("program", "output")) == "hash(hash(program), hash(output))"


def test_fact_registered():
    """
    Tests that fact_registered() checks facts as expected, using FactChecker mock.
    """

    class FactCheckerStub:
        def is_valid(self, fact: str) -> bool:
            return fact == "valid"

    client = SharpClient(
        service_client=None,
        contract_client=FactCheckerStub(),
        steps_limit=0,
        cairo_compiler_path="",
        cairo_run_path="",
    )

    assert client.fact_registered("valid")
    assert not client.fact_registered("not valid")


def test_job_failed():
    """
    Tests that job_failed() interacts with the SHARP service correctly, using ClientLib mock.
    """

    class ClientLibStub:
        def get_status(self, job_key):
            if job_key == "invalid_job":
                return "INVALID"
            if job_key == "failed_job":
                return "FAILED"
            return "Success"

    client = SharpClient(
        service_client=ClientLibStub(),
        contract_client=None,
        steps_limit=0,
        cairo_compiler_path="",
        cairo_run_path="",
    )

    # Test job_failed()
    assert client.job_failed("invalid_job")
    assert client.job_failed("failed_job")
    assert not client.job_failed("valid_job")

    # Test get_status()
    assert client.get_job_status("valid_job") == "Success"
    assert client.get_job_status("invalid_job") == "INVALID"
    assert client.get_job_status("failed_job") == "FAILED"
