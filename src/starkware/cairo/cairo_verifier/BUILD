load("//src/starkware/cairo/lang:cairo_rules.bzl", "cairo_library")
load(
    "//src/starkware/cairo/cairo_verifier:cairo_verifier_layout_program.bzl",
    "cairo_verifier_program",
)
load("cairo_verifier_layouts.bzl", "CAIRO_LAYOUTS")

cairo_library(
    name = "cairo_verifier",
    srcs = [
        "objects.cairo",
        "//src/starkware/cairo/lang/compiler/lib:registers.cairo",
    ],
    deps = [
        "//src/starkware/cairo/common:cairo_common_cairo_lib",
        "//src/starkware/cairo/stark_verifier/core:stark",
        "//src/starkware/cairo/stark_verifier/core/fri",
    ],
)

CAIRO_VERIFIER_LAYOUT_PROGRAM_OUTPUTS = [
    cairo_verifier_program(layout_name = layout_name)
    for layout_name in CAIRO_LAYOUTS
]

CAIRO_VERIFIER_PROGRAM_ARTIFACTS_ALL_LAYOUTS = [
    output.compiled_program_name
    for output in CAIRO_VERIFIER_LAYOUT_PROGRAM_OUTPUTS
]

package(default_visibility = ["//visibility:public"])

exports_files([
    "example_proof.json",
    "objects.cairo",
])
