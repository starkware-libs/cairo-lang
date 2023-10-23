load("//bazel_utils/python:defs.bzl", "requirement")
load(
    "//src/services/external_api:vars.bzl",
    "SERVICES_EXTERNAL_API_LIB_ADDITIONAL_FILES",
    "SERVICES_EXTERNAL_API_LIB_ADDITIONAL_LIBS",
)

package(default_visibility = ["//visibility:public"])

py_library(
    name = "services_external_api_utils_lib",
    srcs = [
        "utils.py",
    ],
    visibility = ["//visibility:public"],
    deps = [],
)

py_library(
    name = "services_external_api_lib",
    srcs = [
        "client.py",
        "has_uri_prefix.py",
    ] + SERVICES_EXTERNAL_API_LIB_ADDITIONAL_FILES,
    visibility = ["//visibility:public"],
    deps = [
        ":services_external_api_utils_lib",
        "//src/starkware/starkware_utils:starkware_dataclasses_field_utils_lib",
        "//src/starkware/python:starkware_python_utils_lib",
        requirement("aiohttp"),
    ] + SERVICES_EXTERNAL_API_LIB_ADDITIONAL_LIBS,
)

py_library(
    name = "services_eth_gas_constants_lib",
    srcs = [
        "eth_gas_constants.py",
    ],
    visibility = ["//visibility:public"],
    deps = [],
)
