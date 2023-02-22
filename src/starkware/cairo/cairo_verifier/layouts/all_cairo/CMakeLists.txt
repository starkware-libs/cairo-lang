full_python_test(cairo_verifier_program_hash_all_cairo_test
    PREFIX starkware/cairo/cairo_verifier/layouts/all_cairo
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/cairo/cairo_verifier/layouts/all_cairo

    FILES
    program_hash.json
    program_hash_test.py

    LIBS
    cairo_hash_program_lib
    program_hash_test_utils_lib
    pip_pytest

    ARTIFACTS
    "${CMAKE_BINARY_DIR}/src/starkware/cairo/cairo_verifier/cairo_verifier_compiled_all_cairo.json cairo_verifier_compiled_all_cairo.json"
)

add_dependencies(cairo_verifier_program_hash_all_cairo_test_lib cairo_verifier_program_all_cairo)

python_exe(generate_cairo_verifier_program_hash_all_cairo
    VENV cairo_verifier_program_hash_all_cairo_test_venv
    MODULE starkware.cairo.cairo_verifier.layouts.all_cairo.program_hash_test
    ARGS "--fix"
)
