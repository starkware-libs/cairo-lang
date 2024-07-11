load("//bazel_utils:solidity.bzl", "sol_library")

package(default_visibility = ["//visibility:public"])

exports_files(glob(["*.sol"]))

sol_library(
    name = "main_storage_sol",
    srcs = [
        "MainStorage.sol",
    ],
    deps = [
        "//src/starkware/solidity/libraries:common_library_sol",
        "//src/starkware/solidity/upgrade:proxy_storage_sol",
    ],
)

sol_library(
    name = "governance_storage_sol",
    srcs = [
        "GovernanceStorage.sol",
    ],
    deps = [
        "//src/starkware/solidity/components:governance_sol",
    ],
)

sol_library(
    name = "governance_sol",
    srcs = [
        "Governance.sol",
    ],
    deps = [
        "//src/starkware/solidity/interfaces:governance_interface_sol",
    ],
)

sol_library(
    name = "token_transfers_sol",
    srcs = [
        "TokenTransfers.sol",
    ],
    deps = [
        "//src/starkware/solidity/interfaces:token_asset_data_interface_sol",
        "//src/starkware/solidity/interfaces:token_quantization_interface_sol",
        "//src/starkware/solidity/interfaces:token_transfers_interface_sol",
        "//src/starkware/solidity/libraries:addresses_library_sol",
        "//src/starkware/solidity/tokens:token_interfaces_sol",
    ],
)

sol_library(
    name = "token_register_sol",
    srcs = [
        "TokenRegister.sol",
    ],
    deps = [
        "//src/starkware/solidity/components:main_storage_sol",
        "//src/starkware/solidity/interfaces:token_asset_data_interface_sol",
        "//src/starkware/solidity/libraries:starkex_constants_library_sol",
        "//src/starkware/solidity/tokens:erc20_sol",
    ],
)

sol_library(
    name = "governance_contract_sol",
    srcs = [
        "GenericGovernance.sol",
        "Governance.sol",
        "GovernanceStorage.sol",
        "Operator.sol",
    ],
    deps = [
        "//src/starkware/solidity/interfaces:governance_interface_sol",
    ],
)

sol_library(
    name = "operator_sol",
    srcs = [
        "Operator.sol",
    ],
    deps = [
        "//src/starkware/solidity/interfaces:governance_interface_sol",
    ],
)

sol_library(
    name = "starkex_operator_sol",
    srcs = [
        "StarkExOperator.sol",
    ],
    deps = [
        "//src/starkware/solidity/components:main_storage_sol",
        "//src/starkware/solidity/components:operator_sol",
    ],
)

sol_library(
    name = "verify_fact_chain_sol",
    srcs = [
        "VerifyFactChain.sol",
    ],
    deps = [
        "//src/starkware/solidity/components:main_storage_sol",
        "//src/starkware/solidity/interfaces:fact_registry_interface_sol",
    ],
)

sol_library(
    name = "solidity_contracts_components_sol",
    srcs = [
        "FactRegistry.sol",
        "OnchainDataFactTreeEncoder.sol",
    ],
    deps = [
        "//src/starkware/solidity/interfaces:solidity_contracts_interfaces_sol",
        "//src/starkware/solidity/libraries:addresses_library_sol",
    ],
)

sol_library(
    name = "governed_finalizable_sol",
    srcs = [
        "GovernedFinalizable.sol",
    ],
    deps = [
        "//src/starkware/solidity/interfaces:governance_interface_sol",
        "//src/starkware/solidity/libraries:named_storage8_sol",
    ],
)
