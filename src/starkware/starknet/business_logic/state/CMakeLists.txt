python_lib(starknet_business_logic_state_lib
    PREFIX starkware/starknet/business_logic/state

    FILES
    state.py
    state_api.py
    state_api_objects.py

    LIBS
    cairo_version_lib
    everest_business_logic_state_api_lib
    starknet_contract_class_lib
    starknet_definitions_lib
    starknet_general_config_lib
    starkware_dataclasses_utils_lib
    starkware_error_handling_lib
    starkware_python_utils_lib
    starkware_utils_lib
    pip_marshmallow_dataclass
)
