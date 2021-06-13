python_lib(starknet_feeder_gateway_client_lib
    PREFIX starkware/starknet/services/api/feeder_gateway

    FILES
    feeder_gateway_client.py

    LIBS
    everest_feeder_gateway_client_lib
    starknet_transaction_lib
)
