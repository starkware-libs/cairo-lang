python_lib(starknet_business_logic_lib
    PREFIX starkware/starknet/business_logic

    FILES
    state.py
    state_objects.py

    LIBS
    cairo_vm_lib
    everest_business_logic_lib
    everest_definitions_lib
    starknet_contract_definition_lib
    starknet_definitions_lib
    starknet_general_config_lib
    starknet_os_abi_lib
    starknet_storage_lib
    starkware_config_utils_lib
    starkware_dataclasses_utils_lib
    starkware_error_handling_lib
    starkware_python_utils_lib
    starkware_storage_lib
    starkware_utils_lib
    pip_marshmallow_dataclass
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
    starknet_business_logic_lib
    starknet_definitions_lib
    starknet_general_config_lib
    starknet_transaction_lib
    starknet_transaction_execution_objects_lib
    starkware_config_utils_lib
    starkware_error_handling_lib
)

python_lib(starknet_transaction_execution_objects_lib
    PREFIX starkware/starknet/business_logic

    FILES
    transaction_execution_objects.py

    LIBS
    cairo_vm_lib
    everest_definitions_lib
    everest_internal_transaction_lib
    starknet_business_logic_lib
    starknet_contract_definition_lib
    starknet_definitions_lib
    starkware_dataclasses_utils_lib
    pip_marshmallow_dataclass
)

python_lib(starknet_internal_transaction_lib
    PREFIX starkware/starknet/business_logic

    FILES
    internal_transaction.py

    LIBS
    cairo_function_runner_lib
    cairo_relocatable_lib
    cairo_vm_lib
    everest_business_logic_lib
    everest_internal_transaction_lib
    everest_transaction_lib
    starknet_abi_lib
    starknet_business_logic_lib
    starknet_contract_address_lib
    starknet_contract_definition_lib
    starknet_definitions_lib
    starknet_general_config_lib
    starknet_internal_transaction_interface_lib
    starknet_os_abi_lib
    starknet_os_utils_lib
    starknet_storage_lib
    starknet_transaction_execution_objects_lib
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
