python_lib(starknet_sequencer_api_utils_lib
    PREFIX starkware/starknet/services/utils

    FILES
    sequencer_api_utils.py

    LIBS
    everest_transaction_lib
    starknet_business_logic_fact_state_lib
    starknet_business_logic_state_lib
    starknet_business_logic_utils_lib
    starknet_feeder_gateway_response_objects_lib
    starknet_general_config_lib
    starknet_transaction_execution_objects_lib
    starknet_transaction_fee_lib
    starknet_transaction_lib
    starknet_transaction_objects_lib
    starknet_transaction_state_objects_lib
    starkware_config_utils_lib
)
