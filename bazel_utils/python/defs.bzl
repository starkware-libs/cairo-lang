load("@rules_python//python:defs.bzl", "py_binary", "py_library", "py_test")

_PythonVersionInfo = provider(fields = ["interpreter"])

def _python_version_info_impl(ctx):
    return [_PythonVersionInfo(interpreter = ctx.build_setting_value)]

python_version_info = rule(
    implementation = _python_version_info_impl,
    build_setting = config.string(flag = True),
)

def _set_python_version_impl(settings, attr):
    return {"//bazel_utils/python:python_version": attr.python_version}

_set_python_version = transition(
    implementation = _set_python_version_impl,
    inputs = [],
    outputs = ["//bazel_utils/python:python_version"],
)

def _python_version_deps_impl(ctx):
    library = ctx.attr.library[0]
    return [
        DefaultInfo(
            files = library[DefaultInfo].files,
            runfiles = library[DefaultInfo].default_runfiles,
        ),
        library[PyInfo],
        library[OutputGroupInfo],
    ]

_python_version_deps = rule(
    implementation = _python_version_deps_impl,
    attrs = {
        "python_version": attr.string(),
        "library": attr.label(cfg = _set_python_version, providers = [PyInfo]),
        "_allowlist_function_transition": attr.label(
            default = "@bazel_tools//tools/allowlists/function_transition_allowlist",
        ),
    },
)

def unify_requirements(repo_to_requirements):
    requirements = depset(
        transitive = [
            depset([req[len("@" + repo + "_"):-len("//:pkg")] for req in requirements])
            for repo, requirements in repo_to_requirements.items()
        ],
    )
    return requirements.to_list()

def requirement(name):
    return "//src/third_party/pip:" + name

def _pypy_rule(py_rule, name, main = None, srcs = [], data = [], deps = [], **kwargs):
    py_library(
        name = "_" + name + "_deps",
        data = data,
        deps = deps,
    )
    _python_version_deps(
        name = "_pypy_" + name,
        python_version = "pypy",
        library = ":_" + name + "_deps",
    )
    new_main = name + "_uses_pypy_.py"

    # Copying the main file to another path might cause bugs in executables that rely on the path
    #   of the main file and are located in a different directory from where they are defined.
    #   This will never happen for rules defined by py_exe and pytest_test.
    native.genrule(
        name = "generate_" + new_main,
        outs = [new_main],
        srcs = [main or (name + ".py")],
        cmd = "cp $(SRCS) $(OUTS)",
    )
    py_rule(
        name = name,
        main = new_main,
        data = [
            "@pypy3.9//:files",
            "@pypy3.9//:python3",
        ],
        srcs = srcs + [new_main],
        deps = [":_pypy_" + name],
        **kwargs
    )

def _cpython_rule(py_rule, name, data = [], deps = [], **kwargs):
    py_library(
        name = "_" + name + "_deps",
        data = data,
        deps = deps,
    )
    _python_version_deps(
        name = "_cpython_" + name,
        python_version = "cpython",
        library = ":_" + name + "_deps",
    )
    py_rule(
        name = name,
        deps = [":_cpython_" + name],
        **kwargs
    )

def pypy_binary(name, **kwargs):
    _pypy_rule(py_binary, name = name, **kwargs)

def pypy_test(name, **kwargs):
    _pypy_rule(py_test, name = name, **kwargs)

def cpython_binary(name, **kwargs):
    _cpython_rule(py_binary, name = name, **kwargs)

def cpython_test(name, **kwargs):
    _cpython_rule(py_test, name = name, **kwargs)
