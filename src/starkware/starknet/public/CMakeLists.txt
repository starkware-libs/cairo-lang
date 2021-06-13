python_lib(starknet_abi_lib
    PREFIX starkware/starknet/public
    FILES
    abi.py

    LIBS
    cairo_vm_crypto_lib
    pip_eth_hash
    pip_pycryptodome
)


full_python_test(starknet_abi_lib_test
    PREFIX starkware/starknet/public
    PYTHON python3.7
    TESTED_MODULES starkware/starknet/public/

    FILES
    abi_test.py

    LIBS
    starknet_abi_lib
    pip_pytest
)
