full_python_test(cairo_compile_formatting_test
    PREFIX starkware/cairo/lang/compiler/ast
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/cairo/lang/compiler/ast

    FILES
    parentheses_expr_wrapper_test.py
    particle_test.py

    LIBS
    cairo_compile_lib
    cairo_compile_test_utils_lib
    pip_pytest
)
