python_lib(starknet_contract_class_lib
    PREFIX starkware/starknet/services/api/contract_class

    FILES
    contract_class.py

    LIBS
    cairo_compile_lib
    cairo_constants_lib
    starknet_abi_lib
    starknet_definitions_lib
    starkware_dataclasses_utils_lib
    starkware_error_handling_lib
    starkware_python_utils_lib
    starkware_utils_lib
    pip_marshmallow
    pip_marshmallow_dataclass
)

python_lib(starknet_contract_class_utils_lib
    PREFIX starkware/starknet/services/api/contract_class
    PYTHON ${PYTHON_COMMAND}

    FILES
    contract_class_utils.py

    LIBS
    cairo_compile_lib
    starknet_compile_v1_lib
    starknet_contract_class_lib
)
