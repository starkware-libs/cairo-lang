add_subdirectory(layouts)

python_lib(starkware_cairo_stark_verifier_air_lib
    PREFIX starkware/cairo/stark_verifier/air

    FILES
    config.cairo
    diluted.cairo
    layout.cairo
    oods.cairo
    params.cairo
    parser.py
    public_input.cairo
    public_memory.cairo
    traces.cairo
    utils.py

    LIBS
    starkware_cairo_stark_verifier_core_stark_lib
)

full_python_test(starkware_cairo_stark_verifier_air_test
    PREFIX starkware/cairo/stark_verifier/air
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/cairo/stark_verifier/air

    FILES
    example_proof.json
    stark_test.py

    LIBS
    cairo_common_lib
    cairo_common_validate_utils_lib
    cairo_compile_lib
    cairo_function_runner_lib
    starkware_cairo_stark_verifier_air_bitwise_lib
    starkware_cairo_stark_verifier_air_dex_lib
    starkware_cairo_stark_verifier_air_perpetual_with_bitwise_lib
    starkware_cairo_stark_verifier_air_recursive_lib
    starkware_cairo_stark_verifier_air_lib
    starkware_cairo_stark_verifier_core_stark_lib
    starkware_python_utils_lib
    pip_eth_hash
    pip_pytest
)
