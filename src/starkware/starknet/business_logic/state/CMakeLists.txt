python_lib(starknet_business_logic_state_lib
    PREFIX starkware/starknet/business_logic/state

    FILES
    state.py
    objects.py

    LIBS
    cairo_vm_lib
    everest_business_logic_lib
    everest_definitions_lib
    starknet_contract_definition_lib
    starknet_definitions_lib
    starknet_general_config_lib
    starknet_os_abi_lib
    starknet_storage_lib
    starkware_commitment_tree_facts_lib
    starkware_config_utils_lib
    starkware_dataclasses_utils_lib
    starkware_error_handling_lib
    starkware_python_utils_lib
    starkware_storage_lib
    starkware_utils_lib
    pip_marshmallow_dataclass
)
