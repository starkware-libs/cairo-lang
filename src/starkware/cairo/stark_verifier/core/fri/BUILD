load("//bazel_utils:python.bzl", "pytest_test")
load("//src/starkware/cairo/lang:cairo_rules.bzl", "cairo_library")

package(default_visibility = ["//visibility:public"])

cairo_library(
    name = "fri_config",
    srcs = [
        "config.cairo",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/common:cairo_common_cairo_lib",
        "//src/starkware/cairo/stark_verifier/core:cairo_commitment",
    ],
)

cairo_library(
    name = "fri",
    srcs = [
        "fri.cairo",
        "fri_formula.cairo",
        "fri_layer.cairo",
    ],
    visibility = ["//visibility:public"],
    deps = [
        ":fri_config",
        "//src/starkware/cairo/common:cairo_common_cairo_lib",
        "//src/starkware/cairo/stark_verifier/core:cairo",
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
    data = [":fri"],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/common:cairo_function_runner_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/python:starkware_python_test_utils_lib",
    ],
)
