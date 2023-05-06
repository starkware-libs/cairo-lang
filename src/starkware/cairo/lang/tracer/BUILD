load("//bazel_utils/python:defs.bzl", "requirement")
load("//bazel_utils:python.bzl", "pytest_test")

package(default_visibility = ["//visibility:public"])

py_library(
    name = "cairo_tracer_lib",
    srcs = [
        "profile.py",
        "profiler.py",
        "tracer.py",
        "tracer_data.py",
        "//src/starkware/cairo/lang/tracer/third_party:profile_pb2.py",
    ],
    data = [
        "favicon.png",
        "index.html",
        "tracer.css",
        "tracer.js",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_lib",
        requirement("protobuf"),
    ],
)

pytest_test(
    name = "cairo_tracer_test",
    srcs = [
        "tracer_data_test.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "cairo_tracer_lib",
        "//src/starkware/cairo/lang/vm:cairo_run_lib",
    ],
)
