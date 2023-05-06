load("//bazel_utils/python:defs.bzl", "requirement")

package(default_visibility = ["//visibility:public"])

py_library(
    name = "starknet_feeder_gateway_client_lib",
    srcs = [
        "feeder_gateway_client.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "starknet_feeder_gateway_request_objects_lib",
        "starknet_feeder_gateway_response_objects_lib",
        "//src/services/everest/api/feeder_gateway:everest_feeder_gateway_client_lib",
        "//src/services/external_api:services_external_api_lib",
        "//src/starkware/starknet/definitions:starknet_definitions_lib",
        "//src/starkware/starknet/services/api/gateway:starknet_transaction_lib",
        "//src/starkware/starkware_utils:starkware_dataclasses_utils_lib",
        requirement("typing_extensions"),
    ],
)

py_library(
    name = "starknet_feeder_gateway_response_objects_lib",
    srcs = [
        "response_objects.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/services/everest/api/feeder_gateway:everest_feeder_gateway_response_objects_lib",
        "//src/services/everest/business_logic:everest_transaction_execution_objects_lib",
        "//src/services/everest/definitions:everest_definitions_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_lib",
        "//src/starkware/eth:web3_wrapper_lib",
        "//src/starkware/python:starkware_python_utils_lib",
        "//src/starkware/starknet/business_logic/execution:starknet_transaction_execution_objects_lib",
        "//src/starkware/starknet/business_logic/transaction:starknet_transaction_objects_lib",
        "//src/starkware/starknet/definitions:starknet_definitions_lib",
        "//src/starkware/starknet/services/api/contract_class:starknet_contract_class_lib",
        "//src/starkware/starknet/services/api/gateway:starknet_transaction_utils_lib",
        "//src/starkware/starkware_utils:starkware_dataclasses_field_utils_lib",
        "//src/starkware/starkware_utils:starkware_dataclasses_utils_lib",
        requirement("marshmallow"),
        requirement("marshmallow_dataclass"),
        requirement("marshmallow_enum"),
        requirement("marshmallow_oneofschema"),
        requirement("typing_extensions"),
        requirement("web3"),
    ],
)

py_library(
    name = "starknet_feeder_gateway_request_objects_lib",
    srcs = [
        "request_objects.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/services/everest/definitions:everest_definitions_lib",
        "//src/starkware/starknet/business_logic/execution:starknet_execute_entry_point_lib",
        "//src/starkware/starknet/business_logic/transaction:starknet_transaction_objects_lib",
        "//src/starkware/starknet/definitions:starknet_definitions_lib",
        "//src/starkware/starkware_utils:starkware_dataclasses_utils_lib",
        requirement("marshmallow_dataclass"),
    ],
)
