python_lib(starknet_feeder_gateway_client_lib
    PREFIX starkware/starknet/services/api/feeder_gateway

    FILES
    feeder_gateway_client.py

    LIBS
    everest_feeder_gateway_client_lib
    starknet_definitions_lib
    starknet_feeder_gateway_response_objects_lib
    starknet_transaction_lib
    starkware_dataclasses_utils_lib
    pip_typing_extensions
)

python_lib(starknet_block_hash_lib
    PREFIX starkware/starknet/services/api/feeder_gateway

    FILES
    block_hash.py

    LIBS
    cairo_common_lib
    cairo_vm_crypto_lib
    starknet_general_config_lib
    starkware_python_utils_lib
    starkware_storage_lib
    starkware_storage_utils_lib
    starkware_utils_lib
)

python_lib(starknet_feeder_gateway_response_objects_lib
    PREFIX starkware/starknet/services/api/feeder_gateway

    FILES
    response_objects.py

    LIBS
    cairo_vm_lib
    everest_definitions_lib
    everest_feeder_gateway_response_objects_lib
    everest_transaction_execution_objects_lib
    starknet_contract_definition_lib
    starknet_definitions_lib
    starknet_internal_transaction_lib
    starknet_transaction_execution_objects_lib
    starkware_dataclasses_utils_lib
    pip_marshmallow
    pip_marshmallow_dataclass
    pip_marshmallow_enum
    pip_marshmallow_oneofschema
    pip_typing_extensions
)
