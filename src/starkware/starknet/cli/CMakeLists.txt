python_lib(starknet_cli_utils_lib
    PREFIX starkware/starknet/cli

    FILES
    starknet_cli_utils.py

    LIBS
    cairo_compile_lib
    services_external_api_lib
    starknet_abi_lib
    starknet_contract_class_lib
    starknet_definitions_lib
    starknet_feeder_gateway_client_lib
    starknet_feeder_gateway_response_objects_lib
    starknet_feeder_gateway_request_objects_lib
    starknet_gateway_client_lib
    starknet_general_config_lib
    starknet_transaction_lib
    starknet_wallets_lib
    starkware_error_handling_lib
    starkware_python_utils_lib
)

python_lib(starknet_cli_lib
    PREFIX starkware/starknet/cli

    FILES
    class_hash.py
    compiled_class_hash.py
    reconstruct_starknet_traceback.py
    starknet_cli.py

    LIBS
    cairo_compile_lib
    cairo_version_lib
    cairo_vm_crypto_lib
    cairo_vm_utils_lib
    everest_definitions_lib
    starknet_abi_lib
    starknet_api_utils_lib
    starknet_cli_utils_lib
    starknet_compile_lib
    starknet_contract_class_lib
    starknet_contract_class_utils_lib
    starknet_definitions_lib
    starknet_feeder_gateway_client_lib
    starknet_feeder_gateway_request_objects_lib
    starknet_feeder_gateway_response_objects_lib
    starknet_gateway_client_lib
    starknet_general_config_lib
    starknet_os_abi_lib
    starknet_standard_wallets_lib
    starknet_transaction_lib
    starknet_wallets_lib
    starkware_python_utils_lib
    pip_eth_utils
)

python_venv(starknet_cli_venv
    PYTHON ${PYTHON_COMMAND}

    LIBS
    starknet_cli_lib
)

python_exe(starknet_cli
    VENV starknet_cli_venv
    MODULE starkware.starknet.cli.starknet_cli
)

full_python_test(starknet_cli_lib_test
    PREFIX starkware/starknet/cli
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/starknet/cli

    FILES
    reconstruct_starknet_traceback_test.py

    LIBS
    starknet_cli_lib
    cairo_constants_lib
    pip_pytest
)
