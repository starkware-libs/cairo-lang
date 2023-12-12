load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive", "http_file")
load("//bazel_utils:get_from_cairo_lang.bzl", "get_from_cairo_lang")
load("//src/starkware/cairo:vars_cairo_compiler.bzl", "CAIRO_COMPILER_ARCHIVE")

http_archive(
    name = "build_bazel_rules_nodejs",
    sha256 = "f10a3a12894fc3c9bf578ee5a5691769f6805c4be84359681a785a0c12e8d2b6",
    urls = [
        "https://github.com/bazelbuild/rules_nodejs/releases/download/5.5.3/rules_nodejs-5.5.3.tar.gz",
    ],
)

load("@build_bazel_rules_nodejs//:repositories.bzl", "build_bazel_rules_nodejs_dependencies")

build_bazel_rules_nodejs_dependencies()

load("@build_bazel_rules_nodejs//:index.bzl", "yarn_install")

yarn_install(
    name = "npm_ganache",
    package_json = "//:package.json",
    yarn_lock = "//:yarn_ganache.lock",
)

http_file(
    name = "solc-0.6.12",
    downloaded_file_path = "solc-0.6.12",
    executable = True,
    sha256 = "f6cb519b01dabc61cab4c184a3db11aa591d18151e362fcae850e42cffdfb09a",
    urls = [
        "https://binaries.soliditylang.org/linux-amd64/solc-linux-amd64-v0.6.12+commit.27d51765",
        "https://starkware-third-party.s3.us-east-2.amazonaws.com/ethereum/solc-0.6.12",
    ],
)

http_archive(
    name = "rules_python",
    patch_args = ["-p1"],
    patches = ["//bazel_utils/patches:rules_python.patch"],
    sha256 = "9d04041ac92a0985e344235f5d946f71ac543f1b1565f2cdbc9a2aaee8adf55b",
    strip_prefix = "rules_python-0.26.0",
    url = "https://github.com/bazelbuild/rules_python/releases/download/0.26.0/rules_python-0.26.0.tar.gz",
)

load("@rules_python//python:repositories.bzl", "py_repositories", "python_register_toolchains")

py_repositories()

http_archive(
    name = CAIRO_COMPILER_ARCHIVE,
    build_file = get_from_cairo_lang(
        "//src/starkware/starknet/compiler/v1:BUILD." + CAIRO_COMPILER_ARCHIVE,
    ),
    strip_prefix = "cairo",
    url = "https://github.com/starkware-libs/cairo/releases/download/v2.4.0/release-x86_64-unknown-linux-musl.tar.gz",
)

http_archive(
    name = "pypy3.9",
    build_file = "//:pypy3.9_archive_build_file.bzl",
    sha256 = "d506172ca11071274175d74e9c581c3166432d0179b036470e3b9e8d20eae581",
    strip_prefix = "pypy3.9-v7.3.11-linux64",
    url = "https://downloads.python.org/pypy/pypy3.9-v7.3.11-linux64.tar.bz2",
)

register_toolchains("//bazel_utils/python:py_stub_toolchain")

python_register_toolchains(
    name = "python3",
    python_version = "3.9",
    register_toolchains = False,
)

# Install python pip packages in a lazy way.
load("@python3//:defs.bzl", "interpreter")
load("@rules_python//python:pip.bzl", "pip_parse")

pip_parse(
    name = "cpython_reqs",
    extra_pip_args = [
        "--retries=100",
        "--timeout=3000",
    ],
    python_interpreter_target = interpreter,
    requirements_lock = "//scripts:requirements.txt",
)

load("@cpython_reqs//:requirements.bzl", "install_deps")

install_deps()

pip_parse(
    name = "pypy_reqs",
    extra_pip_args = [
        "--retries=100",
        "--timeout=3000",
    ],
    python_interpreter_target = "@pypy3.9//:bin/pypy3",
    requirements_lock = "//scripts:pypy-requirements.txt",
)

load("@pypy_reqs//:requirements.bzl", pypy_install_deps = "install_deps")

pypy_install_deps()
