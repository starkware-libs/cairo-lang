load("//src/starkware/cairo/lang:cairo_rules.bzl", "cairo_library")
load("//bazel_utils:python.bzl", "pytest_test")

cairo_library(
    name = "cairo_builtin_selection_cairo_lib",
    srcs = [
        "inner_select_builtins.cairo",
        "select_builtins.cairo",
        "select_input_builtins.cairo",
        "validate_builtins.cairo",
    ],
)

py_library(
    name = "cairo_builtin_selection_lib",
    data = [
        ":cairo_builtin_selection_cairo_lib",
    ],
    visibility = ["//visibility:public"],
)

package(default_visibility = ["//visibility:public"])

exports_files([
    "inner_select_builtins.cairo",
    "select_input_builtins.cairo",
    "validate_builtins.cairo",
])

pytest_test(
    name = "cairo_builtin_selection_test",
    srcs = [
        "select_input_builtins_test.py",
        "validate_builtins_test.py",
    ],
    data = [
        ":cairo_builtin_selection_cairo_lib",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/common:cairo_function_runner_lib",
        "//src/starkware/cairo/lang:cairo_constants_lib",
        "//src/starkware/cairo/lang:cairo_instances_lib",
        "//src/starkware/cairo/lang/builtins:cairo_all_builtins_lib",
        "//src/starkware/cairo/lang/builtins:cairo_run_builtins_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_lib",
        "//src/starkware/python:starkware_python_test_utils_lib",
        "//src/starkware/python:starkware_python_utils_lib",
    ],
)
