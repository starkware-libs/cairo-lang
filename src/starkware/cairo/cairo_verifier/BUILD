load("//src/starkware/cairo/lang:cairo_rules.bzl", "cairo_library")
load(
    "//src/starkware/cairo/cairo_verifier:cairo_verifier_layout_program.bzl",
    "cairo_verifier_program",
)
load("cairo_verifier_layouts.bzl", "CAIRO_LAYOUTS")

cairo_library(
    name = "cairo_verifier_lib",
    srcs = [
        "objects.cairo",
        "//src/starkware/cairo/lang/compiler/lib:registers.cairo",
        "//src/starkware/cairo/stark_verifier/core:air_interface.cairo",
        "//src/starkware/cairo/stark_verifier/core:channel.cairo",
        "//src/starkware/cairo/stark_verifier/core:config.cairo",
        "//src/starkware/cairo/stark_verifier/core:domains.cairo",
        "//src/starkware/cairo/stark_verifier/core:proof_of_work.cairo",
        "//src/starkware/cairo/stark_verifier/core:queries.cairo",
        "//src/starkware/cairo/stark_verifier/core:stark.cairo",
        "//src/starkware/cairo/stark_verifier/core:table_commitment.cairo",
        "//src/starkware/cairo/stark_verifier/core:utils.cairo",
        "//src/starkware/cairo/stark_verifier/core:vector_commitment.cairo",
        "//src/starkware/cairo/stark_verifier/core/fri:config.cairo",
        "//src/starkware/cairo/stark_verifier/core/fri:fri.cairo",
        "//src/starkware/cairo/stark_verifier/core/fri:fri_formula.cairo",
        "//src/starkware/cairo/stark_verifier/core/fri:fri_layer.cairo",
    ],
    deps = ["//src/starkware/cairo/common:cairo_common_cairo_lib"],
)

cairo_library(
    name = "cairo_verifier_program_lib",
    srcs = [
        "//src/starkware/cairo/stark_verifier/air:config.cairo",
        "//src/starkware/cairo/stark_verifier/air:diluted.cairo",
        "//src/starkware/cairo/stark_verifier/air:layout.cairo",
        "//src/starkware/cairo/stark_verifier/air:oods.cairo",
        "//src/starkware/cairo/stark_verifier/air:public_input.cairo",
        "//src/starkware/cairo/stark_verifier/air:public_memory.cairo",
        "//src/starkware/cairo/stark_verifier/air:traces.cairo",
    ],
    deps = [":cairo_verifier_lib"],
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
