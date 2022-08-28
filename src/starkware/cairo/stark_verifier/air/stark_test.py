import json
import os

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.common.validate_utils import validate_builtin_usage
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo_files
from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.stark_verifier.air.parser import parse_proof

PROOF_FILE = os.path.join(os.path.dirname(__file__), "example_proof.json")


def get_program_for_layout(layout: str) -> Program:
    return compile_cairo_files(
        [os.path.join(os.path.dirname(__file__), f"layouts/{layout}/verify.cairo")],
        prime=DEFAULT_PRIME,
        debug_info=True,
        main_scope=ScopedName.from_string(
            f"starkware.cairo.stark_verifier.air.layouts.{layout}.verify"
        ),
    )


def run_test(proof_file: str, layout: str):
    with open(proof_file, "r") as fp:
        proof_json = json.load(fp)
    program = get_program_for_layout(layout)
    proof = parse_proof(identifiers=program.identifiers, proof_json=proof_json)

    runner = CairoFunctionRunner(program, layout="small")
    runner.run(
        "verify_proof",
        range_check_ptr=runner.range_check_builtin.base,
        pedersen_ptr=runner.pedersen_builtin.base,
        bitwise_ptr=runner.bitwise_builtin.base,
        proof=proof,
        security_bits=80,
    )
    print("Steps:", runner.vm.current_step)
    (range_check_ptr, pedersen_ptr, bitwise_ptr) = runner.get_return_values(3)
    validate_builtin_usage(runner.range_check_builtin, range_check_ptr)
    validate_builtin_usage(runner.pedersen_builtin, pedersen_ptr)
    validate_builtin_usage(runner.bitwise_builtin, bitwise_ptr)


def test_stark():
    run_test(proof_file=PROOF_FILE, layout="recursive")
