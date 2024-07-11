load("//bazel_utils/python:defs.bzl", "requirement")
load("//src/starkware/cairo/lang:cairo_rules.bzl", "cairo_binary")
load("//bazel_utils:python.bzl", "pytest_test")

package(default_visibility = ["//visibility:public"])

py_library(
    name = "cairo_aggregator_lib",
    srcs = [
        "output_parser.py",
        "utils.py",
    ],
    deps = [
        "//src/starkware/cairo/lang/vm:cairo_relocatable_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_lib",
        "//src/starkware/python:starkware_python_utils_lib",
        "//src/starkware/starknet/core/os:kzg_manager_lib",
        "//src/starkware/starknet/definitions:starknet_definitions_lib",
    ],
)

cairo_binary(
    name = "aggregator",
    srcs = [
        "combine_blocks.cairo",
        "main.cairo",
    ],
    cairoopts = [
        "--debug_info_with_source",
    ],
    compiled_program_name = "aggregator.json",
    main = "main.cairo",
    deps = [
        "//src/starkware/starknet/core/os:output",
        "//src/starkware/starknet/core/os/data_availability:bls_field",
        "//src/starkware/starknet/core/os/state:starknet_os_state_lib",
    ],
)

pytest_test(
    name = "starknet_aggregator_test",
    srcs = [
        "aggregator_test.py",
    ],
    data = [
        ":aggregator.json",
        "//src/starkware/starknet/core/os/data_availability:bls_field",
    ],
    deps = [
        ":cairo_aggregator_lib",
        "//src/starkware/cairo/bootloaders:cairo_bootloader_fact_topology_lib",
        "//src/starkware/cairo/bootloaders:cairo_bootloader_generate_fact_lib",
        "//src/starkware/cairo/common:cairo_common_validate_utils_lib",
        "//src/starkware/cairo/common:cairo_function_runner_lib",
        "//src/starkware/cairo/common:poseidon_utils_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_lib",
        "//src/starkware/python:starkware_python_test_utils_lib",
    ],
)

py_library(
    name = "aggregate_program_lib",
    srcs = [
        "aggregator_program.py",
    ],
    data = [
        "program_hash.json",
    ],
    deps = [requirement("cachetools")],
)

pytest_test(
    name = "aggregator_program_hash_test",
    srcs = [
        "program_hash_test.py",
    ],
    data = [
        "program_hash.json",
        ":aggregator",
    ],
    deps = [
        "//src/starkware/cairo/bootloaders:aggregator_utils",
        "//src/starkware/cairo/bootloaders:program_hash_test_utils_lib",
        "//src/starkware/python:starkware_python_utils_lib",
    ],
)
