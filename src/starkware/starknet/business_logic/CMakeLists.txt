add_subdirectory(execution)
add_subdirectory(fact_state)
add_subdirectory(state)
add_subdirectory(transaction)

python_lib(starknet_business_logic_utils_lib
    PREFIX starkware/starknet/business_logic

    FILES
    utils.py

    LIBS
    cairo_function_runner_lib
    cairo_vm_lib
    starknet_abi_lib
    starknet_business_logic_fact_state_lib
    starknet_business_logic_patricia_state_lib
    starknet_business_logic_state_lib
    starknet_contract_class_lib
    starknet_definitions_lib
    starknet_execution_usage_lib
    starknet_general_config_lib
    starknet_transaction_execution_objects_lib
    starknet_transaction_hash_lib
    starkware_error_handling_lib
    starkware_python_utils_lib
    starkware_storage_lib
)
