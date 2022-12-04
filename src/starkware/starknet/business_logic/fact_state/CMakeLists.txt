python_lib(starknet_business_logic_fact_state_lib
    PREFIX starkware/starknet/business_logic/fact_state

    FILES
    state.py

    LIBS
    cairo_vm_lib
    everest_business_logic_lib
    starknet_business_logic_fact_state_utils_lib
    starknet_business_logic_patricia_state_lib
    starknet_business_logic_state_lib
    starknet_definitions_lib
    starknet_general_config_lib
    starknet_transaction_lib
    starkware_config_utils_lib
    starkware_error_handling_lib
    starkware_python_utils_lib
    starkware_storage_lib
    starkware_utils_lib
    pip_marshmallow_dataclass
)

python_lib(starknet_business_logic_patricia_state_lib
    PREFIX starkware/starknet/business_logic/fact_state

    FILES
    contract_state_objects.py
    patricia_state.py

    LIBS
    everest_business_logic_lib
    starknet_business_logic_state_lib
    starknet_contract_class_lib
    starknet_definitions_lib
    starknet_general_config_lib
    starknet_os_abi_lib
    starknet_storage_lib
    starkware_commitment_tree_facts_lib
    starkware_dataclasses_utils_lib
    starkware_error_handling_lib
    starkware_python_utils_lib
    starkware_storage_lib
    starkware_utils_lib
    pip_marshmallow_dataclass
)

python_lib(starknet_business_logic_fact_state_utils_lib
    PREFIX starkware/starknet/business_logic/fact_state

    FILES
    utils.py

    LIBS
    starknet_business_logic_state_lib
)
