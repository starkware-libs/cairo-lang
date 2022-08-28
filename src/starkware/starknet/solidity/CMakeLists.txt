include(solidity.cmake)

python_lib(starknet_core_sol
    PREFIX starkware/starknet/solidity
    FILES
    Output.sol
    Starknet.sol
    StarknetOperator.sol
    StarknetState.sol

    LIBS
    governance_contract_sol
    named_storage_sol
    solidity_contract_initializer_sol
    solidity_contracts_interfaces_sol
    solidity_contracts_components_sol
    starknet_governance_sol
    starknet_messaging_sol
)

solidity_env(starknet_core_contract
    CONTRACTS
    Starknet

    LIBS
    starknet_core_sol
)
