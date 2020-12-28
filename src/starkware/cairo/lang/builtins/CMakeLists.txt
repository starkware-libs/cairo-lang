python_lib(cairo_run_builtins_lib
    PREFIX starkware/cairo/lang/builtins

    FILES
    checkpoints/instance_def.py
    checkpoints/checkpoints_builtin_runner.py
    hash/hash_builtin_runner.py
    hash/instance_def.py
    range_check/instance_def.py
    range_check/range_check_builtin_runner.py
    signature/instance_def.py
    signature/signature_builtin_runner.py

    LIBS
    cairo_relocatable
    cairo_vm_lib
    starkware_python_utils_lib
)

python_lib(cairo_run_builtins_test_utils_lib
    PREFIX starkware/cairo/lang/builtins
    FILES
    builtin_runner_test_utils.py

    LIBS
    cairo_compile_lib
    cairo_run_lib
)

full_python_test(cairo_run_builtins_test
    PREFIX starkware/cairo/lang/builtins
    PYTHON python3.7
    TESTED_MODULES starkware/cairo/lang/builtins

    FILES
    range_check/range_check_builtin_runner_test.py
    signature/signature_builtin_runner_test.py

    LIBS
    cairo_common_lib
    cairo_compile_lib
    cairo_run_lib
    cairo_run_builtins_lib
    cairo_run_builtins_test_utils_lib
    starkware_python_test_utils_lib
    pip_pytest
)
