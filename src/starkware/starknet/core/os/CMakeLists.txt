add_subdirectory(os_config)

cairo_compile(starknet_os_program
    starknet_os_compiled.json os.cairo "--debug_info_with_source")

python_lib(starknet_os_abi_lib
    PREFIX starkware/starknet/core/os

    FILES
    contracts.cairo
    contract_hash.py

    LIBS
    cairo_common_lib
    cairo_compile_lib
    cairo_constants_lib
    cairo_function_runner_lib
    cairo_run_builtins_lib
    cairo_vm_crypto_lib
    starknet_abi_lib
    starknet_contract_definition_lib
    starkware_python_utils_lib
    pip_cachetools
)

python_lib(starknet_os_utils_lib
    PREFIX starkware/starknet/core/os

    FILES
    os_program.py
    os_utils.py
    segment_utils.py
    syscall_utils.py

    ARTIFACTS
    "${CMAKE_CURRENT_BINARY_DIR}/starknet_os_compiled.json starknet_os_compiled.json"

    LIBS
    cairo_common_lib
    cairo_compile_lib
    cairo_function_runner_lib
    cairo_hash_program_lib
    cairo_relocatable_lib
    cairo_run_lib
    cairo_vm_lib
    starknet_abi_lib
    starknet_business_logic_lib
    starknet_contract_definition_lib
    starknet_definitions_lib
    starknet_execute_entry_point_base_lib
    starknet_general_config_lib
    starknet_internal_transaction_interface_lib
    starknet_storage_lib
    starknet_transaction_lib
    starknet_transaction_execution_objects_lib
    starkware_error_handling_lib
    starkware_python_utils_lib
    pip_cachetools
)

add_dependencies(starknet_os_utils_lib starknet_os_program)

full_python_test(starknet_os_program_hash_test
    PREFIX starkware/starknet/core/os
    PYTHON python3.7
    TESTED_MODULES starkware/starknet/core/os

    FILES
    program_hash_test.py

    LIBS
    cairo_hash_program_lib
    program_hash_test_utils_lib
    starknet_os_utils_lib
    starkware_python_utils_lib
    pip_pytest
)

python_lib(starknet_transaction_hash_lib
    PREFIX starkware/starknet/core/os

    FILES
    transaction_hash.py

    LIBS
    cairo_common_lib
    cairo_vm_crypto_lib
    starknet_contract_definition_lib
    starknet_definitions_lib
    starkware_python_utils_lib
)

full_python_test(starknet_transaction_hash_test
    PREFIX starkware/starknet/core/os
    PYTHON python3.7
    TESTED_MODULES starkware/starknet/core/os

    FILES
    transaction_hash_test.py

    LIBS
    cairo_common_lib
    cairo_function_runner_lib
    starknet_contract_definition_lib
    starknet_definitions_lib
    starknet_os_utils_lib
    starknet_transaction_hash_lib
    starkware_crypto_lib
    pip_pytest
    pip_pytest_asyncio
)
