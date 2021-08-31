python_lib(starknet_storage_lib
    PREFIX starkware/starknet/storage

    FILES
    starknet_storage.py

    LIBS
    cairo_constants_lib
    starkware_storage_lib
    starkware_utils_lib
)
