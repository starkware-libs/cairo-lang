load("//src/starkware/cairo/lang:cairo_rules.bzl", "cairo_binary", "cairo_library")

package(default_visibility = ["//visibility:public"])

cairo_library(
    name = "circuit_applicative_bootloader_lib",
    srcs = [
        "circuit_applicative_bootloader.cairo",
        "circuit_unpack.cairo",
        "config_commitment.cairo",
    ],
    deps = [
        "//src/starkware/cairo/bootloaders/bootloader:bootloader_lib",
    ],
)

cairo_binary(
    name = "circuit_applicative_bootloader_program",
    cairoopts = [
        "--debug_info_with_source",
        "--proof_mode",
    ],
    compiled_program_name = "circuit_applicative_bootloader_compiled.json",
    main = "circuit_applicative_bootloader.cairo",
    deps = [":circuit_applicative_bootloader_lib"],
)

# A committed copy of the circuit registry the proving repo published at the commit recorded in
# the bootloaders README, the file the proving binaries are given. A monorepo test compares the
# copy with the published registry and regenerates it in fix mode.
# Committed rather than read from the artifacts bucket for two reasons: this package is
# externalized (see external.txt), so it must not depend on a private bucket, and the circuit
# hashes in it are the unpacking's trust anchors, so changing them belongs in a reviewable diff.
filegroup(
    name = "production_circuit_registry_json",
    srcs = ["production_circuit_registry.json"],
)

# The committed inputs of the config commitment and the Python mirror of config_commitment.cairo.
# Externalized so the commitment the bootloader config carries can be recomputed without the
# artifacts bucket.
py_library(
    name = "circuit_applicative_bootloader_config_commitment_lib",
    srcs = ["config_commitment.py"],
    data = [
        "circuit_verifier_program_hash.json",
        ":production_circuit_registry_json",
    ],
    deps = ["//src/starkware/cairo/common:cairo_common_lib"],
)
