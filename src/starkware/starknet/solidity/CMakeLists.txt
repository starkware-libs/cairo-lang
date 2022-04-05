python_lib(starknet_messaging_sol
    PREFIX starkware/starknet/solidity
    FILES
    IStarknetMessaging.sol
    IStarknetMessagingEvents.sol
    StarknetMessaging.sol

    LIBS
    named_storage_sol
)
