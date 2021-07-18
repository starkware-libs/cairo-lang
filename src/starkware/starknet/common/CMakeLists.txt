python_lib(starknet_common_lib
    PREFIX starkware/starknet/common

    FILES
    messages.cairo
    storage.cairo
    syscalls.cairo
)

full_python_test(starknet_common_lib_test
    PREFIX starkware/starknet/common
    PYTHON python3.7
    TESTED_MODULES starkware/starknet/common

    FILES
    storage_test.py

    LIBS
    cairo_function_runner_lib
    starknet_abi_lib
    starknet_common_lib
    pip_pytest
)
