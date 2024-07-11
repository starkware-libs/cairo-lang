load("//src/starkware/cairo/lang:cairo_rules.bzl", "cairo_binary", "cairo_library")

cairo_library(
    name = "simple_bootloader_lib",
    srcs = [
        "execute_task.cairo",
        "run_simple_bootloader.cairo",
        "simple_bootloader.cairo",
        "//src/starkware/cairo/builtin_selection:inner_select_builtins.cairo",
        "//src/starkware/cairo/builtin_selection:select_input_builtins.cairo",
        "//src/starkware/cairo/builtin_selection:validate_builtins.cairo",
        "//src/starkware/cairo/common:cairo_builtins.cairo",
        "//src/starkware/cairo/common:ec_point.cairo",
        "//src/starkware/cairo/common:hash_chain.cairo",
        "//src/starkware/cairo/common:keccak_state.cairo",
        "//src/starkware/cairo/common:poseidon_state.cairo",
        "//src/starkware/cairo/common:registers.cairo",
        "//src/starkware/cairo/common:sha256_state.cairo",
    ],
)

cairo_binary(
    name = "simple_bootloader_program",
    cairoopts = [
        "--debug_info_with_source",
        "--proof_mode",
    ],
    compiled_program_name = "simple_bootloader_compiled.json",
    main = "simple_bootloader.cairo",
    deps = [":simple_bootloader_lib"],
)

package(default_visibility = ["//visibility:public"])

exports_files([
    "execute_task.cairo",
    "run_simple_bootloader.cairo",
])
