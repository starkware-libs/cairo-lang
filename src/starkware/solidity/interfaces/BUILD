load("//bazel_utils:solidity.bzl", "sol_library")

package(default_visibility = ["//visibility:public"])

exports_files(glob(["*.sol"]))

sol_library(
    name = "solidity_contracts_interfaces_sol",
    srcs = [
        "BlockDirectCall.sol",
        "IFactRegistry.sol",
        "IQueryableFactRegistry.sol",
        "Identity.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
    ],
)

sol_library(
    name = "block_direct_call_sol",
    srcs = [
        "BlockDirectCall.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
    ],
)

sol_library(
    name = "identified_fact_registry_interface_sol",
    srcs = [
        "IFactRegistry.sol",
        "IQueryableFactRegistry.sol",
        "Identity.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
    ],
)

sol_library(
    name = "fact_registry_interface_sol",
    srcs = [
        "IFactRegistry.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
    ],
)

sol_library(
    name = "approval_chain_interface_sol",
    srcs = [
        "MApprovalChain.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/solidity/libraries:starkex_types_library_sol",
    ],
)

sol_library(
    name = "sub_contract_interface_sol",
    srcs = [
        "SubContractor.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/solidity/interfaces:identity_interface_sol",
    ],
)

sol_library(
    name = "identity_interface_sol",
    srcs = [
        "Identity.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
    ],
)

sol_library(
    name = "accept_modifications_interface_sol",
    srcs = [
        "MAcceptModifications.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
    ],
)

sol_library(
    name = "deposits_interface_sol",
    srcs = [
        "MDeposits.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
    ],
)

sol_library(
    name = "freezable_interface_sol",
    srcs = [
        "MFreezable.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
    ],
)

sol_library(
    name = "governance_interface_sol",
    srcs = [
        "MGovernance.sol",
        "MOperator.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
    ],
)

sol_library(
    name = "key_getters_interface_sol",
    srcs = [
        "MKeyGetters.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
    ],
)

sol_library(
    name = "state_root_interface_sol",
    srcs = [
        "MStateRoot.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
    ],
)

sol_library(
    name = "token_asset_data_interface_sol",
    srcs = [
        "MTokenAssetData.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
    ],
)

sol_library(
    name = "token_quantization_interface_sol",
    srcs = [
        "MTokenQuantization.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
    ],
)

sol_library(
    name = "token_transfers_interface_sol",
    srcs = [
        "MTokenTransfers.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
    ],
)

sol_library(
    name = "external_initializer_interface_sol",
    srcs = [
        "ExternalInitializer.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
    ],
)

sol_library(
    name = "solidity_contract_initializer_sol",
    srcs = [
        "ContractInitializer.sol",
        "ExternalInitializer.sol",
        "ProxySupport.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/solidity/components:governance_contract_sol",
        "//src/starkware/solidity/interfaces:solidity_contracts_interfaces_sol",
        "//src/starkware/solidity/libraries:addresses_library_sol",
    ],
)

sol_library(
    name = "main_dispatcher_base_sol",
    srcs = [
        "IDispatcherBase.sol",
        "MainDispatcherBase.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
        ":block_direct_call_sol",
        ":sub_contract_interface_sol",
        "//src/starkware/solidity/components:governance_contract_sol",
        "//src/starkware/solidity/interfaces:solidity_contracts_interfaces_sol",
        "//src/starkware/solidity/libraries:addresses_library_sol",
    ],
)

sol_library(
    name = "main_dispatcher_sol",
    srcs = [
        "MainDispatcher.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
        ":main_dispatcher_base_sol",
        "//src/starkware/solidity/components:main_storage_sol",
    ],
)
