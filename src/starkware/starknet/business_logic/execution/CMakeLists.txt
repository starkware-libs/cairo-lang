python_lib(starknet_transaction_execution_objects_lib
    PREFIX starkware/starknet/business_logic/execution

    FILES
    objects.py

    LIBS
    cairo_vm_lib
    everest_definitions_lib
    everest_transaction_execution_objects_lib
    starknet_abi_lib
    starknet_business_logic_patricia_state_lib
    starknet_business_logic_state_lib
    starknet_contract_class_lib
    starknet_definitions_lib
    starknet_transaction_lib
    starkware_dataclasses_field_utils_lib
    starkware_dataclasses_utils_lib
    starkware_python_utils_lib
    pip_marshmallow
    pip_marshmallow_dataclass
)

python_lib(starknet_execute_entry_point_base_lib
    PREFIX starkware/starknet/business_logic/execution

    FILES
    execute_entry_point_base.py

    LIBS
    starknet_business_logic_fact_state_lib
    starknet_business_logic_state_lib
    starknet_contract_class_lib
    starknet_definitions_lib
    starknet_general_config_lib
    starknet_transaction_execution_objects_lib
    starkware_dataclasses_utils_lib
)

python_lib(starknet_execute_entry_point_lib
    PREFIX starkware/starknet/business_logic/execution

    FILES
    execute_entry_point.py

    LIBS
    cairo_function_runner_lib
    cairo_relocatable_lib
    cairo_vm_lib
    starknet_abi_lib
    starknet_business_logic_fact_state_lib
    starknet_business_logic_state_lib
    starknet_business_logic_utils_lib
    starknet_contract_class_lib
    starknet_definitions_lib
    starknet_execute_entry_point_base_lib
    starknet_general_config_lib
    starknet_os_utils_lib
    starknet_storage_lib
    starknet_transaction_execution_objects_lib
    starkware_error_handling_lib
)

python_lib(starknet_execution_usage_lib
    PREFIX starkware/starknet/business_logic/execution

    FILES
    os_resources.json
    os_usage.py
    gas_usage.py

    LIBS
    cairo_vm_lib
    services_eth_gas_constants_lib
    starknet_definitions_lib
    starknet_transaction_execution_objects_lib
    starkware_dataclasses_utils_lib
    pip_marshmallow_dataclass
)
