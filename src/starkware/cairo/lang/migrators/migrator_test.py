from typing import Iterable, Optional

from starkware.cairo.lang.migrators.migrator import parse_and_migrate


def run_migrator_test(
    input: str,
    expected_output: str,
    migrate_syntax: bool = True,
    single_return_functions: Optional[Iterable[str]] = None,
):
    filename = "<input>"
    ast = parse_and_migrate(
        input,
        filename,
        migrate_syntax=migrate_syntax,
        single_return_functions=single_return_functions,
    )
    assert ast.format() == expected_output


def test_return_type_migration():
    run_migrator_test(
        input="""\
func test{x}(y) -> (a, b : felt*, c):
    foo(4, 5)
    if a == c and 1 == 2:
        [ap] = 0; ap++
    end
    ret
end
""",
        expected_output="""\
func test{x}(y) -> (a: felt, b: felt*, c: felt) {
    foo(4, 5);
    if (a == c and 1 == 2) {
        [ap] = 0, ap++;
    }
    ret;
}
""",
    )

    run_migrator_test(
        input="""\
func test(y):
    ret
end
""",
        expected_output="""\
func test(y) {
    ret;
}
""",
    )

    run_migrator_test(
        input="""\
func test{y}() -> ():
    ret
end
""",
        expected_output="""\
func test{y}() -> () {
    ret;
}
""",
    )


def test_struct_migration():
    run_migrator_test(
        input="""\
struct A:
    member x : felt  # Comment
end
""",
        expected_output="""\
struct A {
    x: felt,  // Comment
}
""",
    )


def test_namespace_migration():
    run_migrator_test(
        input="""\
namespace A:
    const x = 0
end
""",
        expected_output="""\
namespace A {
    const x = 0;
}
""",
    )


def test_return_expr_migration():
    run_migrator_test(
        input="""
func test():
    return (res=1)
    return (5)
    return (x=1, y=2)
    # Test partially named return statement.
    # Note that the migrated line will not compile, and the developer will have to manually fix it.
    return (1, x=2)

    # Test that tail calls can be parsed.
    return test()
end
""",
        expected_output="""\
func test() {
    return (res=1);
    return (5,);
    return (x=1, y=2);
    // Test partially named return statement.
    // Note that the migrated line will not compile, and the developer will have to manually fix it.
    return (1, x=2);

    // Test that tail calls can be parsed.
    return test();
}
""",
    )


def test_single_return_functions():
    before = """
from a import is_nn
from a import abs_value as abs_value2
namespace A:
    func test() -> (x):
        let (res) = foo(x)
        return abs_value(res)
        let (res) = is_nn(x)
        return abs_value2(res)
    end
end
"""
    after_only_syntax = """\
from a import is_nn
from a import abs_value as abs_value2
namespace A {
    func test() -> (x: felt) {
        let (res) = foo(x);
        return abs_value(res);
        let (res) = is_nn(x);
        return abs_value2(res);
    }
}
"""
    after = """\
from a import is_nn
from a import abs_value as abs_value2
namespace A {
    func test() -> (x: felt) {
        let (res) = foo(x);
        return abs_value(res);
        let res = is_nn(x);
        return (abs_value2(res),);
    }
}
"""
    single_return_functions = ["a.is_nn", "a.abs_value"]
    run_migrator_test(before, after_only_syntax, migrate_syntax=True, single_return_functions=None)
    run_migrator_test(
        after_only_syntax,
        after,
        migrate_syntax=False,
        single_return_functions=single_return_functions,
    )
    run_migrator_test(
        before, after, migrate_syntax=True, single_return_functions=single_return_functions
    )
