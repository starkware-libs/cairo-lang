load("//bazel_utils/python:defs.bzl", "requirement")
load("//bazel_utils:solidity.bzl", "sol_contract", "sol_library")

sol_library(
    name = "starknet_mock_messaging_sol",
    srcs = [
        "MockStarknetMessaging.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/starknet/solidity:starknet_messaging_sol",
    ],
)

sol_contract(
    name = "mock_starknet_messaging_sol_env",
    contracts = [
        "MockStarknetMessaging.json",
    ],
    solc_exe = "//bazel_utils:solc-0.8.24",
    deps = [
        "starknet_mock_messaging_sol",
    ],
)

py_library(
    name = "starknet_mock_messaging_contracts_lib",
    srcs = [
        "contracts.py",
    ],
    data = [
        ":mock_starknet_messaging_sol_env",
    ],
    visibility = ["//visibility:public"],
    deps = ["//src/starkware/solidity:starkware_contracts_utils_lib"],
)

py_library(
    name = "starknet_testing_test_utils_lib",
    srcs = [
        "test_utils.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/starknet/business_logic/transaction:starknet_account_transaction_objects_lib",
        "//src/starkware/starknet/business_logic/transaction:starknet_transaction_deprecated_objects_lib",
        "//src/starkware/starknet/core/os/contract_address:starknet_contract_address_lib",
        "//src/starkware/starknet/definitions:starknet_definitions_lib",
        "//src/starkware/starknet/public:starknet_abi_lib",
        requirement("web3"),
    ],
)

package(default_visibility = ["//visibility:public"])
