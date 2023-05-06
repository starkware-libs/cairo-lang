SolidityInfo = provider(fields = ["transitive_sources"])

def get_transitive_solidity_srcs(srcs, deps):
    """
    Returns the Solidity source files for a target and its transitive dependencies.
    """
    return depset(srcs, transitive = [dep[SolidityInfo].transitive_sources for dep in deps])

# Rule for a library of Solidity files (similar to py_library).

def _solidity_library_impl(ctx):
    trans_srcs = get_transitive_solidity_srcs(srcs = ctx.files.srcs, deps = ctx.attr.deps)
    return [
        SolidityInfo(transitive_sources = trans_srcs),
    ]

sol_library = rule(
    implementation = _solidity_library_impl,
    attrs = {
        "srcs": attr.label_list(allow_files = [".sol"]),
        "deps": attr.label_list(providers = [SolidityInfo]),
    },
)

def _sol_contract_impl(ctx):
    """
    Compiles a Solidity contract.
    """
    trans_srcs = get_transitive_solidity_srcs(srcs = [], deps = ctx.attr.deps)
    srcs_list = trans_srcs.to_list()

    combined_json = ctx.actions.declare_file("_%s/combined.json" % ctx.attr.name)

    if ctx.executable.solc_exe.basename == "solc-0.6.12":
        ctx.actions.run(
            executable = ctx.executable._solc_wrapper,
            arguments = [
                "--solc",
                ctx.executable.solc_exe.path,
                "--optimize_runs",
                str(ctx.attr.optimize_runs),
                "--base_path",
                ctx.attr.include_path,
                "--output",
                combined_json.dirname,
                "--srcs",
            ] + [f.path for f in srcs_list],
            inputs = srcs_list + ctx.files.solc_exe,
            outputs = [combined_json],
        )
    else:  # solc-0.8.16
        ctx.actions.run(
            executable = ctx.executable.solc_exe,
            arguments = [
                "--optimize",
                "--optimize-runs",
                str(ctx.attr.optimize_runs),
                "--combined-json",
                "abi,bin",
                "--base-path",
                ".",
                "--include-path",
                ctx.attr.include_path,
                "-o",
                combined_json.dirname,
            ] + [f.path for f in srcs_list],
            inputs = srcs_list,
            outputs = [combined_json],
        )

    if ctx.label.workspace_root == "":
        current_dir = "/".join([combined_json.root.path, ctx.label.package])
    else:
        current_dir = (
            "/".join([combined_json.root.path, ctx.label.workspace_root, ctx.label.package])
        )
    outputs = [ctx.actions.declare_file(f) for f in ctx.attr.contracts]
    ctx.actions.run(
        executable = ctx.executable.extract_artifacts_exe,
        arguments = [
            "--input_json",
            combined_json.path,
            "--artifacts_dir",
            current_dir,
            "--source_dir",
            ctx.label.package,
            "--contracts",
        ] + ctx.attr.contracts,
        inputs = [combined_json],
        outputs = outputs,
    )
    return [DefaultInfo(files = depset(outputs), runfiles = ctx.runfiles(files = outputs))]

sol_contract = rule(
    implementation = _sol_contract_impl,
    attrs = {
        "deps": attr.label_list(),
        "contracts": attr.string_list(mandatory = True, allow_empty = False),
        "optimize_runs": attr.int(default = 200),
        "include_path": attr.string(default = "src"),
        "solc_exe": attr.label(
            default = Label("//bazel_utils:solc-0.6.12"),
            allow_files = True,
            executable = True,
            # See https://bazel.build/rules/rules#configurations.
            cfg = "exec",
        ),
        "_solc_wrapper": attr.label(
            default = Label("//bazel_utils:solc_wrapper"),
            allow_files = True,
            executable = True,
            # See https://bazel.build/rules/rules#configurations.
            cfg = "exec",
        ),
        "extract_artifacts_exe": attr.label(
            default = Label("//bazel_utils:default_extract_artifacts_exe"),
            allow_files = True,
            executable = True,
            # See https://bazel.build/rules/rules#configurations.
            cfg = "exec",
        ),
    },
)
