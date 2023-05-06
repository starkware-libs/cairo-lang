load("//bazel_utils/python:defs.bzl", "requirement")

package(default_visibility = ["//visibility:public"])

py_library(
    name = "everest_business_logic_state_api_lib",
    srcs = [
        "state_api.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
    ],
)

py_library(
    name = "everest_business_logic_lib",
    srcs = [
        "state.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "everest_business_logic_state_api_lib",
        "//src/starkware/python:starkware_python_utils_lib",
        "//src/starkware/starkware_utils:starkware_config_utils_lib",
        "//src/starkware/starkware_utils:starkware_dataclasses_field_utils_lib",
        "//src/starkware/starkware_utils:starkware_utils_lib",
        "//src/starkware/storage:starkware_storage_lib",
    ],
)

py_library(
    name = "everest_internal_transaction_lib",
    srcs = [
        "internal_transaction.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "everest_business_logic_lib",
        "everest_business_logic_state_api_lib",
        "everest_transaction_execution_objects_lib",
        "//src/services/everest/api/gateway:everest_transaction_lib",
        "//src/starkware/starkware_utils:starkware_config_utils_lib",
        "//src/starkware/starkware_utils:starkware_one_of_schema_utils_lib",
    ],
)

py_library(
    name = "everest_transaction_execution_objects_lib",
    srcs = [
        "transaction_execution_objects.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/starkware_utils:starkware_dataclasses_field_utils_lib",
        requirement("marshmallow"),
        requirement("marshmallow_dataclass"),
    ],
)
