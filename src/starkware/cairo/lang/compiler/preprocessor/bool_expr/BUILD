load("//bazel_utils:python.bzl", "pytest_test")

package(default_visibility = ["//visibility:public"])

exports_files([
    "__init__.py",
    "errors.py",
    "lowering.py",
    "lowering_test_utils.py",
])

pytest_test(
    name = "cairo_compile_preprocessor_bool_expr_test",
    srcs = [
        "lowering_test.py",
        "lowering_test_utils.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_test_utils_lib",
    ],
)
