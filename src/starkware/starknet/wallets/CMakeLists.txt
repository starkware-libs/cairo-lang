python_lib(starknet_wallets_lib
    PREFIX starkware/starknet/wallets

    FILES
    account.py
    starknet_context.py

    LIBS
    starknet_feeder_gateway_client_lib
    starknet_gateway_client_lib
    starkware_crypto_lib
)

python_lib(starknet_standard_wallets_lib
    PREFIX starkware/starknet/wallets

    FILES
    open_zeppelin.py

    LIBS
    open_zeppelin_contracts_lib
    starknet_wallets_lib
    starkware_crypto_lib
)
