starknet_compile(compile_open_zeppelin_account account.json Account.cairo "--account_contract")

python_lib(open_zeppelin_contracts_lib
    PREFIX starkware/starknet/third_party/open_zeppelin

    FILES
    starknet_contracts.py

    ARTIFACTS
    "${CMAKE_CURRENT_BINARY_DIR}/account.json account.json"

    LIBS
    cairo_common_lib
    starknet_common_lib
    starknet_contract_class_lib
)
add_dependencies(open_zeppelin_contracts_lib
    compile_open_zeppelin_account
)
