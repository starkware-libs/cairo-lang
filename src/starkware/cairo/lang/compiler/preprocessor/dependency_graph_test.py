from typing import Dict

from starkware.cairo.lang.compiler.ast.module import CairoModule
from starkware.cairo.lang.compiler.parser import parse_file
from starkware.cairo.lang.compiler.preprocessor.dependency_graph import (
    DependencyGraphVisitor,
    get_main_functions_to_compile,
)
from starkware.cairo.lang.compiler.preprocessor.identifier_collector import IdentifierCollector
from starkware.cairo.lang.compiler.scoped_name import ScopedName

scope = ScopedName.from_string


def _extract_dependency_graph(codes: Dict[str, str]) -> DependencyGraphVisitor:
    """
    Extracts the dependencies from the given codes (given as a map from a file name to its content).
    Returns the DependencyGraphVisitor instance.
    """
    modules = [
        CairoModule(
            cairo_file=parse_file(code),
            module_name=ScopedName.from_string(name),
        )
        for name, code in codes.items()
    ]
    identifier_collector = IdentifierCollector()
    for module in modules:
        identifier_collector.visit(module)
    dependency_graph_visitor = DependencyGraphVisitor(identifiers=identifier_collector.identifiers)
    for module in modules:
        dependency_graph_visitor.visit(module)
    return dependency_graph_visitor


def test_dependency_graph():
    modules = {
        "module": """
func func0() -> (res: felt) {
    return (res=0);
}
func func1() {
    return ();
}
func func2() {
    return ();
}
func func3() {
    return ();
}
""",
        "__main__": """
from module import func1 as func1_alias

func foo() {
    struct S {
        x: S*,
        y: S*,
    }

    struct T {
        x: S*,
    }

    // Importing creates a dependency even if not used.
    from module import func0 as func0_alias, func2

    tempvar _tempvar = [ap];
    const _const = [ap];
    local _local = [ap];
    let _reference = [fp] + 2;

    _label:
    let _typed_reference: W = ns.myfunc(1, 2, 3);
}

namespace ns {
    func myfunc() {
        myfunc();
        func1_alias();
    }

    call bar;  // This line will be ignored since it's outside of any function.
}

struct W {
    x: felt,
}

func bar() {
    const a = foo.S.x + 1;
    jmp bar if foo.S.y * 2 != 0;
    let w: W* = 0;
    let w_x = w.x;
    foo.func0_alias();
}

func main() {
    jmp foo._label;
    call bar;
}

call bar;  // This line will be ignored since it's outside of any function.
""",
        "": """
from module import func2
""",
    }

    dependency_graph_visitor = _extract_dependency_graph(modules)
    dependencies = {
        str(scope): set(map(str, deps))
        for scope, deps in dependency_graph_visitor.visited_identifiers.items()
    }
    assert dependencies == {
        "__main__.foo": {
            "__main__.foo._tempvar",
            "__main__.foo._const",
            "__main__.foo._local",
            "__main__.foo._reference",
            "__main__.foo._label",
            "__main__.foo._typed_reference",
            "__main__.ns.myfunc",
            "module.func0",
            "module.func2",
        },
        "__main__.ns.myfunc": {
            "__main__.ns.myfunc",
            "module.func1",
        },
        "__main__.bar": {
            "__main__.bar",
            "__main__.bar.a",
            "__main__.bar.w",
            "__main__.bar.w_x",
            "__main__.foo.S",
            "module.func0",
        },
        "__main__.main": {
            "__main__.bar",
            "__main__.foo._label",
        },
        "module.func0": set(),
        "module.func1": set(),
        "module.func2": set(),
        "module.func3": set(),
    }

    assert dependency_graph_visitor.find_function_dependencies({scope("__main__.main")}) == {
        ScopedName(path=("__main__", "bar")),
        ScopedName(path=("__main__", "foo")),
        ScopedName(path=("__main__", "main")),
        ScopedName(path=("__main__", "ns", "myfunc")),
        ScopedName(path=("module", "func0")),
        ScopedName(path=("module", "func1")),
        ScopedName(path=("module", "func2")),
    }
    assert dependency_graph_visitor.find_function_dependencies({scope("__main__.ns.myfunc")}) == {
        ScopedName(path=("__main__", "ns", "myfunc")),
        ScopedName(path=("module", "func1")),
    }
    assert dependency_graph_visitor.find_function_dependencies(
        {scope("__main__.ns.myfunc"), scope("__main__.bar")}
    ) == {
        ScopedName(path=("__main__", "bar")),
        ScopedName(path=("__main__", "foo")),
        ScopedName(path=("__main__", "ns", "myfunc")),
        ScopedName(path=("module", "func0")),
        ScopedName(path=("module", "func1")),
        ScopedName(path=("module", "func2")),
    }
    assert dependency_graph_visitor.find_function_dependencies({scope("foo")}) == set()

    # Test get_main_functions_to_compile().

    assert get_main_functions_to_compile(
        identifiers=dependency_graph_visitor.identifiers, scopes_to_compile={scope("module")}
    ) == {
        scope("module.func0"),
        scope("module.func1"),
        scope("module.func2"),
        scope("module.func3"),
    }
    assert get_main_functions_to_compile(
        identifiers=dependency_graph_visitor.identifiers, scopes_to_compile={scope("__main__")}
    ) == {
        scope("module.func1"),
        scope("__main__.foo"),
        scope("__main__.ns"),
        scope("__main__.bar"),
        scope("__main__.main"),
    }
    assert get_main_functions_to_compile(
        identifiers=dependency_graph_visitor.identifiers, scopes_to_compile={scope("")}
    ) == {
        scope("module.func2"),
        scope("module"),
        scope("__main__"),
    }
