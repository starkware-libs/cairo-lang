add_subdirectory(feeder_gateway)
add_subdirectory(gateway)
add_subdirectory(contract_class)

python_lib(starknet_messages_lib
    PREFIX starkware/starknet/services/api

    FILES
    messages.py

    LIBS
    cairo_bootloader_generate_fact_lib
    everest_definitions_lib
    starknet_definitions_lib
    starknet_transaction_objects_lib
    starkware_dataclasses_utils_lib
    starkware_error_handling_lib
    starkware_python_utils_lib
)
