starknet_compile(compile_delegate_proxy delegate_proxy.json delegate_proxy.cairo "")
starknet_compile(compile_dummy_account_contract
    dummy_account.json dummy_account.cairo "--account_contract")

python_lib(starknet_external_compiled_contracts_lib
    PREFIX starkware/starknet/core/test_contract

    ARTIFACTS
    "${CMAKE_CURRENT_BINARY_DIR}/delegate_proxy.json delegate_proxy.json"
    "${CMAKE_CURRENT_BINARY_DIR}/dummy_account.json dummy_account.json"
)
add_dependencies(starknet_external_compiled_contracts_lib
    compile_delegate_proxy
    compile_dummy_account_contract
)

python_lib(starknet_test_external_contract_test_utils_lib
    PREFIX starkware/starknet/core/test_contract

    FILES
    test_utils.py

    LIBS
    starknet_contract_class_lib
    starknet_external_compiled_contracts_lib
)
