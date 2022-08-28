full_python_test(cairo_run_builtins_ec_op_test
    PREFIX starkware/cairo/lang/builtins/ec
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/cairo/lang/builtins/ec

    FILES
    ec_op_builtin_runner_test.py

    LIBS
    cairo_run_builtins_test_utils_lib
    cairo_vm_lib
    starkware_crypto_lib
    starkware_python_utils_lib
    pip_pytest
)
