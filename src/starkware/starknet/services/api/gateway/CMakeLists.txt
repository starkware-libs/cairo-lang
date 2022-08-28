python_lib(starknet_transaction_lib
    PREFIX starkware/starknet/services/api/gateway

    FILES
    transaction.py

    LIBS
    everest_transaction_lib
    starknet_abi_lib
    starknet_contract_address_lib
    starknet_contract_class_lib
    starknet_definitions_lib
    starknet_general_config_lib
    starknet_transaction_hash_lib
    starknet_transaction_utils_lib
    pip_marshmallow
    pip_marshmallow_dataclass
    pip_marshmallow_enum
    pip_marshmallow_oneofschema
)

python_lib(starknet_transaction_utils_lib
    PREFIX starkware/starknet/services/api/gateway

    FILES
    transaction_utils.py

    LIBS
    services_external_api_lib
    starknet_definitions_lib
    starkware_error_handling_lib
)

python_lib(starknet_gateway_client_lib
    PREFIX starkware/starknet/services/api/gateway

    FILES
    gateway_client.py

    LIBS
    everest_gateway_client_lib
    starknet_transaction_lib
)
