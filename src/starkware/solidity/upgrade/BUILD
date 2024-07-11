load("//bazel_utils:solidity.bzl", "sol_library")

sol_library(
    name = "proxy_storage_sol",
    srcs = [
        "ProxyStorage.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/solidity/components:governance_storage_sol",
    ],
)
