load("//bazel_utils/python:defs.bzl", "requirement")
load("//bazel_utils:python.bzl", "pytest_test")

py_library(
    name = "starkware_cairo_stark_verifier_air_test_base_lib",
    srcs = [
        "stark_test_utils.py",
    ],
    data = [
        "example_proof.json",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "starkware_cairo_stark_verifier_air_lib",
        "//src/starkware/cairo/common:cairo_common_lib",
        "//src/starkware/cairo/common:cairo_common_validate_utils_lib",
        "//src/starkware/cairo/common:cairo_function_runner_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/cairo/stark_verifier/air/layouts:starkware_cairo_stark_verifier_air_starknet_with_keccak_lib",
        "//src/starkware/cairo/stark_verifier/core:starkware_cairo_stark_verifier_core_stark_lib",
        "//src/starkware/python:starkware_python_utils_lib",
        requirement("eth_hash"),
    ],
)

package(default_visibility = ["//visibility:public"])

exports_files(glob([
    "*.cairo",
    "*.json",
]))

py_library(
    name = "starkware_cairo_stark_verifier_air_lib",
    srcs = [
        "parser.py",
        "utils.py",
    ],
    data = [
        "config.cairo",
        "diluted.cairo",
        "layout.cairo",
        "oods.cairo",
        "params.cairo",
        "public_input.cairo",
        "public_memory.cairo",
        "traces.cairo",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/stark_verifier/core:starkware_cairo_stark_verifier_core_stark_lib",
    ],
)

pytest_test(
    name = "starkware_cairo_stark_verifier_air_test",
    srcs = [
        "stark_test.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "starkware_cairo_stark_verifier_air_test_base_lib",
    ],
)
