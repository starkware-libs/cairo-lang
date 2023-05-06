package(default_visibility = ["//visibility:public"])

py_library(
    name = "cairo_script_lib",
    srcs = [
    ],
    data = [
        "cairo-compile",
        "cairo-format",
        "cairo-hash-program",
        "cairo-migrate",
        "cairo-reconstruct-traceback",
        "cairo-run",
        "cairo-sharp",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/bootloaders:cairo_hash_program_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/cairo/lang/migrators:cairo_migrator_lib",
        "//src/starkware/cairo/lang/vm:cairo_run_lib",
        "//src/starkware/cairo/lang/vm:cairo_vm_utils_lib",
        "//src/starkware/cairo/sharp:sharp_client_lib",
    ],
)
