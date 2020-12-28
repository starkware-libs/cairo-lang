from starkware.cairo.lang.compiler.identifier_definition import (
    AliasDefinition, ConstDefinition, LabelDefinition, MemberDefinition, ReferenceDefinition)
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
    with collector.scoped(ScopedName()):
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
member e = 6
f:
let g : H = f(1, 2, 3)
"""
    assert set(_extract_identifiers(code)) == {
        ('a', ReferenceDefinition),
        ('b', ConstDefinition),
        ('c', ReferenceDefinition),
        ('d', ReferenceDefinition),
        ('e', MemberDefinition),
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
        ('a', LabelDefinition),
        ('a.SIZEOF_LOCALS', ConstDefinition),
        ('a.Args.b', MemberDefinition),
        ('a.b', ReferenceDefinition),
        ('a.Args.c', MemberDefinition),
        ('a.c', ReferenceDefinition),
        ('a.Return.d', MemberDefinition),
        ('a.Args.SIZE', ConstDefinition),
        ('a.Return.SIZE', ConstDefinition),
        ('e', ReferenceDefinition),
        ('f', ReferenceDefinition),
    }


def test_nested_funcs():
    code = """
func foo(x):
    local a
    func bar(y):
        tempvar b = [ap]
    end
end
"""
    assert set(_extract_identifiers(code)) == {
        ('foo', LabelDefinition),
        ('foo.SIZEOF_LOCALS', ConstDefinition),
        ('foo.Args.SIZE', ConstDefinition),
        ('foo.Return.SIZE', ConstDefinition),
        ('foo.Args.x', MemberDefinition),
        ('foo.x', ReferenceDefinition),
        ('foo.a', ReferenceDefinition),
        ('foo.bar', LabelDefinition),
        ('foo.bar.SIZEOF_LOCALS', ConstDefinition),
        ('foo.bar.Args.SIZE', ConstDefinition),
        ('foo.bar.Return.SIZE', ConstDefinition),
        ('foo.bar.Args.y', MemberDefinition),
        ('foo.bar.y', ReferenceDefinition),
        ('foo.bar.b', ReferenceDefinition),
        ('foo.bar.Args.SIZE', ConstDefinition),
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
file:?:?: Redefinition of 'name'.
local name = [ap]
      ^**^
""")


def test_imports():
    collector = IdentifierCollector()
    collector.identifiers.add_identifier(
        ScopedName.from_string('foo.bar'), ConstDefinition(value=0))
    with collector.scoped(ScopedName()):
        collector.visit(parse_file("""
from foo import bar as bar0
""").code_block)

    assert collector.identifiers.get_scope(ScopedName()).identifiers == {
        'bar0': AliasDefinition(destination=ScopedName.from_string('foo.bar')),
    }
