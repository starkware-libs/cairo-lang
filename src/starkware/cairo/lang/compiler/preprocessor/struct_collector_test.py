from typing import Dict, Set

import pytest

from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt, TypePointer, TypeStruct
from starkware.cairo.lang.compiler.ast.module import CairoModule
from starkware.cairo.lang.compiler.identifier_definition import (
    AliasDefinition, FutureIdentifierDefinition, MemberDefinition, StructDefinition)
from starkware.cairo.lang.compiler.parser import parse_file
from starkware.cairo.lang.compiler.preprocessor.identifier_collector import IdentifierCollector
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.preprocessor.struct_collector import StructCollector
from starkware.cairo.lang.compiler.scoped_name import ScopedName


def _collect_struct_definitions(codes: Dict[str, str]) -> Dict[str, Set[str]]:
    """
    Collects the struct related identifiers from the given codes (given as a map from a file name to
    its content).

    Return the collected identifiers as a dict.
    """
    modules = [
        CairoModule(
            cairo_file=parse_file(code),
            module_name=ScopedName.from_string(name),
        ) for name, code in codes.items()]
    identifier_collector = IdentifierCollector()
    for module in modules:
        identifier_collector.visit(module)
    struct_collector = StructCollector(identifiers=identifier_collector.identifiers)
    for module in modules:
        struct_collector.visit(module)
    return {
        str(name): identifier_definition
        for name, identifier_definition in struct_collector.identifiers.as_dict().items()
        if not isinstance(identifier_definition, FutureIdentifierDefinition)}


def test_struct_collector():
    modules = {'module': """
struct S:
    member x : S*
    member y : S*
end
""", '__main__': """
from module import S

func foo{z}(a : S, b) -> (c : S):
    struct T:
        member x : S*
    end
    const X = 5
    return (c=a + X)
end
const Y = 1 + 1
"""}

    scope = ScopedName.from_string

    struct_defs = _collect_struct_definitions(modules)

    expected_def = {
        'module.S': StructDefinition(
            full_name=scope('module.S'),
            members={
                'x': MemberDefinition(offset=0, cairo_type=TypePointer(pointee=TypeStruct(
                    scope=scope('module.S'), is_fully_resolved=True))),
                'y': MemberDefinition(offset=1, cairo_type=TypePointer(pointee=TypeStruct(
                    scope=scope('module.S'), is_fully_resolved=True))),
            }, size=2),
        '__main__.S': AliasDefinition(destination=scope('module.S')),
        '__main__.foo.Args': StructDefinition(
            full_name=scope('__main__.foo.Args'),
            members={
                'a': MemberDefinition(offset=0, cairo_type=TypeStruct(
                    scope=scope('module.S'), is_fully_resolved=True)),
                'b': MemberDefinition(offset=2, cairo_type=TypeFelt()),
            }, size=3),
        '__main__.foo.ImplicitArgs': StructDefinition(
            full_name=scope('__main__.foo.ImplicitArgs'),
            members={'z': MemberDefinition(offset=0, cairo_type=TypeFelt())}, size=1),
        '__main__.foo.Return': StructDefinition(
            full_name=scope('__main__.foo.Return'),
            members={
                'c': MemberDefinition(offset=0, cairo_type=TypeStruct(
                    scope=scope('module.S'), is_fully_resolved=True))
            }, size=2),
        '__main__.foo.T': StructDefinition(
            full_name=scope('__main__.foo.T'),
            members={
                'x': MemberDefinition(offset=0, cairo_type=TypePointer(pointee=TypeStruct(
                    scope=scope('module.S'), is_fully_resolved=True))),
            }, size=1)
    }

    assert struct_defs == expected_def


def test_struct_collector_failure():
    modules = {'module': """
struct S:
    member x : S*
    member x : S*
end
"""}

    with pytest.raises(PreprocessorError, match="Redefinition of 'module.S.x'."):
        _collect_struct_definitions(modules)

    modules = {'module': """
struct S:
    member local a
end
"""}
    with pytest.raises(PreprocessorError, match="Unexpected modifier 'local'."):
        _collect_struct_definitions(modules)

    modules = {'module': """
struct S:
    return()
end
"""}
    with pytest.raises(PreprocessorError, match='Unexpected statement inside a struct definition.'):
        _collect_struct_definitions(modules)
