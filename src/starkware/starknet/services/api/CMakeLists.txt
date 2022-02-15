add_subdirectory(feeder_gateway)
add_subdirectory(gateway)

python_lib(starknet_messages_lib
    PREFIX starkware/starknet/services/api

    FILES
    messages.py

    LIBS
    cairo_bootloader_generate_fact_lib
    everest_definitions_lib
    starknet_contract_definition_lib
    starknet_definitions_lib
    starknet_internal_transaction_lib
    starkware_dataclasses_utils_lib
    starkware_error_handling_lib
)

python_lib(starknet_contract_definition_lib
    PREFIX starkware/starknet/services/api

    FILES
    contract_definition.py

    LIBS
    cairo_compile_lib
    cairo_constants_lib
    starknet_abi_lib
    starknet_definitions_lib
    starkware_dataclasses_utils_lib
    starkware_error_handling_lib
    starkware_utils_lib
    pip_marshmallow_dataclass
)
