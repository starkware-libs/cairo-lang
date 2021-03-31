from typing import Dict, Set

from starkware.cairo.lang.compiler.ast.module import CairoModule
from starkware.cairo.lang.compiler.parser import parse_file
from starkware.cairo.lang.compiler.preprocessor.dependency_graph import DependencyGraphVisitor
from starkware.cairo.lang.compiler.preprocessor.identifier_collector import IdentifierCollector
from starkware.cairo.lang.compiler.scoped_name import ScopedName


def _extract_dependency_graph(codes: Dict[str, str]) -> Dict[str, Set[str]]:
    """
    Extracts the dependencies from the given codes (given as a map from a file name to its content).
    Returns the dependencies as a map from scope name to a set of the identifiers it uses.
    """
    modules = [
        CairoModule(
            cairo_file=parse_file(code),
            module_name=ScopedName.from_string(name),
        ) for name, code in codes.items()]
    identifier_collector = IdentifierCollector()
    for module in modules:
        identifier_collector.visit(module)
    dependency_graph_visitor = DependencyGraphVisitor(identifiers=identifier_collector.identifiers)
    for module in modules:
        dependency_graph_visitor.visit(module)
    return {
        str(scope): set(map(str, deps))
        for scope, deps in dependency_graph_visitor.visited_identifiers.items()}


def test_dependency_graph():
    modules = {'module': """
func func0():
    return ()
end
func func1():
    return ()
end
func func2():
    return ()
end
""", '__main__': """
from module import func1 as func1_alias

func foo():
    struct S:
        member x : S*
        member y : S*
    end

    struct T:
        member x : S*
    end

    # Importing creates a dependency even if not used.
    from module import func0 as func0_alias, func2

    tempvar _tempvar = [ap]
    const _const = [ap]
    local _local = [ap]
    let _reference = [fp] + 2

    _label:
    let _typed_reference : W = myfunc(1, 2, 3)
end

func myfunc():
    myfunc()
    func1_alias()
end

struct W:
    member x : felt
end

func bar():
    const a = foo.S.x + 1
    jmp bar if foo.S.y * 2 != 0
    let w : W* = 0
    let w_x = w.x
    foo.func0_alias()
end

func main():
    jmp foo._label
    call bar
end
"""}

    assert _extract_dependency_graph(modules) == {
        '__main__': {
            'module.func1',
        },
        '__main__.foo': {
            '__main__.foo._tempvar',
            '__main__.foo._const',
            '__main__.foo._local',
            '__main__.foo._reference',
            '__main__.foo._label',
            '__main__.foo._typed_reference',
            '__main__.myfunc',
            'module.func0',
            'module.func2',
        },
        '__main__.myfunc': {
            '__main__.myfunc',
            'module.func1',
        },
        '__main__.bar': {
            '__main__.bar',
            '__main__.bar.a',
            '__main__.bar.w',
            '__main__.bar.w_x',
            '__main__.foo.S',
            'module.func0',
        },
        '__main__.main': {
            '__main__.bar',
            '__main__.foo._label',
        },
    }
