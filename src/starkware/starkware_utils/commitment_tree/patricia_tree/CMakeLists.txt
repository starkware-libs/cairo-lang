full_python_test(patricia_tree_test
    PREFIX starkware/starkware_utils/commitment_tree/patricia_tree
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/starkware_utils/commitment_tree/patricia_tree

    FILES
    nodes_test.py
    patricia_tree_test.py
    virtual_calculation_node_test.py
    virtual_patricia_node_test.py

    LIBS
    cairo_common_lib
    starkware_crypto_lib
    starkware_python_test_utils_lib
    starkware_python_utils_lib
    starkware_storage_lib
    starkware_storage_test_utils_lib
    starkware_storage_utils_lib
    starkware_utils_lib
    pip_pytest
    pip_pytest_asyncio
)
