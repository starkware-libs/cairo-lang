python_lib(starkware_python_utils_lib
    PREFIX starkware/python
    FILES
    async_subprocess.py
    math_utils.py
    object_utils.py
    python_dependencies.py
    utils.py
    utils_stub_module.py
    utils_stub_module.pyi

    LIBS
    pip_pyyaml
    pip_sympy
    pip_typing_extensions
)

python_lib(starkware_expression_string_lib
    PREFIX starkware/python
    FILES
    expression_string.py
)

python_lib(starkware_json_rpc_lib
    PREFIX starkware/python
    FILES
    json_rpc/client.py
)

python_lib(starkware_merkle_tree_lib
    PREFIX starkware/python
    FILES
    merkle_tree.py
)

python_lib(starkware_python_test_utils_lib
    PREFIX starkware/python
    FILES
    random_test.py
    test_utils.py
    LIBS
    pip_mypy_extensions
    pip_pytest
)

full_python_test(starkware_python_utils_test
    PREFIX starkware/python
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/python

    FILES
    expression_string_test.py
    json_rpc/client_test.py
    math_utils_test.py
    test_utils_test.py
    utils_test.py

    LIBS
    starkware_expression_string_lib
    starkware_json_rpc_lib
    starkware_python_test_utils_lib
    starkware_python_utils_lib
    pip_pytest
    pip_pytest_asyncio
)
