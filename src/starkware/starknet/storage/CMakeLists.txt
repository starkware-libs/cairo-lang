python_lib(starknet_storage_lib
    PREFIX starkware/starknet/storage

    FILES
    starknet_storage.py

    LIBS
    cairo_constants_lib
    starknet_definitions_lib
    starkware_commitment_tree_facts_lib
    starkware_dataclasses_utils_lib
    starkware_python_utils_lib
    starkware_storage_lib
    starkware_utils_lib
)
