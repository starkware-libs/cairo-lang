include(CMakeLists_common.txt)

python_lib(starkware_utils_lib
    PREFIX starkware/starkware_utils

    FILES
    commitment_tree/binary_fact_tree.py
    commitment_tree/binary_fact_tree_da_utils.py
    commitment_tree/binary_fact_tree_node.py
    commitment_tree/calculation.py
    commitment_tree/merkle_tree/traverse_tree.py
    commitment_tree/patricia_tree/virtual_calculation_node.py
    commitment_tree/patricia_tree/nodes.py
    commitment_tree/patricia_tree/patricia_tree.py
    commitment_tree/patricia_tree/virtual_patricia_node.py
    commitment_tree/update_tree.py
    executor.py
    subsequence.py
    ${STARKWARE_UTILS_LIBS_ADDITIONAL_FILES}

    LIBS
    starkware_commitment_tree_facts_lib
    starkware_config_utils_lib
    starkware_custom_dict_utils_lib
    starkware_dataclasses_field_utils_lib
    starkware_error_handling_lib
    starkware_python_utils_lib
    starkware_serializability_utils_lib
    starkware_storage_lib
    pip_marshmallow_dataclass
    ${STARKWARE_UTILS_LIBS_ADDITIONAL_LIBS}
)

full_python_test(patricia_tree_test
    PREFIX starkware/starkware_utils
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/starkware_utils

    FILES
    commitment_tree/patricia_tree/nodes_test.py
    commitment_tree/patricia_tree/patricia_tree_test.py
    commitment_tree/patricia_tree/virtual_calculation_node_test.py
    commitment_tree/patricia_tree/virtual_patricia_node_test.py

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
