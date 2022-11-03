python_lib(starknet_common_lib
    PREFIX starkware/starknet/common

    FILES
    constants.cairo
    eth_utils.cairo
    messages.cairo
    storage.cairo
    syscalls.cairo

    LIBS
    cairo_common_lib
)

full_python_test(starknet_common_lib_test
    PREFIX starkware/starknet/common
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/starknet/common

    FILES
    storage_test.py
    eth_utils_test.py

    LIBS
    cairo_function_runner_lib
    starknet_abi_lib
    starknet_common_lib
    starkware_python_test_utils_lib
    pip_pytest
)
