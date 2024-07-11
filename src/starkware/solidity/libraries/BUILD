load("//bazel_utils:solidity.bzl", "sol_library")

package(default_visibility = ["//visibility:public"])

exports_files(glob(["*.sol"]))

sol_library(
    name = "named_storage_sol",
    srcs = [
        "NamedStorage.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [],
)

sol_library(
    name = "named_storage8_sol",
    srcs = [
        "NamedStorage8.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [],
)

sol_library(
    name = "common_library_sol",
    srcs = [],
    visibility = ["//visibility:public"],
    deps = [
        "addresses_library_sol",
        "starkex_constants_library_sol",
        "starkex_types_library_sol",
    ],
)

sol_library(
    name = "addresses_library_sol",
    srcs = [
        "Addresses.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [],
)

sol_library(
    name = "starkex_types_library_sol",
    srcs = [
        "StarkExTypes.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [],
)

sol_library(
    name = "starkex_constants_library_sol",
    srcs = [
        "LibConstants.sol",
    ],
    visibility = ["//visibility:public"],
    deps = [],
)
