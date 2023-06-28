load("//bazel_utils:solidity.bzl", "sol_library")

package(default_visibility = ["//visibility:public"])

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
    name = "solidity_contracts_components_sol",
    srcs = [
        "FactRegistry.sol",
        "GovernedFinalizable.sol",
        "OnchainDataFactTreeEncoder.sol",
    ],
    deps = [
        "//src/starkware/solidity/interfaces:governance_interface_sol",
        "//src/starkware/solidity/interfaces:solidity_contracts_interfaces_sol",
        "//src/starkware/solidity/libraries:common_library_sol",
        "//src/starkware/solidity/libraries:named_storage_sol",
    ],
)
