load("//bazel_utils/python:defs.bzl", "requirement")
load("//bazel_utils:python.bzl", "py_exe", "pytest_test")
load("//src/starkware/cairo:vars.bzl", "CAIRO_LANG_VENV_ADDITIONAL_LIBS", "CAIRO_VM_CRYPTO_ADDITIONAL_LIBS")

package(default_visibility = ["//visibility:public"])

py_library(
    name = "cairo_relocatable_lib",
    srcs = [
        "relocatable.py",
        "relocatable_fields.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/python:starkware_python_utils_lib",
        requirement("marshmallow"),
    ],
)

py_library(
    name = "cairo_vm_crypto_lib",
    srcs = [
        "crypto.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/common:poseidon_utils_lib",
        "//src/starkware/crypto:starkware_crypto_lib",
    ] + CAIRO_VM_CRYPTO_ADDITIONAL_LIBS,
)

py_library(
    name = "cairo_vm_lib",
    srcs = [
        "air_public_input.py",
        "builtin_runner.py",
        "cairo_pie.py",
        "memory_dict.py",
        "memory_dict_backend.py",
        "memory_segments.py",
        "output_builtin_runner.py",
        "trace_entry.py",
        "utils.py",
        "validated_memory_dict.py",
        "virtual_machine_base.py",
        "vm.py",
        "vm_consts.py",
        "vm_core.py",
        "vm_exceptions.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        ":cairo_relocatable_lib",
        "//src/starkware/cairo/lang:cairo_constants_lib",
        "//src/starkware/cairo/lang/builtins:cairo_all_builtins_lib",
        "//src/starkware/cairo/lang/builtins:instance_def_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/python:starkware_python_utils_lib",
        "//src/starkware/starknet/security:starknet_security_lib",
        "//src/starkware/starkware_utils:starkware_dataclasses_utils_lib",
        requirement("marshmallow"),
        requirement("marshmallow_dataclass"),
        requirement("typing_extensions"),
    ],
)

py_library(
    name = "cairo_run_lib",
    srcs = [
        "cairo_run.py",
        "cairo_runner.py",
        "security.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        ":cairo_relocatable_lib",
        ":cairo_vm_crypto_lib",
        ":cairo_vm_lib",
        "//src/starkware/cairo/lang:cairo_instances_lib",
        "//src/starkware/cairo/lang:cairo_version_lib",
        "//src/starkware/cairo/lang:dynamic_layout_params_lib",
        "//src/starkware/cairo/lang/builtins:cairo_run_builtins_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        # A tracer module is loaded dynamically in runtime and available with the following
        # target.
        "//src/starkware/cairo/lang/tracer:cairo_tracer_lib",
        "//src/starkware/crypto:starkware_crypto_lib",
        "//src/starkware/python:starkware_python_utils_lib",
        "//src/starkware/starkware_utils:starkware_utils_lib",
    ],
)

py_library(
    name = "cairo_vm_utils_lib",
    srcs = [
        "reconstruct_traceback.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/lang:cairo_version_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
    ],
)

py_exe(
    name = "cairo_run_exe",
    module = "starkware.cairo.lang.vm.cairo_run",
    deps = [
        "cairo_run_lib",
        "//src/starkware/cairo/bootloaders:cairo_bootloader_generate_fact_lib",
        "//src/starkware/cairo/bootloaders:cairo_hash_program_lib",
        "//src/starkware/cairo/common:cairo_common_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/cairo/lang/scripts:cairo_script_lib",
    ] + CAIRO_LANG_VENV_ADDITIONAL_LIBS,
)

py_library(
    name = "cairo_vm_test_utils_lib",
    srcs = [
        "test_utils.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "cairo_run_lib",
        "cairo_vm_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
    ],
)

pytest_test(
    name = "cairo_vm_test",
    srcs = [
        "cairo_pie_test.py",
        "cairo_runner_test.py",
        "memory_dict_test.py",
        "memory_segments_test.py",
        "output_builtin_runner_test.py",
        "reconstruct_traceback_test.py",
        "relocatable_fields_test.py",
        "relocatable_test.py",
        "security_test.py",
        "trace_entry_test.py",
        "validated_memory_dict_test.py",
        "vm_consts_test.py",
        "vm_test.py",
    ],
    data = [
        "test.cairo",
    ],
    visibility = ["//visibility:public"],
    deps = [
        ":cairo_relocatable_lib",
        ":cairo_run_lib",
        ":cairo_vm_crypto_lib",
        ":cairo_vm_lib",
        ":cairo_vm_test_utils_lib",
        ":cairo_vm_utils_lib",
        "//src/starkware/cairo/common:cairo_common_lib",
        "//src/starkware/cairo/lang:cairo_constants_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/python:starkware_python_test_utils_lib",
        "//src/starkware/python:starkware_python_utils_lib",
        "//src/starkware/starkware_utils:starkware_dataclasses_utils_lib",
        requirement("marshmallow_dataclass"),
    ],
)
