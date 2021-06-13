from starkware.cairo.lang.compiler.identifier_definition import (
    AliasDefinition, ConstDefinition, FunctionDefinition, LabelDefinition, ReferenceDefinition,
    StructDefinition)
from starkware.cairo.lang.compiler.parser import parse_file
from starkware.cairo.lang.compiler.preprocessor.identifier_collector import IdentifierCollector
from starkware.cairo.lang.compiler.preprocessor.preprocessor_test_utils import verify_exception
from starkware.cairo.lang.compiler.scoped_name import ScopedName


def _extract_identifiers(code):
    """
    Extracts the identifiers defined in the code block and returns them as strings.
    """
    ast = parse_file(code)
    collector = IdentifierCollector()
    with collector.scoped(ScopedName(), parent=ast):
        collector.visit(ast.code_block)
    return [
        (str(name), identifier_definition.identifier_type)
        for name, identifier_definition in collector.identifiers.as_dict().items()]


def test_collect_single_binds():
    code = """
tempvar a = [ap]
const b = [ap]
local c = [ap]
let d = [fp] + 2
f:
let g : H = f(1, 2, 3)
"""
    assert set(_extract_identifiers(code)) == {
        ('a', ReferenceDefinition),
        ('b', ConstDefinition),
        ('c', ReferenceDefinition),
        ('d', ReferenceDefinition),
        ('f', LabelDefinition),
        ('g', ReferenceDefinition),
    }


def test_collect_multi_binds():
    code = """
func a(b, c) -> (d):
    [ap] = [ap]
end
let (e, f) = g()
"""
    assert set(_extract_identifiers(code)) == {
        ('a', FunctionDefinition),
        ('a.SIZEOF_LOCALS', ConstDefinition),
        ('a.Args', StructDefinition),
        ('a.ImplicitArgs', StructDefinition),
        ('a.Return', StructDefinition),
        ('a.b', ReferenceDefinition),
        ('a.c', ReferenceDefinition),
        ('e', ReferenceDefinition),
        ('f', ReferenceDefinition),
    }


def test_nested_funcs():
    code = """
func foo{z}(x):
    local a
    func bar(y):
        tempvar b = [ap]
    end
end
"""
    assert set(_extract_identifiers(code)) == {
        ('foo', FunctionDefinition),
        ('foo.SIZEOF_LOCALS', ConstDefinition),
        ('foo.Args', StructDefinition),
        ('foo.ImplicitArgs', StructDefinition),
        ('foo.Return', StructDefinition),
        ('foo.x', ReferenceDefinition),
        ('foo.z', ReferenceDefinition),
        ('foo.a', ReferenceDefinition),
        ('foo.bar', FunctionDefinition),
        ('foo.bar.SIZEOF_LOCALS', ConstDefinition),
        ('foo.bar.Args', StructDefinition),
        ('foo.bar.ImplicitArgs', StructDefinition),
        ('foo.bar.Return', StructDefinition),
        ('foo.bar.y', ReferenceDefinition),
        ('foo.bar.b', ReferenceDefinition),
    }


def test_redefinition():
    code = """
tempvar name = [ap]
local name = [ap]
"""
    assert _extract_identifiers(code) == [
        ('name', ReferenceDefinition),
    ]


def test_redefinition_failures():
    verify_exception("""
name:
local name = [ap]
""", """
file:?:?: Redefinition of 'test_scope.name'.
local name = [ap]
      ^**^
""")


def test_imports():
    collector = IdentifierCollector()
    collector.identifiers.add_identifier(
        ScopedName.from_string('foo.bar'), ConstDefinition(value=0))
    ast = parse_file("""
from foo import bar as bar0
""")
    with collector.scoped(ScopedName(), parent=ast):
        collector.visit(ast.code_block)

    assert collector.identifiers.get_scope(ScopedName()).identifiers == {
        'bar0': AliasDefinition(destination=ScopedName.from_string('foo.bar')),
    }
