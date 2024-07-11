load("//bazel_utils:python.bzl", "pytest_test")
load("//src/starkware/cairo/lang:cairo_rules.bzl", "cairo_library")
load("//bazel_utils/python:defs.bzl", "requirement")

package(default_visibility = ["//visibility:public"])

exports_files(glob(["*.cairo"]))

cairo_library(
    name = "serialize",
    srcs = [
        "serialize_utils.cairo",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/common:cairo_common_cairo_lib",
    ],
)

cairo_library(
    name = "cairo",
    srcs = [
        "air_instances.cairo",
        "air_interface.cairo",
        "channel.cairo",
        "config_instances.cairo",
        "proof_of_work.cairo",
        "queries.cairo",
        "table_commitment.cairo",
        "utils.cairo",
        "vector_commitment.cairo",
    ],
    visibility = ["//visibility:public"],
    deps = [
        ":cairo_commitment",
        "//src/starkware/cairo/common:cairo_common_cairo_lib",
        "//src/starkware/cairo/stark_verifier/core:serialize",
        "//src/starkware/cairo/stark_verifier/core/fri:fri_config",
    ],
)

cairo_library(
    name = "cairo_commitment",
    srcs = [
        "channel.cairo",
        "table_commitment.cairo",
        "utils.cairo",
        "vector_commitment.cairo",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/common:cairo_common_cairo_lib",
        "//src/starkware/cairo/stark_verifier/core:serialize",
    ],
)

cairo_library(
    name = "stark",
    srcs = [
        "config.cairo",
        "config_instances.cairo",
        "domains.cairo",
        "stark.cairo",
    ],
    visibility = ["//visibility:public"],
    deps = [
        ":cairo",
        "//src/starkware/cairo/common:cairo_common_cairo_lib",
        "//src/starkware/cairo/stark_verifier/air:cairo",
        "//src/starkware/cairo/stark_verifier/core/fri",
    ],
)

py_library(
    name = "supported_proof_params",
    srcs = [
        "supported_proof_params.py",
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
        ":cairo",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/common:cairo_common_lib",
        "//src/starkware/cairo/common:cairo_common_validate_utils_lib",
        "//src/starkware/cairo/common:cairo_function_runner_lib",
        "//src/starkware/cairo/lang:cairo_constants_lib",
        "//src/starkware/cairo/lang/builtins:cairo_run_builtins_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_lib",
        "//src/starkware/python:starkware_python_test_utils_lib",
        requirement("pytest_asyncio"),
    ],
)
