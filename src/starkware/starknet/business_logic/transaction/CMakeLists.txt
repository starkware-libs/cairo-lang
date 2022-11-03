python_lib(starknet_transaction_objects_lib
    PREFIX starkware/starknet/business_logic/transaction

    FILES
    objects.py

    LIBS
    everest_business_logic_lib
    everest_business_logic_state_api_lib
    everest_internal_transaction_lib
    everest_transaction_lib
    starknet_abi_lib
    starknet_business_logic_fact_state_lib
    starknet_business_logic_patricia_state_lib
    starknet_business_logic_state_lib
    starknet_business_logic_utils_lib
    starknet_contract_address_lib
    starknet_contract_class_lib
    starknet_definitions_lib
    starknet_execute_entry_point_lib
    starknet_general_config_lib
    starknet_transaction_state_objects_lib
    starknet_os_abi_lib
    starknet_os_utils_lib
    starknet_transaction_execution_objects_lib
    starknet_transaction_fee_lib
    starknet_transaction_hash_lib
    starknet_transaction_lib
    starkware_config_utils_lib
    starkware_dataclasses_field_utils_lib
    starkware_error_handling_lib
    starkware_python_utils_lib
    starkware_storage_lib
    pip_marshmallow
    pip_marshmallow_dataclass
    pip_marshmallow_enum
    pip_marshmallow_oneofschema
)

python_lib(starknet_transaction_state_objects_lib
    PREFIX starkware/starknet/business_logic/transaction

    FILES
    state_objects.py

    LIBS
    cairo_vm_lib
    everest_business_logic_lib
    everest_business_logic_state_api_lib
    everest_internal_transaction_lib
    everest_transaction_lib
    starknet_business_logic_fact_state_lib
    starknet_business_logic_patricia_state_lib
    starknet_business_logic_state_lib
    starknet_definitions_lib
    starknet_general_config_lib
    starknet_transaction_lib
    starknet_transaction_execution_objects_lib
    starkware_config_utils_lib
    starkware_error_handling_lib
)

python_lib(starknet_transaction_fee_lib
    PREFIX starkware/starknet/business_logic/transaction

    FILES
    fee.py

    LIBS
    starknet_abi_lib
    starknet_business_logic_fact_state_lib
    starknet_business_logic_state_lib
    starknet_business_logic_utils_lib
    starknet_contract_class_lib
    starknet_definitions_lib
    starknet_execute_entry_point_lib
    starknet_general_config_lib
    starknet_transaction_execution_objects_lib
    starkware_error_handling_lib
)
