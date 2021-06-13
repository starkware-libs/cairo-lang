python_lib(starknet_transaction_lib
    PREFIX starkware/starknet/services/api/gateway

    FILES
    transaction.py

    LIBS
    everest_definitions_lib
    everest_transaction_lib
    pip_marshmallow
    starknet_contract_definition_lib
    starknet_definitions_lib
    pip_marshmallow_dataclass
    pip_marshmallow_enum
    pip_marshmallow_oneofschema
)

python_lib(starknet_gateway_client_lib
    PREFIX starkware/starknet/services/api/gateway

    FILES
    gateway_client.py

    LIBS
    everest_gateway_client_lib
    starknet_transaction_lib
)
