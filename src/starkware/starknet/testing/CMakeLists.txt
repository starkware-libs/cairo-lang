python_lib(starknet_mock_messaging_sol
    PREFIX starkware/starknet/testing
    FILES
    MockStarknetMessaging.sol

    LIBS
    starknet_messaging_sol
)

solidity_env(mock_starknet_messaging_sol_env
    CONTRACTS
    MockStarknetMessaging

    LIBS
    starknet_mock_messaging_sol
)

python_lib(starknet_mock_messaging_contracts_lib
    PREFIX starkware/starknet/testing
    FILES
    contracts.py

    LIBS
    starkware_contracts_utils_lib

    ARTIFACTS
    "${CMAKE_CURRENT_BINARY_DIR}/MockStarknetMessaging.json MockStarknetMessaging.json"
)
add_dependencies(starknet_mock_messaging_contracts_lib mock_starknet_messaging_sol_env)

python_lib(starknet_testing_lib
    PREFIX starkware/starknet/testing

    FILES
    contract.py
    contract_utils.py
    objects.py
    postman.py
    starknet.py
    state.py

    LIBS
    cairo_compile_lib
    cairo_vm_crypto_lib
    cairo_vm_lib
    starknet_abi_lib
    starknet_api_utils_lib
    starknet_business_logic_fact_state_lib
    starknet_business_logic_patricia_state_lib
    starknet_business_logic_state_lib
    starknet_compile_lib
    starknet_contract_class_lib
    starknet_definitions_lib
    starknet_execute_entry_point_lib
    starknet_feeder_gateway_response_objects_lib
    starknet_general_config_lib
    starknet_transaction_objects_lib
    starknet_messages_lib
    starknet_mock_messaging_contracts_lib
    starknet_os_abi_lib
    starknet_transaction_execution_objects_lib
    starknet_transaction_lib
    starkware_dataclasses_utils_lib
    starkware_eth_test_utils_lib
    starkware_python_utils_lib
    starkware_storage_lib
    pip_typeguard
)

full_python_test(starknet_testing_test
    PREFIX starkware/starknet/testing
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/starknet/testing

    FILES
    conftest.py
    contract_test.py
    mock_starknet_messaging_test.py
    postman_test.py
    starknet_test.py
    test.cairo
    test_unwhitelisted_hint.cairo

    LIBS
    cairo_common_lib
    starknet_mock_messaging_contracts_lib
    starknet_test_external_contract_test_utils_lib
    starknet_testing_lib
    starkware_eth_test_utils_lib
    pip_pytest
    pip_pytest_asyncio
)
