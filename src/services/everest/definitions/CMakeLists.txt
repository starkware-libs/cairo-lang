python_lib(everest_definitions_lib
    PREFIX services/everest/definitions

    FILES
    constants.py
    fields.py

    LIBS
    starkware_crypto_lib
    starkware_dataclasses_field_utils_lib
    starkware_error_handling_lib
    pip_marshmallow
    pip_web3
)

python_lib(everest_general_config_lib
    PREFIX services/everest/definitions

    FILES
    general_config.py

    LIBS
    starkware_config_utils_lib
    pip_marshmallow_dataclass
)
