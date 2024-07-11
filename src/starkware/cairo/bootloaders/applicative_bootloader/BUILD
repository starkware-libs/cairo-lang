load("//src/starkware/cairo/lang:cairo_rules.bzl", "cairo_binary", "cairo_library")

cairo_library(
    name = "applicative_bootloader_lib",
    srcs = [
        "applicative_bootloader.cairo",
    ],
    deps = ["//src/starkware/cairo/bootloaders/bootloader:bootloader_lib"],
)

cairo_binary(
    name = "applicative_bootloader_program",
    cairoopts = [
        "--debug_info_with_source",
        "--proof_mode",
    ],
    compiled_program_name = "applicative_bootloader_compiled.json",
    main = "applicative_bootloader.cairo",
    deps = [":applicative_bootloader_lib"],
)

package(default_visibility = ["//visibility:public"])
