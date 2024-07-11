load("//src/starkware/cairo:vars.bzl", "CAIRO_COMMON_LIB_ADDITIONAL_FILES", "CAIRO_COMMON_LIB_ADDITIONAL_LIBS")
load("//src/starkware/cairo/lang:cairo_rules.bzl", "cairo_library")
load("//bazel_utils/python:defs.bzl", "requirement")

cairo_library(
    name = "cairo_common_cairo_lib",
    srcs = [
        "alloc.cairo",
        "bitwise.cairo",
        "bool.cairo",
        "cairo_builtins.cairo",
        "default_dict.cairo",
        "dict.cairo",
        "dict_access.cairo",
        "ec.cairo",
        "ec_point.cairo",
        "find_element.cairo",
        "hash.cairo",
        "hash_chain.cairo",
        "hash_state.cairo",
        "hash_state_poseidon.cairo",
        "invoke.cairo",
        "keccak.cairo",
        "keccak_state.cairo",
        "math.cairo",
        "math_cmp.cairo",
        "memcpy.cairo",
        "memset.cairo",
        "merkle_multi_update.cairo",
        "merkle_update.cairo",
        "modulo.cairo",
        "patricia.cairo",
        "patricia_utils.cairo",
        "patricia_with_poseidon.cairo",
        "patricia_with_sponge.cairo",
        "poseidon_state.cairo",
        "pow.cairo",
        "registers.cairo",
        "segments.cairo",
        "serialize.cairo",
        "set.cairo",
        "sha256_state.cairo",
        "signature.cairo",
        "small_merkle_tree.cairo",
        "sponge_as_hash.cairo",
        "squash_dict.cairo",
        "uint256.cairo",
        "usort.cairo",
        "//src/starkware/cairo/common/builtin_keccak:keccak.cairo",
        "//src/starkware/cairo/common/builtin_poseidon:poseidon.cairo",
        "//src/starkware/cairo/common/cairo_blake2s:blake2s.cairo",
        "//src/starkware/cairo/common/cairo_blake2s:packed_blake2s.cairo",
        "//src/starkware/cairo/common/cairo_keccak:keccak.cairo",
        "//src/starkware/cairo/common/cairo_keccak:packed_keccak.cairo",
        "//src/starkware/cairo/common/cairo_sha256:sha256_utils.cairo",
        "//src/starkware/cairo/common/keccak_utils:keccak_utils.cairo",
    ] + CAIRO_COMMON_LIB_ADDITIONAL_FILES,
    hint_deps = [
        "//src/starkware/crypto:starkware_crypto_lib",
        "//src/starkware/python:starkware_python_utils_lib",
        requirement("eth_hash"),
    ],
    deps = [
        "//src/starkware/cairo/common/cairo_secp:cairo_secp256k1",
        "//src/starkware/cairo/common/secp256r1:cairo_secp256r1",
    ],
)

py_library(
    name = "poseidon_utils_lib",
    srcs = [
        "poseidon_hash.py",
        "poseidon_utils.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/lang:cairo_constants_lib",
        "//src/starkware/python:starkware_python_utils_lib",
        requirement("numpy"),
    ],
)

py_library(
    name = "cairo_common_lib",
    srcs = [
        "dict.py",
        "hash_chain.py",
        "hash_state.py",
        "math_utils.py",
        "patricia_utils.py",
        "small_merkle_tree.py",
        "structs.py",
        "//src/starkware/cairo/common/cairo_blake2s:blake2s_utils.py",
        "//src/starkware/cairo/common/cairo_keccak:keccak_utils.py",
        "//src/starkware/cairo/common/cairo_secp:secp256r1_utils.py",
        "//src/starkware/cairo/common/cairo_secp:secp_utils.py",
        "//src/starkware/cairo/common/cairo_sha256:sha256_utils.py",
        "//src/starkware/cairo/common/keccak_utils:keccak_utils.py",
    ],
    data = [
        ":cairo_common_cairo_lib",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "poseidon_utils_lib",
        "//src/starkware/cairo/lang:cairo_constants_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_crypto_lib",
        "//src/starkware/python:starkware_merkle_tree_lib",
        "//src/starkware/python:starkware_python_utils_lib",
    ] + CAIRO_COMMON_LIB_ADDITIONAL_LIBS,
)

package(default_visibility = ["//visibility:public"])

exports_files(glob([
    "*.cairo",
    "*.py",
]))

py_library(
    name = "cairo_common_validate_utils_lib",
    srcs = [
        "validate_utils.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/lang/builtins:cairo_run_builtins_lib",
        "//src/starkware/cairo/lang/vm:cairo_run_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_lib",
        "//src/starkware/python:starkware_python_utils_lib",
    ],
)

py_library(
    name = "cairo_function_runner_lib",
    srcs = [
        "cairo_function_runner.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        ":cairo_common_lib",
        "//src/starkware/cairo/lang/builtins:cairo_run_builtins_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/cairo/lang/tracer:cairo_tracer_lib",
        "//src/starkware/cairo/lang/vm:cairo_relocatable_lib",
        "//src/starkware/cairo/lang/vm:cairo_run_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_crypto_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_lib",
        "//src/starkware/python:starkware_python_utils_lib",
    ],
)
