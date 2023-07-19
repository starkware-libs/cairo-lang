"""Python related macros and rules."""

load(
    "//bazel_utils/python:defs.bzl",
    "cpython_binary",
    "cpython_test",
    "pypy_binary",
    "pypy_test",
    "requirement",
)

IPYTHON_EXE_SUFFIX = "_ipython"

def pytest_test(
        name,
        srcs,
        deps = [],
        args = [],
        data = [],
        code_coverage = True,
        is_pypy = False,
        legacy_create_init = False,
        **kwargs):
    """
        Calls pytest.
    """

    # Set the test timeout to 'eternal' if it isn't already set.
    timeout = kwargs.pop("timeout", "eternal")

    test_and_debug_targets(
        name = name,
        srcs = [
            "//bazel_utils:pytest_wrapper.py",
        ] + srcs,
        main = "//bazel_utils:pytest_wrapper.py",
        # Args passed to the tests using parser.addoption() need to be sent after the tested
        #   files so pytest recognizes them.
        args = [
            "$(location :%s)" % x
            for x in srcs
        ] + ["--color=yes", "--junitxml=$$XML_OUTPUT_FILE", "--strict-markers"] + args,
        python_version = "PY3",
        srcs_version = "PY3",
        deps = deps + [requirement("pytest"), "//:starkware"],
        data = data,
        timeout = timeout,
        legacy_create_init = legacy_create_init,
        is_pypy = is_pypy,
        **kwargs
    )

def test_and_debug_targets(name, srcs, timeout, is_pypy, **kwargs):
    """
    Creates both a test target and a binary target with the same content, for debugging purposes.
    """
    (pypy_test if is_pypy else cpython_test)(
        name = name,
        srcs = srcs,
        timeout = timeout,
        **kwargs
    )

    (pypy_binary if is_pypy else cpython_binary)(
        name = name + "-debug",
        srcs = srcs,
        **kwargs
    )

def _py_wrappers_impl(ctx):
    ctx.actions.run(
        outputs = [ctx.outputs.py_wrapper, ctx.outputs.sh_wrapper],
        executable = ctx.executable._gen_python_exe,
        arguments = [
            "--py_binary_path",
            "%s/%s/%s" % (
                ctx.label.workspace_name or ctx.workspace_name,
                ctx.label.package,
                ctx.attr.py_binary_name,
            ),
            "--output_py",
            ctx.outputs.py_wrapper.path,
            "--output_sh",
            ctx.outputs.sh_wrapper.path,
            "--name",
            ctx.attr.py_exe_name,
            "--module",
            ctx.attr.module,
        ],
    )

_py_wrappers = rule(
    implementation = _py_wrappers_impl,
    attrs = {
        "py_wrapper": attr.output(),
        "sh_wrapper": attr.output(),
        "py_binary_name": attr.string(),
        "_gen_python_exe": attr.label(
            cfg = "exec",
            default = "//bazel_utils:gen_python_exe",
            executable = True,
        ),
        "py_exe_name": attr.string(),
        "module": attr.string(),
    },
)

def py_exe(
        name,
        module,
        deps = [],
        additional_srcs = [],
        args = [],
        data = [],
        env = {},
        is_pypy = False,
        legacy_create_init = False,
        **kwargs):
    py_exe_module = name + "_exe.py"
    sh_file = name + "_exe.sh"
    py_binary_name = name + "_py_binary"

    _py_wrappers(
        name = name + "_wrappers",
        py_exe_name = name,
        module = module,
        py_binary_name = py_binary_name,
        py_wrapper = py_exe_module,
        sh_wrapper = sh_file,
    )

    (pypy_binary if is_pypy else cpython_binary)(
        name = py_binary_name,
        srcs = [
            py_exe_module,
        ] + additional_srcs,
        main = py_exe_module,
        python_version = "PY3",
        srcs_version = "PY3",
        deps = deps + ["//:starkware"],
        data = data,
        legacy_create_init = legacy_create_init,
        **kwargs
    )

    native.sh_binary(
        name = name,
        srcs = [sh_file],
        data = [
            py_binary_name,
            "@bazel_tools//tools/bash/runfiles",
        ],
        args = args,
        env = env,
    )
