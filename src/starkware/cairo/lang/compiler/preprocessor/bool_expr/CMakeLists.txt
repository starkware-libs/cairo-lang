full_python_test(cairo_compile_preprocessor_bool_expr_test
    PREFIX starkware/cairo/lang/compiler/preprocessor/bool_expr
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/cairo/lang/compiler/preprocessor/bool_expr

    FILES
    lowering_test.py

    LIBS
    cairo_compile_lib

    cairo_compile_test_utils_lib
)
