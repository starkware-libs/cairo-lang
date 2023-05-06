load("//bazel_utils:python.bzl", "pytest_test")

package(default_visibility = ["//visibility:public"])

exports_files([
    "config.cairo",
    "fri.cairo",
    "fri_formula.cairo",
    "fri_layer.cairo",
])

py_library(
    name = "starkware_cairo_stark_verifier_core_fri_lib",
    srcs = [
    ],
    data = [
        "config.cairo",
        "fri.cairo",
        "fri_formula.cairo",
        "fri_layer.cairo",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/common:cairo_common_lib",
        "//src/starkware/cairo/stark_verifier/core:starkware_cairo_stark_verifier_core_lib",
    ],
)

pytest_test(
    name = "starkware_cairo_stark_verifier_core_fri_test",
    srcs = [
        "fri_formula_test.py",
        "fri_layer_test.py",
        "fri_test.py",
        "test_utils.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "starkware_cairo_stark_verifier_core_fri_lib",
        "//src/starkware/cairo/common:cairo_function_runner_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/python:starkware_python_test_utils_lib",
    ],
)
