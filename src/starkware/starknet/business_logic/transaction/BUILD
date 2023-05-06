load("//bazel_utils/python:defs.bzl", "requirement")

package(default_visibility = ["//visibility:public"])

py_library(
    name = "starknet_transaction_objects_lib",
    srcs = [
        "objects.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "starknet_transaction_fee_lib",
        "starknet_transaction_state_objects_lib",
        "//src/services/everest/api/gateway:everest_transaction_lib",
        "//src/services/everest/business_logic:everest_business_logic_lib",
        "//src/services/everest/business_logic:everest_business_logic_state_api_lib",
        "//src/services/everest/business_logic:everest_internal_transaction_lib",
        "//src/services/everest/definitions:everest_definitions_lib",
        "//src/starkware/python:starkware_python_utils_lib",
        "//src/starkware/starknet/business_logic:starknet_business_logic_utils_lib",
        "//src/starkware/starknet/business_logic/execution:starknet_execute_entry_point_lib",
        "//src/starkware/starknet/business_logic/execution:starknet_transaction_execution_objects_lib",
        "//src/starkware/starknet/business_logic/fact_state:starknet_business_logic_patricia_state_lib",
        "//src/starkware/starknet/business_logic/state:starknet_business_logic_state_lib",
        "//src/starkware/starknet/core/os/contract_address:starknet_contract_address_lib",
        "//src/starkware/starknet/core/os/contract_class:starknet_os_abi_lib",
        "//src/starkware/starknet/core/os/transaction_hash:starknet_transaction_hash_lib",
        "//src/starkware/starknet/definitions:starknet_definitions_lib",
        "//src/starkware/starknet/definitions:starknet_general_config_lib",
        "//src/starkware/starknet/public:starknet_abi_lib",
        "//src/starkware/starknet/services/api/contract_class:starknet_contract_class_lib",
        "//src/starkware/starknet/services/api/gateway:starknet_transaction_lib",
        "//src/starkware/starknet/services/api/gateway:starknet_transaction_utils_lib",
        "//src/starkware/starkware_utils:starkware_config_utils_lib",
        "//src/starkware/starkware_utils:starkware_dataclasses_field_utils_lib",
        "//src/starkware/starkware_utils:starkware_error_handling_lib",
        "//src/starkware/storage:starkware_abstract_storage_lib",
        "//src/starkware/storage:starkware_storage_lib",
        requirement("marshmallow"),
        requirement("marshmallow_dataclass"),
        requirement("marshmallow_enum"),
        requirement("marshmallow_oneofschema"),
    ],
)

py_library(
    name = "starknet_transaction_state_objects_lib",
    srcs = [
        "state_objects.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/services/everest/api/gateway:everest_transaction_lib",
        "//src/services/everest/business_logic:everest_business_logic_lib",
        "//src/services/everest/business_logic:everest_business_logic_state_api_lib",
        "//src/services/everest/business_logic:everest_internal_transaction_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_lib",
        "//src/starkware/starknet/business_logic/execution:starknet_transaction_execution_objects_lib",
        "//src/starkware/starknet/business_logic/fact_state:starknet_business_logic_fact_state_lib",
        "//src/starkware/starknet/business_logic/fact_state:starknet_business_logic_patricia_state_lib",
        "//src/starkware/starknet/business_logic/state:starknet_business_logic_state_lib",
        "//src/starkware/starknet/definitions:starknet_definitions_lib",
        "//src/starkware/starknet/definitions:starknet_general_config_lib",
        "//src/starkware/starknet/services/api/gateway:starknet_transaction_lib",
        "//src/starkware/starkware_utils:starkware_config_utils_lib",
        "//src/starkware/starkware_utils:starkware_error_handling_lib",
    ],
)

py_library(
    name = "starknet_transaction_fee_lib",
    srcs = [
        "fee.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/starknet/business_logic:starknet_business_logic_utils_lib",
        "//src/starkware/starknet/business_logic/execution:starknet_execute_entry_point_lib",
        "//src/starkware/starknet/business_logic/execution:starknet_transaction_execution_objects_lib",
        "//src/starkware/starknet/business_logic/state:starknet_business_logic_state_lib",
        "//src/starkware/starknet/definitions:starknet_definitions_lib",
        "//src/starkware/starknet/definitions:starknet_general_config_lib",
        "//src/starkware/starknet/public:starknet_abi_lib",
        "//src/starkware/starknet/services/api/contract_class:starknet_contract_class_lib",
        "//src/starkware/starkware_utils:starkware_error_handling_lib",
    ],
)
