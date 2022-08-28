full_python_test(starknet_transaction_hash_test
    PREFIX starkware/starknet/core/os/transaction_hash
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/starknet/core/os/transaction_hash

    FILES
    transaction_hash_test.py

    LIBS
    cairo_common_lib
    cairo_function_runner_lib
    starknet_abi_lib
    starknet_definitions_lib
    starknet_os_abi_lib
    starknet_os_utils_lib
    starknet_test_external_contract_test_utils_lib
    starknet_transaction_hash_lib
    starkware_crypto_lib
    pip_pytest
    pip_pytest_asyncio
)

python_lib(starknet_transaction_hash_lib
    PREFIX starkware/starknet/core/os/transaction_hash

    FILES
    transaction_hash.py

    LIBS
    cairo_common_lib
    cairo_vm_crypto_lib
    starknet_abi_lib
    starknet_contract_class_lib
    starknet_definitions_lib
    starknet_os_abi_lib
    starkware_python_utils_lib
)
