load("//bazel_utils:python.bzl", "pytest_test")
load("//src/starkware/cairo/lang:cairo_rules.bzl", "cairo_library")

py_library(
    name = "starkware_cairo_stark_verifier_air_test_base_lib",
    srcs = [
        "stark_test_utils.py",
    ],
    data = [
        "example_proof.json",
        "//src/starkware/cairo/stark_verifier/air/layouts/starknet_with_keccak",
        "//src/starkware/cairo/stark_verifier/core:stark",
        "//src/starkware/cairo/stark_verifier/core/fri",
    ],
    visibility = ["//visibility:public"],
    deps = [
        ":python",
        "//src/starkware/cairo/common:cairo_common_validate_utils_lib",
        "//src/starkware/cairo/common:cairo_function_runner_lib",
        "//src/starkware/cairo/lang:cairo_constants_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
    ],
)

package(default_visibility = ["//visibility:public"])

exports_files(glob([
    "*.cairo",
    "*.json",
]))

cairo_library(
    name = "cairo",
    srcs = [
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
        "//src/starkware/cairo/common:cairo_common_cairo_lib",
        "//src/starkware/cairo/stark_verifier/core:cairo",
        "//src/starkware/cairo/stark_verifier/core:serialize",
    ],
)

py_library(
    name = "python",
    srcs = [
        "parser.py",
        "utils.py",
    ],
    data = [":cairo"],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/common:cairo_common_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_lib",
        "//src/starkware/python:starkware_python_utils_lib",
    ],
)

pytest_test(
    name = "starkware_cairo_stark_verifier_air_test",
    srcs = [
        "stark_test.py",
    ],
    visibility = ["//visibility:public"],
    deps = [":starkware_cairo_stark_verifier_air_test_base_lib"],
)
