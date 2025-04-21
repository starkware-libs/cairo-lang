package(default_visibility = ["//visibility:public"])

exports_files([
    "deprecated_execute_entry_point.cairo",
    "deprecated_execute_syscalls.cairo",
    "execute_entry_point.cairo",
    "execute_syscalls.cairo",
    "execute_transaction_utils.cairo",
    "execute_transactions.cairo",
    "revert.cairo",
    "account_backward_compatibility.cairo",
])

py_library(
    name = "account_backward_compatibility_lib",
    srcs = [
        "account_backward_compatibility.py",
    ],
    deps = ["//src/starkware/starknet/definitions:starknet_definitions_lib"],
)
