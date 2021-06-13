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
    starkware_utils_lib
    pip_marshmallow_oneofschema
)

python_lib(everest_gateway_client_lib
    PREFIX services/everest/api/gateway

    FILES
    gateway_client.py

    LIBS
    everest_transaction_lib
    services_external_api_lib
)
