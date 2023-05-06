load("//bazel_utils:python.bzl", "py_exe", "pytest_test")

package(default_visibility = ["//visibility:public"])

py_library(
    name = "cairo_migrator_lib",
    srcs = [
        "migrator.py",
    ],
    data = [
        "migrator_grammar.ebnf",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
    ],
)

pytest_test(
    name = "cairo_migrator_test",
    srcs = [
        "migrator_test.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "cairo_migrator_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
    ],
)

py_exe(
    name = "cairo_migrator",
    module = "starkware.cairo.lang.migrators.migrator",
    deps = [
        "cairo_migrator_lib",
    ],
)
