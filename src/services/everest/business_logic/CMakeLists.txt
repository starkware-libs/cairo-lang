python_lib(everest_business_logic_state_api_lib
    PREFIX services/everest/business_logic

    FILES
    state_api.py
)

python_lib(everest_business_logic_lib
    PREFIX services/everest/business_logic

    FILES
    state.py

    LIBS
    everest_business_logic_state_api_lib
    starkware_config_utils_lib
    starkware_dataclasses_field_utils_lib
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
    everest_business_logic_state_api_lib
    everest_transaction_execution_objects_lib
    everest_transaction_lib
    starkware_config_utils_lib
    starkware_one_of_schema_utils_lib
)

python_lib(everest_transaction_execution_objects_lib
    PREFIX services/everest/business_logic

    FILES
    transaction_execution_objects.py

    LIBS
    starkware_dataclasses_field_utils_lib
    pip_marshmallow
    pip_marshmallow_dataclass
)
