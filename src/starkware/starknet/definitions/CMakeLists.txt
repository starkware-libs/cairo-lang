python_lib(starknet_definitions_lib
    PREFIX starkware/starknet/definitions

    FILES
    constants.py
    error_codes.py
    fields.py
    transaction_type.py

    LIBS
    cairo_vm_crypto_lib
    everest_definitions_lib
    starkware_crypto_lib
    starkware_dataclasses_utils_lib
    starkware_error_handling_lib
    starkware_python_utils_lib
    starkware_storage_lib
    pip_marshmallow
)

python_lib(starknet_general_config_lib
    PREFIX starkware/starknet/definitions

    FILES
    general_config.py
    general_config.yml

    LIBS
    cairo_instances_lib
    cairo_run_builtins_lib
    everest_general_config_lib
    starknet_definitions_lib
    starkware_config_utils_lib
    starkware_dataclasses_utils_lib
    starkware_python_utils_lib
    pip_marshmallow
    pip_marshmallow_dataclass
    pip_marshmallow_enum
)
