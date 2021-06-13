python_lib(starknet_cairo_storage_lib
    PREFIX starkware/starknet/core/storage

    FILES
    storage.cairo
)

full_python_test(starknet_cairo_storage_lib_test
    PREFIX starkware/starknet/core/storage
    PYTHON python3.7
    TESTED_MODULES starkware/starknet/core/storage

    FILES
    storage_test.py

    LIBS
    cairo_function_runner_lib
    starknet_cairo_storage_lib
    pip_pytest
)
