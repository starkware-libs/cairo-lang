"""
Compiles a Cairo 1.0 Starknet contract to Sierra, and then to CASM.

Both exe can be replaced if needed.
Arguments can be passed to the compiler by using `cairoopts`.

Args:
    main: The Cairo file to compile.
    compiled_sierra_name: optional, the json file name to write the Sierra output to.
    compiled_casm_name: optional, the json file name to write the CASM output to.
    **kwargs: contains at least- compile_cairo_to_sierra_exe, compile_sierra_to_casm_exe, cairoopts.
"""

load("//src/starkware/cairo/lang:cairo_rules.bzl", "CairoInfo")
load("//src/starkware/cairo:vars.bzl", "CAIRO_COMPILER_ARCHIVE")

def get_transitive_cairo_srcs(srcs, deps):
    """
    Returns the Cairo source files for a target and its transitive dependencies.
    """
    return depset(srcs, transitive = [dep[CairoInfo].transitive_sources for dep in deps])

def _starknet_contract_impl(ctx):
    compiled_sierra_name = ctx.outputs.compiled_sierra_name
    compiled_casm_name = ctx.outputs.compiled_casm_name
    if compiled_sierra_name == None and compiled_casm_name == None:
        fail(msg = "At least one output file must be declared, either Sierra or Casm.")

    compile_cairo_to_sierra_exe = ctx.executable.compile_cairo_to_sierra_exe
    compile_sierra_to_casm_exe = ctx.executable.compile_sierra_to_casm_exe

    trans_srcs = get_transitive_cairo_srcs(srcs = ctx.files.srcs, deps = ctx.attr.deps)
    srcs_list = trans_srcs.to_list()
    if ctx.file.cairo_project_file != None:
        srcs_list.append(ctx.file.cairo_project_file)

    if compiled_sierra_name == None:
        compiled_sierra_name = ctx.actions.declare_file(ctx.label.name + ".sierra.json")
        outs = []
    else:
        outs = [compiled_sierra_name]

    _compile_internal(
        ctx = ctx,
        srcs_list = srcs_list,
        main = ctx.file.main,
        compiled_file_name = compiled_sierra_name,
        compile_exe = compile_cairo_to_sierra_exe,
        outs = [compiled_sierra_name],
        cairoopts = ctx.attr.cairoopts,
        progress_message = "Compiling cairo to sierra %s..." % ctx.file.main.path,
    )

    if compiled_casm_name != None:
        _compile_internal(
            ctx = ctx,
            srcs_list = [compiled_sierra_name],
            main = compiled_sierra_name,
            compiled_file_name = compiled_casm_name,
            compile_exe = compile_sierra_to_casm_exe,
            outs = [compiled_casm_name],
            cairoopts = ctx.attr.cairoopts + ["--add-pythonic-hints"],
            progress_message = "Compiling sierra to casm %s..." % ctx.file.main.path,
        )
        outs.append(compiled_casm_name)

    return [DefaultInfo(files = depset(outs))]

def _compile_internal(
        ctx,
        srcs_list,
        main,
        compiled_file_name,
        compile_exe,
        outs,
        cairoopts,
        progress_message):
    ctx.actions.run(
        executable = compile_exe,
        # https://github.com/starkware-libs/cairo/blob/main/crates/cairo-lang-runner/README.md
        # Arguments order:
        # File to compile.
        # Output file.
        arguments = [
            main.path,
            compiled_file_name.path,
        ] + cairoopts,
        inputs = srcs_list + [compile_exe] + ctx.files.compiler_data,
        outputs = outs,
        progress_message = progress_message,
    )

starknet_contract = rule(
    implementation = _starknet_contract_impl,
    attrs = {
        "srcs": attr.label_list(allow_files = [".cairo"]),
        "deps": attr.label_list(providers = [CairoInfo]),
        "compiler_data": attr.label_list(
            allow_files = True,
            default = ["@" + CAIRO_COMPILER_ARCHIVE],
        ),
        "compile_cairo_to_sierra_exe": attr.label(
            default = Label("@" + CAIRO_COMPILER_ARCHIVE + "//:bin/starknet-compile"),
            allow_files = True,
            executable = True,
            # See https://bazel.build/rules/rules#configurations.
            cfg = "exec",
        ),
        "compile_sierra_to_casm_exe": attr.label(
            default = Label("@" + CAIRO_COMPILER_ARCHIVE + "//:bin/starknet-sierra-compile"),
            allow_files = True,
            executable = True,
            # See https://bazel.build/rules/rules#configurations.
            cfg = "exec",
        ),
        "compiled_sierra_name": attr.output(),
        "compiled_casm_name": attr.output(),
        "cairoopts": attr.string_list(default = []),
        "main": attr.label(allow_single_file = True, mandatory = True),
        "cairo_project_file": attr.label(allow_single_file = True),
    },
)
