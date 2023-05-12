load("//bazel_utils/python:defs.bzl", "requirement")

package(default_visibility = ["//visibility:public"])

py_library(
    name = "everest_transaction_type_lib",
    srcs = [
        "transaction_type.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
    ],
)

py_library(
    name = "everest_transaction_lib",
    srcs = [
        "transaction.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "everest_transaction_type_lib",
        "//src/starkware/starkware_utils:starkware_dataclasses_field_utils_lib",
        requirement("marshmallow_enum"),
        requirement("marshmallow_oneofschema"),
    ],
)

py_library(
    name = "everest_config_request_lib",
    srcs = [
        "set_config_request.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/starkware_utils:starkware_dataclasses_field_utils_lib",
        "//src/starkware/starkware_utils:starkware_dataclasses_utils_lib",
        "//src/starkware/starkware_utils:starkware_error_handling_lib",
    ],
)

py_library(
    name = "everest_gateway_client_lib",
    srcs = [
        "gateway_client.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "everest_transaction_lib",
        "//src/services/external_api:services_external_api_lib",
    ],
)
