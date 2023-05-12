load("//bazel_utils:python.bzl", "pytest_test")

package(default_visibility = ["//visibility:public"])

exports_files(["cairo_verifier.cairo"])

pytest_test(
    name = "cairo_verifier_program_hash_all_cairo_test",
    srcs = [
        "program_hash_test.py",
    ],
    data = [
        "program_hash.json",
        "//src/starkware/cairo/cairo_verifier:cairo_verifier_compiled_all_cairo.json",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/bootloaders:cairo_hash_program_lib",
        "//src/starkware/cairo/bootloaders:program_hash_test_utils_lib",
    ],
)
