python_lib(solidity_contracts_interfaces_sol
    PREFIX starkware/solidity/interfaces
    FILES
    BlockDirectCall.sol
    IFactRegistry.sol
    Identity.sol
    IQueryableFactRegistry.sol
)

python_lib(governance_interface_sol
    PREFIX starkware/solidity/interfaces
    FILES
    MGovernance.sol
    MOperator.sol
)

python_lib(solidity_contract_initializer_sol
    PREFIX starkware/solidity/interfaces
    FILES
    ExternalInitializer.sol
    ContractInitializer.sol
    ProxySupport.sol

    LIBS
    common_library_sol
    governance_contract_sol
    solidity_contracts_interfaces_sol
)
