add_subdirectory(execution)
add_subdirectory(state)

python_lib(starknet_business_logic_utils_lib
    PREFIX starkware/starknet/business_logic

    FILES
    utils.py

    LIBS
    cairo_function_runner_lib
    starknet_abi_lib
    starknet_business_logic_state_lib
    starknet_contract_class_lib
    starknet_definitions_lib
    starknet_execution_usage_lib
    starknet_general_config_lib
    starknet_transaction_execution_objects_lib
    starknet_transaction_hash_lib
    starkware_error_handling_lib
    starkware_storage_lib
)

python_lib(starknet_internal_transaction_interface_lib
    PREFIX starkware/starknet/business_logic

    FILES
    internal_transaction_interface.py

    LIBS
    cairo_vm_lib
    everest_business_logic_lib
    everest_internal_transaction_lib
    everest_transaction_lib
    starknet_business_logic_state_lib
    starknet_definitions_lib
    starknet_general_config_lib
    starknet_transaction_lib
    starknet_transaction_execution_objects_lib
    starkware_config_utils_lib
    starkware_error_handling_lib
)

python_lib(starknet_internal_transaction_lib
    PREFIX starkware/starknet/business_logic

    FILES
    internal_transaction.py

    LIBS
    cairo_vm_lib
    everest_business_logic_lib
    everest_internal_transaction_lib
    everest_transaction_lib
    starknet_abi_lib
    starknet_business_logic_state_lib
    starknet_business_logic_utils_lib
    starknet_contract_address_lib
    starknet_contract_class_lib
    starknet_definitions_lib
    starknet_execute_entry_point_lib
    starknet_general_config_lib
    starknet_internal_transaction_interface_lib
    starknet_os_abi_lib
    starknet_os_utils_lib
    starknet_transaction_execution_objects_lib
    starknet_transaction_fee_lib
    starknet_transaction_hash_lib
    starknet_transaction_lib
    starkware_config_utils_lib
    starkware_dataclasses_utils_lib
    starkware_error_handling_lib
    starkware_python_utils_lib
    starkware_storage_lib
    pip_marshmallow
    pip_marshmallow_dataclass
    pip_marshmallow_enum
    pip_marshmallow_oneofschema
)

python_lib(starknet_transaction_fee_lib
    PREFIX starkware/starknet/business_logic

    FILES
    transaction_fee.py

    LIBS
    starknet_abi_lib
    starknet_business_logic_state_lib
    starknet_business_logic_utils_lib
    starknet_contract_class_lib
    starknet_definitions_lib
    starknet_execute_entry_point_lib
    starknet_general_config_lib
    starknet_transaction_execution_objects_lib
    starkware_error_handling_lib
)
