load("//bazel_utils:get_from_cairo_lang.bzl", "get_from_cairo_lang")
load("//bazel_utils/python:defs.bzl", "requirement")
load("//bazel_utils:python.bzl", "py_exe", "pytest_test")

py_library(
    name = "program_hash_test_utils_lib",
    srcs = [
        "program_hash_test_utils.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        get_from_cairo_lang("//src/starkware/cairo/bootloaders:cairo_hash_program_lib"),
    ],
)

package(default_visibility = ["//visibility:public"])

py_library(
    name = "cairo_hash_program_lib",
    srcs = [
        "hash_program.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/common:cairo_common_lib",
        "//src/starkware/cairo/lang:cairo_version_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_crypto_lib",
        "//src/starkware/python:starkware_python_utils_lib",
    ],
)

py_exe(
    name = "cairo_hash_program_exe",
    module = "starkware.cairo.bootloaders.hash_program",
    deps = [
        "cairo_hash_program_lib",
    ],
)

py_library(
    name = "cairo_bootloader_fact_topology_lib",
    srcs = [
        "fact_topology.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        requirement("marshmallow"),
        requirement("marshmallow_dataclass"),
    ],
)

py_library(
    name = "cairo_bootloader_generate_fact_lib",
    srcs = [
        "compute_fact.py",
        "generate_fact.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        ":aggregator_utils",
        ":cairo_bootloader_fact_topology_lib",
        ":cairo_hash_program_lib",
        "//src/starkware/cairo/lang/vm:cairo_relocatable_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_lib",
        "//src/starkware/python:starkware_python_utils_lib",
        requirement("eth_hash"),
    ],
)

py_library(
    name = "aggregator_utils",
    srcs = [
        "aggregator_utils.py",
    ],
    deps = [
        "//src/starkware/cairo/lang/vm:cairo_vm_crypto_lib",
        "//src/starkware/python:starkware_python_utils_lib",
    ],
)

pytest_test(
    name = "aggregator_utils_test",
    srcs = ["aggregator_utils_test.py"],
    deps = [":aggregator_utils"],
)
