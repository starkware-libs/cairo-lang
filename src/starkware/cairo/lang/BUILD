load("//src/starkware/cairo:vars.bzl", "CAIRO_INSTANCES_LIB_ADDITIONAL_FILES")
load("//src/starkware/cairo:vars_cairo_compiler.bzl", "CAIRO_COMPILER_ARCHIVE")
load("//bazel_utils:python.bzl", "py_exe")

# Python library with all the dependencies that should be part of the cairo-lang package.
py_library(
    name = "cairo_lang_package_lib",
    srcs = [
        "create_cairo_lang_zip.py",
    ],
    data = [
        "@" + CAIRO_COMPILER_ARCHIVE,
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/bootloaders:cairo_bootloader_generate_fact_lib",
        "//src/starkware/cairo/bootloaders:cairo_hash_program_lib",
        "//src/starkware/cairo/bootloaders:program_hash_test_utils_lib",
        "//src/starkware/cairo/common:cairo_common_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_test_utils_lib",
        "//src/starkware/cairo/lang/scripts:cairo_script_lib",
        "//src/starkware/cairo/lang/vm:cairo_run_lib",
        "//src/starkware/cairo/sharp:sharp_client_config_lib",
        "//src/starkware/cairo/sharp:sharp_client_lib",
        "//src/starkware/eth:starkware_eth_test_utils_lib",
        "//src/starkware/starknet/business_logic/fact_state:starknet_business_logic_fact_state_lib",
        "//src/starkware/starknet/business_logic/state:starknet_business_logic_state_lib",
        "//src/starkware/starknet/core/os/block_hash:starknet_block_hash_lib",
        "//src/starkware/starknet/core/test_contract:starknet_test_external_contract_test_utils_lib",
        "//src/starkware/starknet/scripts:starknet_script_lib",
        "//src/starkware/starknet/services/utils:starknet_sequencer_api_utils_lib",
        "//src/starkware/starknet/testing:starknet_testing_lib",
    ],
)

# src/starkware/cairo/lang/setup.py is run inside the runfiles directory of this target
# to create the cairo-lang package zip.
py_exe(
    name = "create_cairo_lang_package_zip",
    data = [
        ":VERSION",
    ],
    module = "starkware.cairo.lang.create_cairo_lang_zip",
    deps = [
        ":cairo_lang_package_lib",
        "//src/starkware/python:starkware_python_utils_lib",
    ],
)

package(default_visibility = ["//visibility:public"])

exports_files(["cairo_constants.py"])

py_library(
    name = "cairo_version_lib",
    srcs = [
        "version.py",
    ],
    data = [
        "VERSION",
    ],
    visibility = ["//visibility:public"],
    deps = [
    ],
)

py_library(
    name = "cairo_instances_lib",
    srcs = [
        "instances.py",
    ] + CAIRO_INSTANCES_LIB_ADDITIONAL_FILES,
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/lang/builtins:cairo_all_builtins_lib",
        "//src/starkware/cairo/lang/builtins:cairo_run_builtins_lib",
        "//src/starkware/cairo/lang/builtins:instance_def_lib",
        "//src/starkware/python:starkware_python_utils_lib",
    ],
)

py_library(
    name = "cairo_constants_lib",
    srcs = [
        "cairo_constants.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
    ],
)

py_library(
    name = "dynamic_layout_params_lib",
    srcs = [
        "dynamic_layout_params.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        ":cairo_instances_lib",
        "//src/starkware/cairo/lang/builtins:cairo_all_builtins_lib",
        "//src/starkware/cairo/lang/builtins:instance_def_lib",
        "//src/starkware/python:starkware_python_utils_lib",
    ],
)
