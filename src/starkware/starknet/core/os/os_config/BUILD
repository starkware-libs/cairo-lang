package(default_visibility = ["//visibility:public"])

exports_files([
    "os_config.cairo",
    "os_config_hash.json",
])

py_library(
    name = "starknet_os_config_hash_lib",
    srcs = [
        "os_config_hash.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/common:cairo_common_lib",
        "//src/starkware/starknet/definitions:starknet_general_config_lib",
    ],
)

py_library(
    name = "test_utils",
    srcs = [
        "test_utils.py",
    ],
    data = [
        "os_config_hash.json",
        "private_os_config_hash.json",
    ],
    visibility = ["//visibility:public"],
    deps = [
        ":starknet_os_config_hash_lib",
        "//src/starkware/python:starkware_python_utils_lib",
        "//src/starkware/starknet/definitions:starknet_general_config_lib",
    ],
)
