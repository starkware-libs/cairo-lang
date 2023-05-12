load("//bazel_utils:python.bzl", "pytest_test")

package(default_visibility = ["//visibility:public"])

exports_files(glob(["*.py"]))

pytest_test(
    name = "cairo_compile_formatting_test",
    srcs = [
        "parentheses_expr_wrapper_test.py",
        "particle_test.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_test_utils_lib",
    ],
)
