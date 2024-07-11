load("//bazel_utils:python.bzl", "pytest_test")

package(default_visibility = ["//visibility:public"])

exports_files([
    "instance_def.py",
    "mod_builtin_runner.py",
])

pytest_test(
    name = "cairo_run_builtins_mod_test",
    srcs = [
        "mod_builtin_runner_test.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/lang:cairo_instances_lib",
        "//src/starkware/cairo/lang/builtins:cairo_run_builtins_lib",
        "//src/starkware/cairo/lang/builtins:cairo_run_builtins_test_utils_lib",
        "//src/starkware/cairo/lang/vm:cairo_relocatable_lib",
        "//src/starkware/cairo/lang/vm:cairo_run_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_lib",
    ],
)
