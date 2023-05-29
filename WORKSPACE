load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive", "http_file")
load("//bazel_utils:get_from_cairo_lang.bzl", "get_from_cairo_lang")

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
    sha256 = "a3a6e99f497be089f81ec082882e40246bfd435f52f4e82f37e89449b04573f6",
    strip_prefix = "rules_python-0.10.2",
    url = "https://github.com/bazelbuild/rules_python/archive/refs/tags/0.10.2.tar.gz",
)

http_archive(
    name = "cairo-compiler-archive-1.1.0",
    build_file = get_from_cairo_lang(
        "//src/starkware/starknet/compiler/v1:BUILD.cairo-compiler-archive-1.1.0",
    ),
    strip_prefix = "cairo",
    url = "https://github.com/starkware-libs/cairo/releases/download/v1.1.0/release-x86_64-unknown-linux-musl.tar.gz",
)

http_archive(
    name = "pypy3.9",
    build_file = "//:pypy3.9_archive_build_file.bzl",
    sha256 = "d506172ca11071274175d74e9c581c3166432d0179b036470e3b9e8d20eae581",
    strip_prefix = "pypy3.9-v7.3.11-linux64",
    url = "https://downloads.python.org/pypy/pypy3.9-v7.3.11-linux64.tar.bz2",
)

register_toolchains("//bazel_utils/python:py_stub_toolchain")

load("@rules_python//python:repositories.bzl", "python_register_toolchains")

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
    python_interpreter_target = interpreter,
    requirements_lock = "//scripts:requirements.txt",
)

load("@cpython_reqs//:requirements.bzl", "install_deps")

install_deps()

pip_parse(
    name = "pypy_reqs",
    python_interpreter_target = "@pypy3.9//:bin/pypy3",
    requirements_lock = "//scripts:pypy-requirements.txt",
)

load("@pypy_reqs//:requirements.bzl", pypy_install_deps = "install_deps")

pypy_install_deps()
