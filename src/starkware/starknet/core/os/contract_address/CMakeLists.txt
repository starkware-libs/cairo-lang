python_lib(starknet_contract_address_lib
    PREFIX starkware/starknet/core/os/contract_address

    FILES
    contract_address.py
    contract_address.cairo

    LIBS
    cairo_common_lib
    cairo_vm_crypto_lib
    starknet_common_lib
    starknet_contract_class_lib
    starknet_definitions_lib
    starknet_os_abi_lib
    starkware_python_utils_lib
)

full_python_test(starknet_contract_address_cairo_test
    PREFIX starkware/starknet/core/os/contract_address
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/starknet/core/os/contract_address

    FILES
    contract_address_cairo_test.py

    LIBS
    cairo_common_lib
    cairo_function_runner_lib
    starknet_contract_address_lib
    starknet_os_utils_lib
    starknet_transaction_hash_lib
    starkware_crypto_lib
    pip_pytest
    pip_pytest_asyncio
)
