load("//bazel_utils:python.bzl", "pytest_test")

package(default_visibility = ["//visibility:public"])

exports_files([
    "instance_def.py",
    "signature_builtin_runner.py",
])

pytest_test(
    name = "cairo_run_builtins_signature_test",
    srcs = [
        "signature_builtin_runner_test.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/lang/builtins:cairo_run_builtins_test_utils_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_lib",
        "//src/starkware/python:starkware_python_test_utils_lib",
    ],
)
