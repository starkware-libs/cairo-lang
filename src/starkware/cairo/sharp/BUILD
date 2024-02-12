load("//bazel_utils:python.bzl", "pytest_test")
load("//bazel_utils/python:defs.bzl", "requirement")

pytest_test(
    name = "sharp_client_lib_test",
    srcs = [
        "client_lib_test.py",
        "sharp_client_test.py",
    ],
    data = [
        "//src/starkware/cairo/lang/compiler:cairo_compile_exe",
        "//src/starkware/cairo/lang/vm:cairo_run_exe",
    ],
    visibility = ["//visibility:public"],
    deps = [
        ":sharp_client_lib",
        "//src/starkware/cairo/bootloaders:cairo_bootloader_fact_topology_lib",
        "//src/starkware/cairo/bootloaders:cairo_bootloader_generate_fact_lib",
        "//src/starkware/python:starkware_python_utils_lib",
        requirement("urllib3"),
    ],
)

package(default_visibility = ["//visibility:public"])

py_library(
    name = "fact_checker_lib",
    srcs = [
        "fact_checker.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        requirement("web3"),
    ],
)

pytest_test(
    name = "fact_checker_test",
    srcs = [
        "fact_checker_test.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "fact_checker_lib",
    ],
)

py_library(
    name = "sharp_client_lib",
    srcs = [
        "client_lib.py",
        "sharp_client.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        ":fact_checker_lib",
        "//src/starkware/cairo/bootloaders:cairo_bootloader_generate_fact_lib",
        "//src/starkware/cairo/bootloaders:cairo_hash_program_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_crypto_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_lib",
        requirement("urllib3"),
    ],
)

py_library(
    name = "sharp_client_config_lib",
    srcs = [
    ],
    data = [
        "config.json",
    ],
    visibility = ["//visibility:public"],
    deps = [
    ],
)
