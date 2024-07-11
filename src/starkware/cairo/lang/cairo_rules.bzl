CairoInfo = provider(fields = ["transitive_sources"])

def get_transitive_cairo_srcs(srcs, deps, hint_deps):
    """
    Returns the Cairo source files for a target and its transitive dependencies.
    """
    return depset(
        srcs,
        transitive = (
            [dep[CairoInfo].transitive_sources for dep in deps] +
            [dep[PyInfo].transitive_sources for dep in hint_deps]
        ),
    )

# Rule for a library of Cairo files (similar to py_library).

def _cairo_library_impl(ctx):
    trans_srcs = get_transitive_cairo_srcs(
        srcs = ctx.files.srcs,
        deps = ctx.attr.deps,
        hint_deps = ctx.attr.hint_deps,
    )
    return [
        CairoInfo(transitive_sources = trans_srcs),
        DefaultInfo(runfiles = ctx.runfiles(transitive_files = trans_srcs)),
    ]

cairo_library = rule(
    implementation = _cairo_library_impl,
    attrs = {
        "srcs": attr.label_list(allow_files = [".cairo"]),
        "deps": attr.label_list(providers = [CairoInfo]),
        "hint_deps": attr.label_list(providers = [PyInfo]),
    },
)

def _cairo_binary_impl(ctx):
    cairo_compile_exe = ctx.executable.cairo_compile_exe
    trans_srcs = get_transitive_cairo_srcs(
        srcs = ctx.files.srcs,
        deps = ctx.attr.deps,
        hint_deps = ctx.attr.hint_deps,
    )
    srcs_list = trans_srcs.to_list()
    py_srcs_list = [f for f in srcs_list if f.basename.endswith(".py")]

    out = ctx.outputs.compiled_program_name
    outs = [out]

    additional_args = []
    if ctx.outputs.abi != None:
        abi_out = ctx.outputs.abi
        outs.append(abi_out)
        additional_args += ["--abi", abi_out.path]

    ctx.actions.run(
        executable = cairo_compile_exe,
        arguments = [
            ctx.file.main.path,
            "--output",
            out.path,
            "--cairo_path",
            "src:external/cairo-lang/src",
        ] + additional_args + ctx.attr.cairoopts,
        inputs = srcs_list + [cairo_compile_exe],
        outputs = outs,
        progress_message = "Compiling %s..." % ctx.file.main.path,
    )
    return [DefaultInfo(runfiles = ctx.runfiles(transitive_files = depset(outs + py_srcs_list)))]

# Rule for compiling a Cairo program (similar to py_binary).

cairo_binary = rule(
    implementation = _cairo_binary_impl,
    attrs = {
        "srcs": attr.label_list(allow_files = True),
        "deps": attr.label_list(),
        "hint_deps": attr.label_list(providers = [PyInfo]),
        "cairo_compile_exe": attr.label(
            default = Label("//src/starkware/cairo/lang/compiler:cairo_compile_exe"),
            allow_files = True,
            executable = True,
            # See https://bazel.build/rules/rules#configurations.
            cfg = "exec",
        ),
        "cairoopts": attr.string_list(),
        "compiled_program_name": attr.output(mandatory = True),
        "main": attr.label(allow_single_file = True, mandatory = True),
        "abi": attr.output(),
    },
)
