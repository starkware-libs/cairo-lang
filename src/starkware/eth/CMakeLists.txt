python_lib(starkware_eth_test_utils_lib
    PREFIX starkware/eth

    FILES
    eth_test_utils.py

    LIBS
    pip_pytest
    pip_web3
    web3_wrapper_lib
)

python_lib(web3_wrapper_lib
    PREFIX starkware/eth

    FILES
    web3_wrapper.py

    LIBS
    pip_web3
)
