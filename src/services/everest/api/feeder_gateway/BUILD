load("//bazel_utils/python:defs.bzl", "requirement")

package(default_visibility = ["//visibility:public"])

py_library(
    name = "everest_feeder_gateway_client_lib",
    srcs = [
        "feeder_gateway_client.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/services/external_api:services_external_api_lib",
    ],
)

py_library(
    name = "everest_external_api_feeder_gateway_lib",
    srcs = [
        "docs.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
    ],
)

py_library(
    name = "everest_feeder_gateway_response_objects_lib",
    srcs = [
        "response_objects.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/starkware_utils:starkware_dataclasses_field_utils_lib",
        requirement("marshmallow"),
    ],
)
