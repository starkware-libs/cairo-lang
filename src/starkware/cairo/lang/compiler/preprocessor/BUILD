load("//bazel_utils:python.bzl", "pytest_test")

package(default_visibility = ["//visibility:public"])

exports_files(glob(["*.py"]))

pytest_test(
    name = "cairo_compile_preprocessor_test",
    srcs = [
        "compound_expressions_test.py",
        "conftest.py",
        "dependency_graph_test.py",
        "flow_test.py",
        "identifier_aware_visitor_test.py",
        "identifier_collector_test.py",
        "if_labels_test.py",
        "local_variables_test.py",
        "memento_test.py",
        "preprocessor_test.py",
        "reg_tracking_test.py",
        "struct_collector_test.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//src/starkware/cairo/lang:cairo_constants_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_lib",
        "//src/starkware/cairo/lang/compiler:cairo_compile_test_utils_lib",
    ],
)
