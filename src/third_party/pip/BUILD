load("@cpython_reqs//:requirements.bzl", "all_requirements")
load("@pypy_reqs//:requirements.bzl", pypy_all_requirements = "all_requirements")
load("//bazel_utils/python:defs.bzl", "unify_requirements")

[
    alias(
        name = requirement,
        actual = select({
            "//bazel_utils/python:pypy": "@pypy_reqs_" + requirement + "//:pkg",
            "//conditions:default": "@cpython_reqs_" + requirement + "//:pkg",
        }),
        visibility = ["//visibility:public"],
    )
    for requirement in unify_requirements({
        "cpython_reqs": all_requirements,
        "pypy_reqs": pypy_all_requirements,
    })
    if requirement != "greenlet"
]
