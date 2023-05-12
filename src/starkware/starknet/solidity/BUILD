load("//bazel_utils:solidity.bzl", "sol_contract", "sol_library")

sol_library(
    name = "starknet_messaging_sol",
    srcs = [
        "IStarknetMessaging.sol",
        "IStarknetMessagingEvents.sol",
        "StarknetMessaging.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/solidity/libraries:named_storage_sol",
    ],
)

sol_library(
    name = "starknet_governance_sol",
    srcs = [
        "StarknetGovernance.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/solidity/components:governance_contract_sol",
    ],
)

sol_library(
    name = "starknet_core_sol",
    srcs = [
        "Output.sol",
        "Starknet.sol",
        "StarknetOperator.sol",
        "StarknetState.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "starknet_governance_sol",
        "starknet_messaging_sol",
        "//src/starkware/solidity/components:governance_contract_sol",
        "//src/starkware/solidity/components:solidity_contracts_components_sol",
        "//src/starkware/solidity/interfaces:solidity_contract_initializer_sol",
        "//src/starkware/solidity/interfaces:solidity_contracts_interfaces_sol",
        "//src/starkware/solidity/libraries:named_storage_sol",
    ],
)

sol_contract(
    name = "starknet_core_contract",
    contracts = [
        "Starknet.json",
    ],
    deps = [
        "starknet_core_sol",
    ],
)

package(default_visibility = ["//visibility:public"])
