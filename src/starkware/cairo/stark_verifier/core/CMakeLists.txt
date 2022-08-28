add_subdirectory(fri)

python_lib(starkware_cairo_stark_verifier_core_lib
    PREFIX starkware/cairo/stark_verifier/core
    FILES
    air_interface.cairo
    channel.cairo
    proof_of_work.cairo
    queries.cairo
    table_commitment.cairo
    utils.cairo
    vector_commitment.cairo

    LIBS
    cairo_common_lib
)

python_lib(starkware_cairo_stark_verifier_core_stark_lib
    PREFIX starkware/cairo/stark_verifier/core
    FILES
    config.cairo
    domains.cairo
    stark.cairo

    LIBS
    cairo_common_lib
    starkware_cairo_stark_verifier_core_fri_lib
    starkware_cairo_stark_verifier_core_lib
)

full_python_test(starkware_cairo_stark_verifier_core_test
    PREFIX starkware/cairo/stark_verifier/core
    PYTHON  python3.9

    FILES
    channel_test.cairo
    channel_test.py
    merkle_test_data.json
    proof_of_work_test.py
    table_commitment_test.py
    utils_test.py
    vector_commitment_test.py

    LIBS
    cairo_common_lib
    cairo_common_validate_utils_lib
    cairo_compile_lib
    cairo_function_runner_lib
    starkware_cairo_stark_verifier_core_lib
    starkware_python_test_utils_lib
    pip_pytest
)
