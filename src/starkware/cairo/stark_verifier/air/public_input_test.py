import itertools
import json
import os

import pytest

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.common.structs import CairoStructFactory
from starkware.cairo.common.validate_utils import validate_builtin_usage
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo_files
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.vm.air_public_input import (
    PublicInput,
    extract_z_and_alpha,
    get_pages_and_products,
)
from starkware.cairo.stark_verifier.air.parser import parse_proof
from starkware.cairo.stark_verifier.air.utils import (
    compute_continuous_page_headers,
    public_input_to_cairo,
)
from starkware.python.math_utils import safe_div

CAIRO_FILE = os.path.join(os.path.dirname(__file__), "public_input.cairo")
PROOF_FILE = os.path.join(os.path.dirname(__file__), "example_proof.json")
DYNAMIC_LAYOUT_PROOF_FILE = "src/starkware/cairo/stark_verifier/air/dynamic_layout_proof.json"
EXPECTED_FILE = os.path.join(os.path.dirname(__file__), "example_expected.json")


@pytest.fixture(scope="session")
def program():
    return compile_cairo_files(
        [CAIRO_FILE],
        prime=DEFAULT_PRIME,
        debug_info=True,
        main_scope=ScopedName.from_string("starkware.cairo.stark_verifier.air.public_input"),
    )


@pytest.fixture
def structs(program):
    return CairoStructFactory.from_program(
        program,
        additional_imports=[
            "starkware.cairo.stark_verifier.air.public_input.PublicInput",
            "starkware.cairo.stark_verifier.air.public_input.SegmentInfo",
            "starkware.cairo.stark_verifier.air.public_memory.ContinuousPageHeader",
            "starkware.cairo.stark_verifier.core.air_instances.AirInstance",
        ],
    ).structs


@pytest.mark.parametrize(
    "proof_file, expected_json_key",
    [
        (PROOF_FILE, "public_input_test"),
        (DYNAMIC_LAYOUT_PROOF_FILE, "dynamic_layout_public_input_test"),
    ],
)
def test_public_input_to_cairo(program, structs, proof_file, expected_json_key):
    with open(proof_file, "r") as fp:
        proof_json = json.load(fp)
    z, alpha = extract_z_and_alpha(proof_json["annotations"])
    public_input: PublicInput = PublicInput.Schema().load(proof_json["public_input"])
    cairo_public_input = public_input_to_cairo(
        structs=structs, public_input=public_input, z=z, alpha=alpha
    )
    air_instance = structs.AirInstance(
        public_input_hash=0,
        public_input_validate=0,
        traces_config_validate=0,
        traces_commit=0,
        traces_decommit=0,
        traces_eval_composition_polynomial=0,
        eval_oods_boundary_poly_at_points=0,
        n_dynamic_params=len(public_input.dynamic_params)
        if public_input.dynamic_params is not None
        else 0,
        n_constraints=0,
        constraint_degree=0,
        mask_size=0,
    )

    runner = CairoFunctionRunner(program, layout="small")
    extra_const_params = {
        "cpu_component_step": 1,
        "constraint_degree": 2,
        "num_columns_first": 23,
        "num_columns_second": 2,
    }
    proof_config = parse_proof(
        identifiers=program.identifiers,
        proof_json=proof_json,
        only_config=True,
        extra_params=extra_const_params,
    )
    runner.run(
        "public_input_hash",
        range_check_ptr=runner.range_check_builtin.base,
        pedersen_ptr=runner.pedersen_builtin.base,
        poseidon_ptr=runner.poseidon_builtin.base,
        air=air_instance,
        public_input=cairo_public_input,
        config=proof_config,
    )
    (
        range_check_ptr,
        pedersen_ptr,
        poseidon_ptr,
        res,
    ) = runner.get_return_values(4)
    validate_builtin_usage(runner.range_check_builtin, range_check_ptr)
    validate_builtin_usage(runner.pedersen_builtin, pedersen_ptr)
    validate_builtin_usage(runner.poseidon_builtin, poseidon_ptr)

    # Note: This value is also checked in the C++ implementation.
    with open(EXPECTED_FILE, "r") as fp:
        expected_json = json.load(fp)[expected_json_key]
    assert "0x" + res.to_bytes(32, "big").hex() == expected_json["initial_hash_chain_seed"]


def test_public_input_page_product(program):
    with open(PROOF_FILE, "r") as fp:
        proof_json = json.load(fp)
    public_input: PublicInput = PublicInput.Schema().load(proof_json["public_input"])
    z, alpha = extract_z_and_alpha(proof_json["annotations"])
    pages, page_prods = get_pages_and_products(
        public_memory=public_input.public_memory, z=z, alpha=alpha
    )

    runner = CairoFunctionRunner(program, layout="small")
    runner.run(
        "get_page_product",
        z=z,
        alpha=alpha,
        data_len=safe_div(len(pages[0]), 2),
        data=pages[0],
    )
    (res,) = runner.get_return_values(1)
    assert res == page_prods[0]


def test_public_input_continuous_pages_product(program):
    with open(PROOF_FILE, "r") as fp:
        proof_json = json.load(fp)
    public_input: PublicInput = PublicInput.Schema().load(proof_json["public_input"])
    z, alpha = extract_z_and_alpha(proof_json["annotations"])
    _, page_prods = get_pages_and_products(
        public_memory=public_input.public_memory, z=z, alpha=alpha
    )

    continuous_page_headers = compute_continuous_page_headers(
        public_memory=public_input.public_memory, z=z, alpha=alpha
    )
    n_continuous_pages = len(continuous_page_headers)
    continuous_page_headers_cairo = list(itertools.chain(*continuous_page_headers))

    runner = CairoFunctionRunner(program, layout="small")
    runner.run(
        "get_continuous_pages_product",
        n_pages=n_continuous_pages,
        page_headers=continuous_page_headers_cairo,
    )
    (res, total_length) = runner.get_return_values(2)
    expected_prod = 1
    expected_length = sum(size for (_, size, _, _) in continuous_page_headers)
    for page, prod in page_prods.items():
        if page != 0:
            expected_prod = (expected_prod * prod) % DEFAULT_PRIME
    assert res == expected_prod
    assert total_length == expected_length
