load("//bazel_utils/python:defs.bzl", "requirement")

package(default_visibility = ["//visibility:public"])

py_library(
    name = "everest_definitions_lib",
    srcs = [
        "constants.py",
        "fields.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/crypto:starkware_crypto_lib",
        "//src/starkware/eth:web3_wrapper_lib",
        "//src/starkware/python:starkware_python_utils_lib",
        "//src/starkware/starkware_utils:starkware_dataclasses_field_utils_lib",
        "//src/starkware/starkware_utils:starkware_dataclasses_utils_lib",
        "//src/starkware/starkware_utils:starkware_error_handling_lib",
        requirement("marshmallow"),
        requirement("web3"),
    ],
)

py_library(
    name = "everest_general_config_lib",
    srcs = [
        "general_config.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/services/config:base_general_config_lib",
        requirement("marshmallow_dataclass"),
    ],
)
