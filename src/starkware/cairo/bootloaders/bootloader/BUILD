load("//src/starkware/cairo/lang:cairo_rules.bzl", "cairo_binary", "cairo_library")

cairo_library(
    name = "run_bootloader_lib",
    srcs = [
        "run_bootloader.cairo",
        "//src/starkware/cairo/bootloaders/simple_bootloader:execute_task.cairo",
        "//src/starkware/cairo/bootloaders/simple_bootloader:run_simple_bootloader.cairo",
        "//src/starkware/cairo/builtin_selection:inner_select_builtins.cairo",
        "//src/starkware/cairo/builtin_selection:select_input_builtins.cairo",
        "//src/starkware/cairo/builtin_selection:validate_builtins.cairo",
        "//src/starkware/cairo/cairo_verifier:objects.cairo",
        "//src/starkware/cairo/common:bool.cairo",
        "//src/starkware/cairo/common:cairo_builtins.cairo",
        "//src/starkware/cairo/common:ec_point.cairo",
        "//src/starkware/cairo/common:find_element.cairo",
        "//src/starkware/cairo/common:hash.cairo",
        "//src/starkware/cairo/common:hash_chain.cairo",
        "//src/starkware/cairo/common:hash_state.cairo",
        "//src/starkware/cairo/common:keccak_state.cairo",
        "//src/starkware/cairo/common:math.cairo",
        "//src/starkware/cairo/common:memcpy.cairo",
        "//src/starkware/cairo/common:poseidon_state.cairo",
        "//src/starkware/cairo/common:registers.cairo",
        "//src/starkware/cairo/common:sha256_state.cairo",
        "//src/starkware/cairo/lang/compiler/lib:registers.cairo",
    ],
)

cairo_library(
    name = "bootloader_lib",
    srcs = [
        "bootloader.cairo",
    ],
    deps = [":run_bootloader_lib"],
)

cairo_binary(
    name = "bootloader_program",
    cairoopts = [
        "--debug_info_with_source",
        "--proof_mode",
    ],
    compiled_program_name = "bootloader_compiled.json",
    main = "bootloader.cairo",
    deps = [":bootloader_lib"],
)

package(default_visibility = ["//visibility:public"])

exports_files(["bootloader_config_hash.json"])
