package(default_visibility = ["//visibility:public"])

py_library(
    name = "instance_def_lib",
    srcs = [
        "instance_def.py",
    ],
    visibility = ["//visibility:public"],
)

py_library(
    name = "cairo_run_builtins_lib",
    srcs = [
        "//src/starkware/cairo/lang/builtins/bitwise:bitwise_builtin_runner.py",
        "//src/starkware/cairo/lang/builtins/bitwise:instance_def.py",
        "//src/starkware/cairo/lang/builtins/ec:ec_op_builtin_runner.py",
        "//src/starkware/cairo/lang/builtins/ec:instance_def.py",
        "//src/starkware/cairo/lang/builtins/hash:hash_builtin_runner.py",
        "//src/starkware/cairo/lang/builtins/hash:instance_def.py",
        "//src/starkware/cairo/lang/builtins/keccak:instance_def.py",
        "//src/starkware/cairo/lang/builtins/keccak:keccak_builtin_runner.py",
        "//src/starkware/cairo/lang/builtins/modulo:instance_def.py",
        "//src/starkware/cairo/lang/builtins/modulo:mod_builtin_runner.py",
        "//src/starkware/cairo/lang/builtins/poseidon:instance_def.py",
        "//src/starkware/cairo/lang/builtins/poseidon:poseidon_builtin_runner.py",
        "//src/starkware/cairo/lang/builtins/range_check:instance_def.py",
        "//src/starkware/cairo/lang/builtins/range_check:range_check_builtin_runner.py",
        "//src/starkware/cairo/lang/builtins/signature:instance_def.py",
        "//src/starkware/cairo/lang/builtins/signature:signature_builtin_runner.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        ":instance_def_lib",
        "//src/starkware/cairo/common:cairo_common_lib",
        "//src/starkware/cairo/lang/vm:cairo_relocatable_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_crypto_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_lib",
        "//src/starkware/crypto:starkware_crypto_lib",
        "//src/starkware/python:starkware_python_utils_lib",
    ],
)

py_library(
    name = "cairo_all_builtins_lib",
    srcs = [
        "all_builtins.py",
    ],
    visibility = ["//visibility:public"],
)

py_library(
    name = "cairo_run_builtins_test_utils_lib",
    srcs = [
        "builtin_runner_test_utils.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/lang:cairo_instances_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/cairo/lang/vm:cairo_run_lib",
    ],
)
