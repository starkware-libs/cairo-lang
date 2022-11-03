python_lib(starknet_block_hash_lib
    PREFIX starkware/starknet/core/os/block_hash

    FILES
    block_hash.py

    LIBS
    cairo_common_lib
    cairo_vm_crypto_lib
    starknet_general_config_lib
    starkware_python_utils_lib
    starkware_storage_lib
    starkware_storage_utils_lib
    starkware_utils_lib
)
