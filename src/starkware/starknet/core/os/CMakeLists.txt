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
    starkware_storage_lib
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
    starknet_definitions_lib
    starknet_general_config_lib
    starknet_internal_transaction_interface_lib
    starknet_storage_lib
    starknet_transaction_lib
    starkware_python_utils_lib
    starkware_utils_lib
    pip_cachetools
)
add_dependencies(starknet_os_utils_lib starknet_os_program)
