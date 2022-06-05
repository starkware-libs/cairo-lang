python_lib(starknet_abi_lib
    PREFIX starkware/starknet/public
    FILES
    abi.py
    abi_structs.py

    LIBS
    cairo_compile_lib
    cairo_vm_crypto_lib
    starkware_python_utils_lib
    pip_eth_hash
    pip_pycryptodome
)


full_python_test(starknet_abi_lib_test
    PREFIX starkware/starknet/public
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/starknet/public/

    FILES
    abi_structs_test.py
    abi_test.py

    LIBS
    starknet_abi_lib
    pip_pytest
)
