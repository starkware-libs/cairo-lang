add_subdirectory(bool_expr)

full_python_test(cairo_compile_preprocessor_test
    PREFIX starkware/cairo/lang/compiler/preprocessor
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/cairo/lang/compiler/preprocessor

    FILES
    compound_expressions_test.py
    conftest.py
    dependency_graph_test.py
    flow_test.py
    identifier_aware_visitor_test.py
    identifier_collector_test.py
    if_labels_test.py
    local_variables_test.py
    memento_test.py
    preprocessor_test.py
    reg_tracking_test.py
    struct_collector_test.py

    LIBS
    cairo_compile_lib
    cairo_compile_test_utils_lib
    pip_pytest
)
