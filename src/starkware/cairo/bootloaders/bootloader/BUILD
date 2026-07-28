load("//src/starkware/cairo/lang:cairo_rules.bzl", "cairo_binary", "cairo_library")
load("//bazel_utils:python.bzl", "py_exe", "pytest_test")

cairo_library(
    name = "run_bootloader_lib",
    srcs = [
        "constants.cairo",
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

py_exe(
    name = "cairo_bootloader_config_hash_fix",
    additional_srcs = ["bootloader_config_hash_test.py"],
    args = [
        "--fix",
    ],
    data = ["bootloader_config_hash.json"],
    module = "starkware.cairo.bootloaders.bootloader.bootloader_config_hash_test",
    deps = [
        ":supported_program_hashes_utils",
        "//src/starkware/cairo/bootloaders:supported_bootloaders_hash",
        "//src/starkware/cairo/common:cairo_common_lib",
        "//src/starkware/python:starkware_python_utils_lib",
    ],
)

package(default_visibility = ["//visibility:public"])

exports_files(["bootloader_config_hash.json"])

pytest_test(
    name = "cairo_bootloader_config_hash_test",
    srcs = [
        "bootloader_config_hash_test.py",
    ],
    data = [
        "bootloader_config_hash.json",
    ],
    visibility = ["//visibility:public"],
    deps = [
        ":supported_program_hashes_utils",
        "//src/starkware/cairo/bootloaders:supported_bootloaders_hash",
        "//src/starkware/cairo/common:cairo_common_lib",
        "//src/starkware/python:starkware_python_utils_lib",
    ],
)

py_library(
    name = "supported_program_hashes_utils",
    srcs = ["supported_program_hashes_utils.py"],
    data = ["supported_program_hashes.json"],
    visibility = ["//visibility:public"],
)
