python_lib(starknet_script_lib
    PREFIX starkware/starknet/scripts
    FILES
    starknet
    starknet-class-hash
    starknet-compile

    LIBS
    starknet_cli_lib
    starknet_compile_lib
    starknet_standard_wallets_lib
)
