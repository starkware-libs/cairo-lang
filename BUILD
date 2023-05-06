load("vars.bzl", "ADDITIONAL_IMPORTS")

exports_files([
    ".clang-format",
    "package.json",
    "yarn_ganache.lock",
] + glob(["*.py"]))

# The 'starkware' library adds 'src' to PYTHONPATH.
# The library on its own does not add any dependencies.
# This library is needed to allow us to use "import starkware.foo" instead of
# "import src.starkware.foo".
py_library(
    name = "starkware",
    srcs = [],
    imports = [
        "src",
    ] + ADDITIONAL_IMPORTS,
    visibility = ["//visibility:public"],
)
