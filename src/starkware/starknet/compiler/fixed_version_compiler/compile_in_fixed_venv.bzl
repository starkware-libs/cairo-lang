load("//src/starkware/cairo/lang:cairo_rules.bzl", "get_transitive_cairo_srcs")

def _cairo_compile_os_fixed_version_impl(ctx):
    script = ctx.executable.script
    trans_srcs = get_transitive_cairo_srcs(
        srcs = ctx.files.srcs,
        deps = ctx.attr.deps,
        hint_deps = ctx.attr.hint_deps,
    )
    output = ctx.outputs.compiled_program_name

    # Gather all input files: main input + required_sources
    srcs_list = trans_srcs.to_list()
    py_srcs_list = [f for f in srcs_list if f.basename.endswith(".py")]
    all_inputs = [ctx.file.main] + srcs_list
    outs = [output]

    args = [
        ctx.attr.cairo_lang_version,
        ctx.file.main.path,
        "--output",
        output.path,
    ] + ctx.attr.cairoopts

    ctx.actions.run(
        executable = script,
        arguments = args,
        inputs = all_inputs + [script],
        outputs = outs,
        mnemonic = "FixedCairoCompile",
        progress_message = "Compiling %s fixed cairo-lang version..." % ctx.file.main.path,
    )

    return [DefaultInfo(
        files = depset(outs),
        runfiles = ctx.runfiles(transitive_files = depset(outs + py_srcs_list)),
    )]

cairo_compile_os_fixed_version = rule(
    implementation = _cairo_compile_os_fixed_version_impl,
    attrs = {
        "script": attr.label(
            executable = True,
            cfg = "exec",
            default = Label("//src/starkware/starknet/compiler/fixed_version_compiler:fixed_cairo_compile"),
        ),
        "main": attr.label(
            allow_single_file = [".cairo"],
            mandatory = True,
        ),
        "srcs": attr.label_list(allow_files = True),
        "deps": attr.label_list(),
        "hint_deps": attr.label_list(providers = [PyInfo]),
        "compiled_program_name": attr.output(mandatory = True),
        "cairoopts": attr.string_list(),
        "cairo_lang_version": attr.string(mandatory = True),
    },
    executable = False,
)
