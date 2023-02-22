full_python_test(json_rpc_client_test
    PREFIX starkware/python/json_rpc
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/python/json_rpc

    FILES
    client_test.py

    LIBS
    starkware_expression_string_lib
    starkware_json_rpc_lib
    starkware_python_test_utils_lib
    starkware_python_utils_lib
    pip_pytest
    pip_pytest_asyncio
)
