load("//bazel_utils:python.bzl", "pytest_test")

package(default_visibility = ["//visibility:public"])

exports_files([
    "ec_op_builtin_runner.py",
    "instance_def.py",
])

pytest_test(
    name = "cairo_run_builtins_ec_op_test",
    srcs = [
        "ec_op_builtin_runner_test.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/lang/builtins:cairo_run_builtins_test_utils_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_lib",
        "//src/starkware/crypto:starkware_crypto_lib",
        "//src/starkware/python:starkware_python_utils_lib",
    ],
)
