load("@rules_python//python:defs.bzl", "py_runtime", "py_runtime_pair")
load(":defs.bzl", "python_version_info")

python_version_info(
    name = "python_version",
    build_setting_default = "",
    visibility = ["//visibility:public"],
)

config_setting(
    name = "pypy",
    flag_values = {":python_version": "pypy"},
)

config_setting(
    name = "cpython",
    flag_values = {":python_version": "cpython"},
)

py_runtime(
    name = "python_stub_runtime",
    files = [
        "@bazel_tools//tools/bash/runfiles",
        "@python3//:files",
    ],
    interpreter = "//bazel_utils/python:stub.sh",
    python_version = "PY3",
    visibility = ["//visibility:public"],
)

py_runtime_pair(
    name = "py_stub_runtime_pair",
    py2_runtime = None,
    py3_runtime = ":python_stub_runtime",
)

toolchain(
    name = "py_stub_toolchain",
    toolchain = ":py_stub_runtime_pair",
    toolchain_type = "@bazel_tools//tools/python:toolchain_type",
)
