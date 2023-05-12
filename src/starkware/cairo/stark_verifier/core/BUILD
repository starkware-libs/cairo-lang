load("//bazel_utils:python.bzl", "pytest_test")

package(default_visibility = ["//visibility:public"])

exports_files(glob(["*.cairo"]))

py_library(
    name = "starkware_cairo_stark_verifier_core_lib",
    srcs = [
    ],
    data = [
        "air_interface.cairo",
        "channel.cairo",
        "proof_of_work.cairo",
        "queries.cairo",
        "table_commitment.cairo",
        "utils.cairo",
        "vector_commitment.cairo",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/common:cairo_common_lib",
    ],
)

py_library(
    name = "starkware_cairo_stark_verifier_core_stark_lib",
    srcs = [
    ],
    data = [
        "config.cairo",
        "domains.cairo",
        "stark.cairo",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "starkware_cairo_stark_verifier_core_lib",
        "//src/starkware/cairo/common:cairo_common_lib",
        "//src/starkware/cairo/stark_verifier/core/fri:starkware_cairo_stark_verifier_core_fri_lib",
    ],
)

pytest_test(
    name = "starkware_cairo_stark_verifier_core_test",
    srcs = [
        "channel_test.py",
        "proof_of_work_test.py",
        "table_commitment_test.py",
        "utils_test.py",
        "vector_commitment_test.py",
    ],
    data = [
        "channel_test.cairo",
        "merkle_test_data.json",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "starkware_cairo_stark_verifier_core_lib",
        "//src/starkware/cairo/common:cairo_common_lib",
        "//src/starkware/cairo/common:cairo_common_validate_utils_lib",
        "//src/starkware/cairo/common:cairo_function_runner_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/python:starkware_python_test_utils_lib",
    ],
)
