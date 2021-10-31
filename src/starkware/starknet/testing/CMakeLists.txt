python_lib(starknet_testing_lib
    PREFIX starkware/starknet/testing

    FILES
    contract.py
    contract_utils.py
    objects.py
    starknet.py
    state.py

    LIBS
    cairo_compile_lib
    cairo_vm_crypto_lib
    cairo_vm_lib
    starknet_abi_lib
    starknet_business_logic_lib
    starknet_compile_lib
    starknet_contract_definition_lib
    starknet_definitions_lib
    starknet_general_config_lib
    starknet_internal_transaction_interface_lib
    starknet_internal_transaction_lib
    starknet_messages_lib
    starknet_transaction_lib
    starkware_dataclasses_utils_lib
    starkware_python_utils_lib
    starkware_storage_lib
    pip_typeguard
)

full_python_test(starknet_testing_test
    PREFIX starkware/starknet/testing
    PYTHON python3.7
    TESTED_MODULES starkware/starknet/testing

    FILES
    contract_test.py
    starknet_test.py
    test.cairo

    LIBS
    cairo_common_lib
    starknet_testing_lib
    pip_pytest
    pip_pytest_asyncio
)
