add_subdirectory(time)

python_lib(starkware_serializability_utils_lib
    PREFIX starkware/starkware_utils

    FILES
    serializable.py
)

python_lib(starkware_utils_lib
    PREFIX starkware/starkware_utils

    FILES
    commitment_tree/binary_fact_tree.py
    commitment_tree/binary_fact_tree_node.py
    commitment_tree/merkle_tree/traverse_tree.py
    commitment_tree/patricia_tree/nodes.py
    commitment_tree/patricia_tree/patricia_tree.py
    commitment_tree/patricia_tree/virtual_patricia_node.py
    config_base.py
    custom_raising_dict.py
    error_handling.py
    field_validators.py
    marshmallow_dataclass_fields.py
    subsequence.py
    validated_dataclass.py
    validated_fields.py
    ${STARKWARE_UTILS_LIBS_ADDITIONAL_FILES}

    LIBS
    starkware_python_utils_lib
    starkware_serializability_utils_lib
    starkware_storage_lib
    pip_frozendict
    pip_marshmallow
    pip_marshmallow_dataclass
    pip_pyyaml
    pip_typeguard
    pip_web3
    ${STARKWARE_UTILS_LIBS_ADDITIONAL_LIBS}
)

full_python_test(patricia_tree_test
    PREFIX starkware/starkware_utils
    PYTHON python3.7
    TESTED_MODULES starkware/starkware_utils

    FILES
    commitment_tree/patricia_tree/nodes_test.py
    commitment_tree/patricia_tree/virtual_patricia_node_test.py

    LIBS
    cairo_common_lib
    starkware_crypto_lib
    starkware_python_utils_lib
    starkware_storage_lib
    starkware_storage_test_utils_lib
    starkware_utils_lib
    pip_pytest
    pip_pytest_asyncio
)
