python_lib(everest_transaction_type_lib
    PREFIX services/everest/api/gateway

    FILES
    transaction_type.py
)

python_lib(everest_transaction_lib
    PREFIX services/everest/api/gateway

    FILES
    transaction.py

    LIBS
    starkware_dataclasses_field_utils_lib
    pip_marshmallow_enum
    pip_marshmallow_oneofschema
)

python_lib(everest_config_request_lib
    PREFIX services/everest/api/gateway

    FILES
    set_config_request.py

    LIBS
    starkware_dataclasses_field_utils_lib
    starkware_dataclasses_utils_lib
    starkware_error_handling_lib
)

python_lib(everest_gateway_client_lib
    PREFIX services/everest/api/gateway

    FILES
    gateway_client.py

    LIBS
    everest_transaction_lib
    services_external_api_lib
)
