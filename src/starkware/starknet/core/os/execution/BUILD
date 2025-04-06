package(default_visibility = ["//visibility:public"])

exports_files([
    "deprecated_execute_entry_point.cairo",
    "deprecated_execute_syscalls.cairo",
    "execute_entry_point.cairo",
    "execute_syscalls.cairo",
    "execute_transactions.cairo",
    "revert.cairo",
    "version_bound_accounts.cairo",
])

py_library(
    name = "version_bound_accounts_lib",
    srcs = [
        "version_bound_accounts.py",
    ],
    deps = ["//src/starkware/starknet/definitions:starknet_definitions_lib"],
)
