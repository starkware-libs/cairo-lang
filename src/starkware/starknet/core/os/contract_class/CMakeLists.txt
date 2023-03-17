python_lib(starknet_os_abi_lib
    PREFIX starkware/starknet/core/os/contract_class

    FILES
    class_hash.py
    class_hash_utils.py
    compiled_class.cairo
    compiled_class_hash.py
    compiled_class_hash_utils.py
    contract_class.cairo
    deprecated_class_hash.py
    deprecated_compiled_class.cairo
    utils.py

    LIBS
    cairo_common_lib
    cairo_compile_lib
    cairo_constants_lib
    cairo_function_runner_lib
    cairo_run_builtins_lib
    cairo_vm_crypto_lib
    poseidon_utils_lib
    starknet_abi_lib
    starknet_contract_class_lib
    starknet_definitions_lib
    starkware_error_handling_lib
    starkware_python_utils_lib
    pip_cachetools
)
