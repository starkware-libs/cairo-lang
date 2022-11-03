python_lib(starknet_feeder_gateway_client_lib
    PREFIX starkware/starknet/services/api/feeder_gateway

    FILES
    feeder_gateway_client.py

    LIBS
    everest_feeder_gateway_client_lib
    services_external_api_lib
    starknet_definitions_lib
    starknet_feeder_gateway_request_objects_lib
    starknet_feeder_gateway_response_objects_lib
    starknet_transaction_lib
    starkware_dataclasses_utils_lib
    pip_typing_extensions
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
    starknet_contract_class_lib
    starknet_definitions_lib
    starknet_transaction_objects_lib
    starknet_transaction_execution_objects_lib
    starkware_dataclasses_field_utils_lib
    starkware_dataclasses_utils_lib
    starkware_python_utils_lib
    pip_marshmallow
    pip_marshmallow_dataclass
    pip_marshmallow_enum
    pip_marshmallow_oneofschema
    pip_typing_extensions
    pip_web3
)

python_lib(starknet_feeder_gateway_request_objects_lib
    PREFIX starkware/starknet/services/api/feeder_gateway

    FILES
    request_objects.py

    LIBS
    everest_definitions_lib
    starknet_definitions_lib
    starknet_execute_entry_point_lib
    starknet_transaction_objects_lib
    starkware_dataclasses_utils_lib
    pip_marshmallow_dataclass
)
