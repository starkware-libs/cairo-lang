load("//bazel_utils/python:defs.bzl", "requirement")

package(default_visibility = ["//visibility:public"])

py_library(
    name = "base_general_config_lib",
    srcs = [
        "general_config.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/starkware_utils:starkware_config_utils_lib",
        requirement("marshmallow_dataclass"),
    ],
)
