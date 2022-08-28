import copy
import dataclasses
from typing import Dict, List, Type

import pytest

from starkware.cairo.lang.compiler.ast.code_elements import CodeElement, CodeElementScoped
from starkware.cairo.lang.compiler.identifier_definition import (
    FutureIdentifierDefinition,
    StructDefinition,
    TypeDefinition,
)
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.parser import parse_block
from starkware.cairo.lang.compiler.preprocessor.identifier_collector import IdentifierCollector
from starkware.cairo.lang.compiler.preprocessor.memento import (
    AppendOnlyListMemento,
    ByValueMemento,
    ChainMapMemento,
    MembersMemento,
    Memento,
)
from starkware.cairo.lang.compiler.preprocessor.preprocessor import (
    Preprocessor,
    PreprocessorMemento,
)
from starkware.cairo.lang.compiler.preprocessor.preprocessor_test_utils import PRIME
from starkware.cairo.lang.compiler.preprocessor.struct_collector import StructCollector
from starkware.cairo.lang.compiler.scoped_name import ScopedName


@dataclasses.dataclass
class DummyClass:
    a: int

    def increase(self):
        self.a += 1


class DummyMemento(MembersMemento[DummyClass]):
    @classmethod
    def get_fields(cls) -> Dict[str, Type[Memento]]:
        return dict(
            a=ByValueMemento[int],
        )


@pytest.mark.parametrize(
    "memento_cls,prev,op,new,inplace",
    [
        (AppendOnlyListMemento, [1, 2], lambda v: v.extend([3, 4]), [1, 2, 3, 4], True),
        (ChainMapMemento, {1: 2}, lambda v: v.update({3: 4}), {1: 2, 3: 4}, True),
        (DummyMemento, DummyClass(1), DummyClass.increase, DummyClass(2), True),
        (ByValueMemento, 1, None, 2, False),
    ],
)
def test_mementos(memento_cls, prev, op, new, inplace):
    value = copy.deepcopy(prev)
    original_instance = value
    checkpoint, value = memento_cls.from_object(value)

    if inplace:
        op(value)
    else:
        value = new

    value = checkpoint.restore(value)
    if inplace:
        assert value is original_instance
    assert value == prev

    value = copy.deepcopy(prev)
    checkpoint, value = memento_cls.from_object(value)

    if inplace:
        op(value)
    else:
        value = new

    value = checkpoint.apply(value)
    assert value == new


def block_code_to_elements(code: str) -> List[CodeElement]:
    return [elm.code_elm for elm in parse_block(code).code_elements]


def codes_to_scoped_element(codes: List[str]) -> CodeElementScoped:
    return CodeElementScoped(
        scope=ScopedName.from_string("main"),
        code_elements=sum((block_code_to_elements(code) for code in codes), []),
    )


def get_identifiers(codes: List[str]) -> IdentifierManager:
    elm = codes_to_scoped_element(codes)

    identifiers = IdentifierManager()
    identifier_collector = IdentifierCollector(identifiers=identifiers)
    identifier_collector.visit(elm)

    struct_collector = StructCollector(identifiers=identifiers)
    struct_collector.visit(elm)
    return identifiers


def preprocessor_from_codes(codes: List[str]) -> Preprocessor:
    preprocessor = Preprocessor(prime=PRIME, identifiers=get_identifiers(codes), builtins=[])
    elm = codes_to_scoped_element(codes)
    preprocessor.visit(elm)
    return preprocessor


def check_preprocessor_equivalence(proc0: Preprocessor, proc1: Preprocessor):
    assert proc0.instructions == proc1.instructions
    assert proc0.current_pc == proc1.current_pc
    assert proc0.flow_tracking.data == proc1.flow_tracking.data
    assert proc0.next_temp_id == proc1.next_temp_id
    assert proc0.attributes == proc1.attributes

    def strip_identifiers(identifiers: IdentifierManager):
        """
        Strips away identifiers that were computed in previous passes.
        """
        return {
            name: identifier_def
            for name, identifier_def in identifiers.as_dict().items()
            if not isinstance(
                identifier_def, (FutureIdentifierDefinition, StructDefinition, TypeDefinition)
            )
        }

    assert strip_identifiers(proc0.identifiers) == strip_identifiers(proc1.identifiers)


def test_preprocessor_checkpoint():
    code0 = """\
struct A {
    a: felt,
}
func foo0(a: A) -> (res: felt) {
    return (res=1);
}
"""
    code1 = """\
struct B {
    b: felt,
}
func foo1(b: B) -> (res: felt) {
    with_attr attr {
        return (res=2);
    }
}
"""
    code2 = """\
struct C {
    c: felt,
}
func foo2(c: C) -> (res: felt) {
    return (res=3);
}
"""

    identifiers = get_identifiers([code0, code1, code2])
    preprocessor = Preprocessor(prime=PRIME, identifiers=identifiers, builtins=[])
    with preprocessor.scoped(ScopedName(("main",)), parent=None):
        preprocessor.visit(parse_block(code0))
        check_preprocessor_equivalence(preprocessor, preprocessor_from_codes([code0]))

        checkpoint, preprocessor = PreprocessorMemento.from_object(preprocessor)
        preprocessor.visit(parse_block(code1))
        check_preprocessor_equivalence(preprocessor, preprocessor_from_codes([code0, code1]))

        preprocessor = checkpoint.restore(preprocessor)
        check_preprocessor_equivalence(preprocessor, preprocessor_from_codes([code0]))

        checkpoint, preprocessor = PreprocessorMemento.from_object(preprocessor)
        preprocessor.visit(parse_block(code2))
        check_preprocessor_equivalence(preprocessor, preprocessor_from_codes([code0, code2]))

        preprocessor = checkpoint.apply(preprocessor)
        check_preprocessor_equivalence(preprocessor, preprocessor_from_codes([code0, code2]))
