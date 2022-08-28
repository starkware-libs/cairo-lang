set(PROGRAM_ARTIFACTS)
add_custom_target(cairo_verifier_program_all_layouts)

function(cairo_verifier_layout LAYOUT_NAME)
    cairo_compile(cairo_verifier_program_${LAYOUT_NAME}
        cairo_verifier_compiled_${LAYOUT_NAME}.json
        layouts/${LAYOUT_NAME}/cairo_verifier.cairo
        "--no_debug_info --proof_mode"
    )
    set(
        PROGRAM_ARTIFACTS
        ${PROGRAM_ARTIFACTS}
        "${CMAKE_CURRENT_BINARY_DIR}/cairo_verifier_compiled_${LAYOUT_NAME}.json cairo_verifier_compiled_${LAYOUT_NAME}.json"
        PARENT_SCOPE
    )
    add_dependencies(cairo_verifier_program_all_layouts cairo_verifier_program_${LAYOUT_NAME})
endfunction()

cairo_verifier_layout(recursive)

full_python_test(cairo_verifier_program_hash_recursive_test
    PREFIX starkware/cairo/cairo_verifier/
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/cairo/cairo_verifier/

    FILES
    layouts/recursive/program_hash_test.py
    layouts/recursive/program_hash.json

    LIBS
    cairo_hash_program_lib
    program_hash_test_utils_lib
    starkware_python_utils_lib
    pip_pytest

    ARTIFACTS
    "${CMAKE_CURRENT_BINARY_DIR}/cairo_verifier_compiled_recursive.json cairo_verifier_compiled_recursive.json"
)
add_dependencies(cairo_verifier_program_hash_recursive_test_venv cairo_verifier_program_recursive)

python_exe(generate_cairo_verifier_program_hash_recursive
    VENV cairo_verifier_program_hash_recursive_test_venv
    MODULE starkware.cairo.cairo_verifier.layouts.recursive.program_hash_test
    ARGS "--fix"
)
