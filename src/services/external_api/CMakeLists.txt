python_lib(services_external_api_utils_lib
    PREFIX services/external_api

    FILES
    utils.py
)

python_lib(services_external_api_lib
    PREFIX services/external_api

    FILES
    client.py
    has_uri_prefix.py
    ${SERVICES_EXTERNAL_API_LIB_ADDITIONAL_FILES}

    LIBS
    services_external_api_utils_lib
    starkware_dataclasses_field_utils_lib
    starkware_python_utils_lib
    pip_aiohttp
    ${SERVICES_EXTERNAL_API_LIB_ADDITIONAL_LIBS}
)

python_lib(services_eth_gas_constants_lib
    PREFIX services/external_api

    FILES
    eth_gas_constants.py
)
