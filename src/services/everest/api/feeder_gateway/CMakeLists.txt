python_lib(everest_feeder_gateway_client_lib
    PREFIX services/everest/api/feeder_gateway

    FILES
    feeder_gateway_client.py

    LIBS
    services_external_api_lib
)

python_lib(everest_feeder_gateway_response_objects_lib
    PREFIX services/everest/api/feeder_gateway

    FILES
    response_objects.py

    LIBS
    starkware_dataclasses_field_utils_lib
    pip_marshmallow
)
