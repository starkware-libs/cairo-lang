if (NOT DEFINED CAIRO_PYTHON_INTERPRETER)
    set(CAIRO_PYTHON_INTERPRETER python3.7)
endif()

python_lib(starknet_compile_lib
    PREFIX starkware/starknet/compiler

    FILES
    calldata_parser.py
    compile.py
    starknet_pass_manager.py
    starknet_preprocessor.py
    storage_var.py

    LIBS
    cairo_compile_lib
    cairo_constants_lib
    starknet_abi_lib
    starknet_cairo_storage_lib
    starknet_contract_definition_lib
    starknet_definitions_lib
    starknet_hints_whitelist_lib
    starknet_security_lib
)

full_python_test(starknet_compile_test
    PYTHON ${CAIRO_PYTHON_INTERPRETER}
    TESTED_MODULES starkware/starknet/compiler
    PREFIX starkware/starknet/compiler

    FILES
    calldata_parser_test.py
    starknet_preprocessor_test.py
    storage_var_test.py
    test_utils.py

    LIBS
    cairo_compile_test_utils_lib
    starknet_compile_lib
    pip_pytest
)

python_venv(starknet_compile_venv
    PYTHON ${CAIRO_PYTHON_INTERPRETER}

    LIBS
    starknet_compile_lib
)

python_exe(starknet_compile_exe
    VENV starknet_compile_venv
    MODULE starkware.starknet.compiler.compile
)
