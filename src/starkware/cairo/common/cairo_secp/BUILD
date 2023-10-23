load("//src/starkware/cairo/lang:cairo_rules.bzl", "cairo_library")

package(default_visibility = ["//visibility:public"])

exports_files(glob([
    "*.cairo",
    "*.py",
]))

py_library(
    name = "utils",
    srcs = ["secp_utils.py"],
    deps = ["//src/starkware/cairo/common:cairo_common_lib"],
)

cairo_library(
    name = "cairo_secp256k1",
    srcs = [
        "bigint.cairo",
        "bigint3.cairo",
        "constants.cairo",
        "ec.cairo",
        "ec_point.cairo",
        "field.cairo",
        "signature.cairo",
    ],
)
