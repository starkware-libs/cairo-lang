add_subdirectory(feeder_gateway)
add_subdirectory(gateway)

python_lib(starknet_contract_definition_lib
    PREFIX starkware/starknet/services/api

    FILES
    contract_definition.py

    LIBS
    cairo_compile_lib
    starknet_definitions_lib
    starkware_utils_lib
    pip_marshmallow_dataclass
)
