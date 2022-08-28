python_lib(starknet_governance_sol
    PREFIX starkware/starknet/solidity
    FILES
    StarknetGovernance.sol

    LIBS
    governance_contract_sol
)

python_lib(starknet_messaging_sol
    PREFIX starkware/starknet/solidity
    FILES
    IStarknetMessaging.sol
    IStarknetMessagingEvents.sol
    StarknetMessaging.sol

    LIBS
    named_storage_sol
)
