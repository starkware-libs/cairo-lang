python_lib(starkware_cairo_stark_verifier_core_fri_lib
    PREFIX starkware/cairo/stark_verifier/core/fri
    FILES
    config.cairo
    fri.cairo
    fri_formula.cairo
    fri_layer.cairo

    LIBS
    cairo_common_lib
    starkware_cairo_stark_verifier_core_lib
)

full_python_test(starkware_cairo_stark_verifier_core_fri_test
    PREFIX starkware/cairo/stark_verifier/core/fri
    PYTHON  python3.9

    FILES
    fri_formula_test.py
    fri_layer_test.py
    fri_test.py
    test_utils.py

    LIBS
    cairo_compile_lib
    cairo_function_runner_lib
    starkware_cairo_stark_verifier_core_fri_lib
    starkware_python_test_utils_lib
    pip_pytest
)
