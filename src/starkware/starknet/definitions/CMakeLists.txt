python_lib(starknet_definitions_lib
    PREFIX starkware/starknet/definitions

    FILES
    constants.py
    error_codes.py
    fields.py
    transaction_type.py

    LIBS
    cairo_vm_crypto_lib
    starkware_crypto_lib
    starkware_storage_lib
    starkware_utils_lib
    pip_marshmallow
)

python_lib(starknet_general_config_lib
    PREFIX starkware/starknet/definitions

    FILES
    general_config.py
    general_config.yml

    LIBS
    starknet_definitions_lib
    starkware_utils_lib
    pip_marshmallow_dataclass
)
