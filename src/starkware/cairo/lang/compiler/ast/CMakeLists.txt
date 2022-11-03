full_python_test(cairo_compile_formatting_utils_test
    PREFIX starkware/cairo/lang/compiler/ast
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/cairo/lang/compiler/ast

    FILES
    formatting_utils_test.py

    LIBS
    cairo_compile_lib
    pip_pytest
)
