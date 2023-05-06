load("//bazel_utils/python:defs.bzl", "requirement")
load("//bazel_utils:python.bzl", "pytest_test")

pytest_test(
    name = "cairo_blake2s_test",
    srcs = [
        "blake2s_test.py",
    ],
    data = [
        "blake2s_test.cairo",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/common:cairo_common_lib",
        "//src/starkware/cairo/common:cairo_function_runner_lib",
        "//src/starkware/cairo/lang:cairo_constants_lib",
        requirement("pytest_asyncio"),
    ],
)

exports_files([
    "blake2s.cairo",
    "blake2s_utils.py",
    "packed_blake2s.cairo",
])
