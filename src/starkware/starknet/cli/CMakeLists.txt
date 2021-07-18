python_lib(starknet_cli_lib
    PREFIX starkware/starknet/cli

    FILES
    starknet_cli.py

    LIBS
    cairo_compile_lib
    cairo_version_lib
    cairo_vm_utils_lib
    services_external_api_lib
    starknet_compile_lib
    starknet_contract_definition_lib
    starknet_definitions_lib
    starknet_feeder_gateway_client_lib
    starknet_gateway_client_lib
    starknet_transaction_lib
    starkware_utils_lib
)

python_venv(starknet_cli_venv
    PYTHON python3.7

    LIBS
    starknet_cli_lib
)

python_exe(starknet_cli
    VENV starknet_cli_venv
    MODULE starkware.starknet.cli.starknet_cli
)
