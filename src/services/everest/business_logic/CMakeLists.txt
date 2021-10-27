python_lib(everest_business_logic_lib
    PREFIX services/everest/business_logic

    FILES
    state.py

    LIBS
    starkware_config_utils_lib
    starkware_python_utils_lib
    starkware_storage_lib
    starkware_utils_lib
)

python_lib(everest_internal_transaction_lib
    PREFIX services/everest/business_logic

    FILES
    internal_transaction.py

    LIBS
    everest_business_logic_lib
    everest_transaction_lib
    starkware_config_utils_lib
    starkware_dataclasses_utils_lib
    pip_marshmallow
    pip_marshmallow_enum
    pip_marshmallow_oneofschema
)
