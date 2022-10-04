python_lib(starknet_wallets_lib
    PREFIX starkware/starknet/wallets

    FILES
    account.py
    starknet_context.py

    LIBS
    starknet_contract_class_lib
    starknet_definitions_lib
    starknet_feeder_gateway_client_lib
    starknet_gateway_client_lib
    starknet_transaction_lib
    starkware_crypto_lib
)

python_lib(starknet_standard_wallets_lib
    PREFIX starkware/starknet/wallets

    FILES
    open_zeppelin.py

    LIBS
    cairo_common_lib
    open_zeppelin_contracts_lib
    services_external_api_lib
    starknet_abi_lib
    starknet_api_utils_lib
    starknet_contract_address_lib
    starknet_contract_class_lib
    starknet_definitions_lib
    starknet_feeder_gateway_response_objects_lib
    starknet_os_abi_lib
    starknet_transaction_hash_lib
    starknet_transaction_lib
    starknet_wallets_lib
    starkware_crypto_lib
)
