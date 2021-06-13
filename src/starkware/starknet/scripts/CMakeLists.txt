python_lib(starknet_script_lib
    PREFIX starkware/starknet/scripts
    FILES
    starknet
    starknet-compile

    LIBS
    starknet_cli_lib
    starknet_compile_lib
)
