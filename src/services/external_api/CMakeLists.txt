python_lib(services_external_api_lib
    PREFIX services/external_api

    FILES
    base_client.py
    has_uri_prefix.py
    ${SERVICES_EXTERNAL_API_LIB_ADDITIONAL_FILES}

    LIBS
    pip_aiohttp
    ${SERVICES_EXTERNAL_API_LIB_ADDITIONAL_LIBS}
)
