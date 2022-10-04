add_subdirectory(ec)
add_subdirectory(range_check)
add_subdirectory(signature)

python_lib(cairo_run_builtins_lib
    PREFIX starkware/cairo/lang/builtins

    FILES
    bitwise/bitwise_builtin_runner.py
    bitwise/instance_def.py
    ec/ec_op_builtin_runner.py
    ec/instance_def.py
    hash/hash_builtin_runner.py
    hash/instance_def.py
    keccak/keccak_builtin_runner.py
    keccak/instance_def.py
    range_check/instance_def.py
    range_check/range_check_builtin_runner.py
    signature/instance_def.py
    signature/signature_builtin_runner.py

    LIBS
    cairo_common_lib
    cairo_relocatable_lib
    cairo_vm_lib
    starkware_python_utils_lib
)

python_lib(cairo_all_builtins_lib
    PREFIX starkware/cairo/lang/builtins

    FILES
    all_builtins.py
)

python_lib(cairo_run_builtins_test_utils_lib
    PREFIX starkware/cairo/lang/builtins
    FILES
    builtin_runner_test_utils.py

    LIBS
    cairo_compile_lib
    cairo_run_lib
)
