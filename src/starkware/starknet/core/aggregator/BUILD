load("//src/starkware/starknet/compiler/fixed_version_compiler:compile_in_fixed_venv.bzl", "cairo_compile_os_fixed_version")
load("//bazel_utils/python:defs.bzl", "requirement")
load("//src/starkware/cairo/lang:cairo_rules.bzl", "cairo_library")
load("//bazel_utils:python.bzl", "pytest_test")

package(default_visibility = ["//visibility:public"])

exports_files(["program_hash.json"])

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
        "//src/starkware/starknet/core/os/data_availability:compression",
        "//src/starkware/starknet/definitions:starknet_definitions_lib",
    ],
)

cairo_library(
    name = "aggregator_cairo_lib",
    srcs = [
        "combine_blocks.cairo",
        "main.cairo",
    ],
    hint_deps = [
        "//src/starkware/starknet/core/os:kzg_manager_lib",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/starknet/core/os:output",
        "//src/starkware/starknet/core/os/data_availability:bls_field",
        "//src/starkware/starknet/core/os/state:starknet_os_state_lib",
    ],
)

cairo_compile_os_fixed_version(
    name = "aggregator",
    cairo_lang_version = "0.14.0a1",
    cairoopts = [
        "--debug_info_with_source",
    ],
    compiled_program_name = "aggregator.json",
    main = "main.cairo",
    deps = [":aggregator_cairo_lib"],
)

pytest_test(
    name = "starknet_aggregator_test",
    srcs = [
        "aggregator_test.py",
    ],
    data = [
        ":aggregator",
        "//src/starkware/starknet/core/os/data_availability:bls_field",
    ],
    deps = [
        ":aggregate_program_lib",
        ":cairo_aggregator_lib",
        "//src/starkware/cairo/bootloaders:cairo_bootloader_fact_topology_lib",
        "//src/starkware/cairo/bootloaders:cairo_bootloader_generate_fact_lib",
        "//src/starkware/cairo/common:cairo_common_validate_utils_lib",
        "//src/starkware/cairo/common:cairo_function_runner_lib",
        "//src/starkware/cairo/common:poseidon_utils_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_lib",
        "//src/starkware/python:starkware_python_test_utils_lib",
        "//src/starkware/starknet/core/os/data_availability:compression",
    ],
)

py_library(
    name = "aggregate_program_lib",
    srcs = [
        "aggregator_program.py",
    ],
    data = [
        "aggregator.json",
        "program_hash.json",
    ],
    deps = [
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/python:starkware_python_utils_lib",
        requirement("cachetools"),
    ],
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
        ":cairo_aggregator_lib",
        "//src/starkware/cairo/bootloaders:aggregator_utils",
        "//src/starkware/cairo/bootloaders:program_hash_test_utils_lib",
        "//src/starkware/python:starkware_python_utils_lib",
    ],
)
