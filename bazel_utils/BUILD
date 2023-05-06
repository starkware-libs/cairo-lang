load("//bazel_utils:python.bzl", "py_exe")

package(default_visibility = ["//visibility:public"])

exports_files(["pytest_wrapper.py"])

py_binary(
    name = "gen_python_exe",
    srcs = ["gen_python_exe.py"],
    main = "gen_python_exe.py",
)

py_binary(
    name = "solc_wrapper",
    srcs = ["solc_wrapper.py"],
)

sh_binary(
    name = "solc-0.6.12",
    srcs = ["@solc-0.6.12//file"],
)

py_library(
    name = "default_extract_artifacts_lib",
    srcs = [
        "__init__.py",
        "extract_artifacts.py",
    ],
    visibility = ["//visibility:public"],
    deps = [],
)

py_exe(
    name = "default_extract_artifacts_exe",
    module = "bazel_utils.extract_artifacts",
    deps = ["default_extract_artifacts_lib"],
)
