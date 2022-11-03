import re
from typing import ClassVar, MutableMapping, Optional

import pytest

from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt, TypePointer, TypeStruct
from starkware.cairo.lang.compiler.expression_evaluator import ExpressionEvaluator
from starkware.cairo.lang.compiler.identifier_definition import (
    AliasDefinition,
    ConstDefinition,
    IdentifierDefinition,
    LabelDefinition,
    MemberDefinition,
    NamespaceDefinition,
    ReferenceDefinition,
    StructDefinition,
)
from starkware.cairo.lang.compiler.identifier_manager import (
    IdentifierError,
    IdentifierManager,
    MissingIdentifierError,
)
from starkware.cairo.lang.compiler.parser import parse_expr
from starkware.cairo.lang.compiler.preprocessor.flow import FlowTrackingDataActual, ReferenceManager
from starkware.cairo.lang.compiler.preprocessor.reg_tracking import RegTrackingData
from starkware.cairo.lang.compiler.references import FlowTrackingError, Reference
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.type_system import mark_types_in_expr_resolved
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, MaybeRelocatableDict
from starkware.cairo.lang.vm.vm_consts import VmConsts, VmConstsContext

scope = ScopedName.from_string


def dummy_evaluator(expr):
    return 0


def test_vmconsts_simple():
    identifier_values = {
        scope("x.y.z"): ConstDefinition(1),
        scope("x.z"): ConstDefinition(2),
        scope("y"): ConstDefinition(3),
    }
    context = VmConstsContext(
        identifiers=IdentifierManager.from_dict(identifier_values),
        evaluator=dummy_evaluator,
        reference_manager=ReferenceManager(),
        flow_tracking_data=FlowTrackingDataActual(ap_tracking=RegTrackingData()),
        memory={},
        pc=0,
    )
    consts = VmConsts(context=context, accessible_scopes=[ScopedName()])
    assert consts.x.y.z == 1
    assert consts.x.z == 2
    assert consts.y == 3
    assert isinstance(consts.x, VmConsts)


def test_label_and_namespace():
    identifier_values = {
        scope("a"): NamespaceDefinition(),
        scope("a.x"): LabelDefinition(10),
        scope("a.x.y"): ConstDefinition(1),
        scope("a.y"): ConstDefinition(2),
    }
    context = VmConstsContext(
        identifiers=IdentifierManager.from_dict(identifier_values),
        evaluator=dummy_evaluator,
        reference_manager=ReferenceManager(),
        flow_tracking_data=FlowTrackingDataActual(ap_tracking=RegTrackingData()),
        memory={},
        pc=0,
    )
    consts = VmConsts(context=context, accessible_scopes=[ScopedName()])
    assert consts.a.x.instruction_offset_ == 10
    assert consts.a.y == 2
    assert consts.a.x.y == 1


def test_alias():
    identifier_values = {
        scope("w"): AliasDefinition(scope("z.y")),
        scope("x"): AliasDefinition(scope("z")),
        scope("z.y"): ConstDefinition(1),
    }
    context = VmConstsContext(
        identifiers=IdentifierManager.from_dict(identifier_values),
        evaluator=dummy_evaluator,
        reference_manager=ReferenceManager(),
        flow_tracking_data=FlowTrackingDataActual(ap_tracking=RegTrackingData()),
        memory={},
        pc=0,
    )
    consts = VmConsts(context=context, accessible_scopes=[ScopedName()])
    assert consts.x.y == 1
    assert consts.w == 1


def test_scope_order():
    identifier_values = {
        scope("x.y"): ConstDefinition(1),
        scope("y"): ConstDefinition(2),
    }
    context = VmConstsContext(
        identifiers=IdentifierManager.from_dict(identifier_values),
        evaluator=dummy_evaluator,
        reference_manager=ReferenceManager(),
        flow_tracking_data=FlowTrackingDataActual(ap_tracking=RegTrackingData()),
        memory={},
        pc=0,
    )
    consts = VmConsts(context=context, accessible_scopes=[ScopedName(), scope("x")])
    assert consts.y == 1
    assert consts.x.y == 1


def test_references():
    reference_manager = ReferenceManager()
    references = {
        scope("x.ref"): reference_manager.alloc_id(
            Reference(
                pc=0,
                value=parse_expr("[ap + 1]"),
                ap_tracking_data=RegTrackingData(group=0, offset=2),
            )
        ),
        scope("x.ref2"): reference_manager.alloc_id(
            Reference(
                pc=0,
                value=parse_expr("[ap + 1] + 0"),
                ap_tracking_data=RegTrackingData(group=0, offset=2),
            )
        ),
        scope("x.ref3"): reference_manager.alloc_id(
            Reference(
                pc=0,
                value=parse_expr("ap + 1"),
                ap_tracking_data=RegTrackingData(group=0, offset=2),
            )
        ),
        scope("x.typeref"): reference_manager.alloc_id(
            Reference(
                pc=0,
                value=mark_types_in_expr_resolved(parse_expr("cast(ap + 1, MyStruct*)")),
                ap_tracking_data=RegTrackingData(group=0, offset=3),
            )
        ),
        scope("x.typeref2"): reference_manager.alloc_id(
            Reference(
                pc=0,
                value=mark_types_in_expr_resolved(parse_expr("cast([ap + 1], MyStruct*)")),
                ap_tracking_data=RegTrackingData(group=0, offset=3),
            )
        ),
    }

    my_struct = TypeStruct(scope=scope("MyStruct"))
    my_struct_star = TypePointer(pointee=my_struct)
    identifier_values = {
        scope("x.ref"): ReferenceDefinition(
            full_name=scope("x.ref"), cairo_type=TypeFelt(), references=[]
        ),
        scope("x.ref2"): ReferenceDefinition(
            full_name=scope("x.ref2"), cairo_type=TypeFelt(), references=[]
        ),
        scope("x.ref3"): ReferenceDefinition(
            full_name=scope("x.ref3"), cairo_type=TypeFelt(), references=[]
        ),
        scope("x.typeref"): ReferenceDefinition(
            full_name=scope("x.typeref"), cairo_type=my_struct_star, references=[]
        ),
        scope("x.typeref2"): ReferenceDefinition(
            full_name=scope("x.typeref2"), cairo_type=my_struct_star, references=[]
        ),
        scope("MyStruct"): StructDefinition(
            full_name=scope("MyStruct"),
            members={
                "member": MemberDefinition(offset=10, cairo_type=TypeFelt()),
                "struct": MemberDefinition(offset=11, cairo_type=my_struct),
            },
            size=11,
        ),
    }
    identifiers = IdentifierManager.from_dict(identifier_values)
    prime = 2**64 + 13
    ap = 100
    fp = 200
    memory: MaybeRelocatableDict = {
        (ap - 2) + 1: 1234,
        (ap - 1) + 1: 1000,
        (ap - 1) + 1 + 2: 13,
        (ap - 1) + 1 + 10: 17,
    }

    flow_tracking_data = FlowTrackingDataActual(
        ap_tracking=RegTrackingData(group=0, offset=4),
        reference_ids=references,
    )
    context = VmConstsContext(
        identifiers=identifiers,
        evaluator=ExpressionEvaluator(prime, ap, fp, memory, identifiers).eval,
        reference_manager=reference_manager,
        flow_tracking_data=flow_tracking_data,
        memory=memory,
        pc=0,
    )
    consts = VmConsts(context=context, accessible_scopes=[ScopedName()])

    assert consts.x.ref == memory[(ap - 2) + 1]
    assert consts.x.typeref.address_ == (ap - 1) + 1
    assert consts.x.typeref.member == memory[(ap - 1) + 1 + 10]
    with pytest.raises(IdentifierError, match="'abc' is not a member of 'MyStruct'."):
        consts.x.typeref.abc

    with pytest.raises(IdentifierError, match="'SIZE' is not a member of 'MyStruct'."):
        consts.x.typeref.SIZE

    with pytest.raises(AssertionError, match="Cannot change the value of a struct definition."):
        consts.MyStruct = 13

    assert consts.MyStruct.member == 10
    with pytest.raises(AssertionError, match="Cannot change the value of a constant."):
        consts.MyStruct.member = 13

    assert consts.MyStruct.SIZE == 11
    with pytest.raises(AssertionError, match="Cannot change the value of a constant."):
        consts.MyStruct.SIZE = 13

    with pytest.raises(IdentifierError, match="'abc' is not a member of 'MyStruct'."):
        consts.MyStruct.abc

    # Test that VmConsts can be used to assign values to references of the form '[...]'.
    memory.clear()

    consts.x.ref = 1234
    assert memory == {(ap - 2) + 1: 1234}

    memory.clear()
    # Use "type: ignore" since mypy is unable to deduce the type of members of VmConsts.
    consts.x.typeref.member = 1001  # type: ignore
    assert memory == {(ap - 1) + 1 + 10: 1001}

    memory.clear()
    consts.x.typeref2 = 4321
    assert memory == {(ap - 1) + 1: 4321}

    consts.x.typeref2.member = 1  # type: ignore
    assert memory == {
        (ap - 1) + 1: 4321,
        4321 + 10: 1,
    }

    consts.x.typeref2.struct.member = 2  # type: ignore
    assert memory == {
        (ap - 1) + 1: 4321,
        4321 + 10: 1,
        4321 + 11 + 10: 2,
    }

    with pytest.raises(AssertionError, match="Cannot change the value of a scope definition"):
        consts.x = 1000
    with pytest.raises(
        AssertionError,
        match=r"x.ref2 \(= \[ap \+ 1\] \+ 0\) does not reference memory and cannot be assigned.",
    ):
        consts.x.ref2 = 1000
    with pytest.raises(
        AssertionError,
        match=r"x.typeref \(= ap \+ 1\) does not reference memory and cannot be assigned.",
    ):
        consts.x.typeref = 1000


def get_vm_consts(
    identifier_values,
    reference_manager,
    flow_tracking_data,
    memory: Optional[MutableMapping[MaybeRelocatable, MaybeRelocatable]] = None,
):
    """
    Creates a simple VmConsts object.
    """
    memory = {} if memory is None else memory
    identifiers = IdentifierManager.from_dict(identifier_values)
    context = VmConstsContext(
        identifiers=identifiers,
        evaluator=ExpressionEvaluator[MaybeRelocatable](
            2**64 + 13, 0, 0, memory, identifiers
        ).eval,
        reference_manager=reference_manager,
        flow_tracking_data=flow_tracking_data,
        memory=memory,
        pc=9,
    )
    return VmConsts(context=context, accessible_scopes=[ScopedName()])


def test_reference_rebinding():
    identifier_values = {
        scope("ref"): ReferenceDefinition(
            full_name=scope("ref"),
            cairo_type=TypeFelt(),
            references=[],
        )
    }

    reference_manager = ReferenceManager()
    flow_tracking_data = FlowTrackingDataActual(ap_tracking=RegTrackingData())
    consts = get_vm_consts(identifier_values, reference_manager, flow_tracking_data)
    with pytest.raises(FlowTrackingError, match="Reference 'ref' is revoked."):
        consts.ref

    flow_tracking_data2 = flow_tracking_data.add_reference(
        reference_manager=reference_manager,
        name=scope("ref"),
        ref=Reference(
            pc=10,
            value=parse_expr("10"),
            ap_tracking_data=RegTrackingData(group=0, offset=2),
        ),
    )
    consts = get_vm_consts(identifier_values, reference_manager, flow_tracking_data2)
    assert consts.ref == 10


def test_reference_to_structs():
    t = TypeStruct(scope=scope("T"))
    t_star = TypePointer(pointee=t)
    identifier_values = {
        scope("ref"): ReferenceDefinition(full_name=scope("ref"), cairo_type=t, references=[]),
        scope("T"): StructDefinition(
            full_name=scope("T"),
            members={
                "x": MemberDefinition(offset=3, cairo_type=t_star),
            },
            size=4,
        ),
    }
    reference_manager = ReferenceManager()
    flow_tracking_data = FlowTrackingDataActual(ap_tracking=RegTrackingData())
    flow_tracking_data2 = flow_tracking_data.add_reference(
        reference_manager=reference_manager,
        name=scope("ref"),
        ref=Reference(
            pc=0,
            value=mark_types_in_expr_resolved(parse_expr("[cast(100, T*)]")),
            ap_tracking_data=RegTrackingData(group=0, offset=2),
        ),
    )
    memory: MaybeRelocatableDict = {103: 200}
    consts = get_vm_consts(identifier_values, reference_manager, flow_tracking_data2, memory=memory)

    assert consts.ref.address_ == 100
    assert consts.ref.x.address_ == 200
    # Set the pointer ref.x.x to 300.
    consts.ref.x.x = 300
    assert memory[203] == 300
    # Use "type: ignore" since mypy is unable to deduce the type of members of VmConsts.
    assert consts.ref.x.x.address_ == 300  # type: ignore

    assert consts.ref.type_ == consts.T


def test_missing_attributes():
    identifier_values = {
        scope("x.y"): ConstDefinition(1),
        scope("z"): AliasDefinition(scope("x")),
        scope("x.missing"): AliasDefinition(scope("nothing")),
    }

    context = VmConstsContext(
        identifiers=IdentifierManager.from_dict(identifier_values),
        evaluator=dummy_evaluator,
        reference_manager=ReferenceManager(),
        flow_tracking_data=FlowTrackingDataActual(ap_tracking=RegTrackingData()),
        memory={},
        pc=0,
    )
    consts = VmConsts(context=context, accessible_scopes=[ScopedName()])

    # Identifier not exists anywhere.
    with pytest.raises(MissingIdentifierError, match="Unknown identifier 'xx'."):
        consts.xx

    # Identifier not exists in accessible scopes.
    with pytest.raises(MissingIdentifierError, match="Unknown identifier 'y'."):
        consts.y

    # Recursive search.
    with pytest.raises(MissingIdentifierError, match="Unknown identifier 'x.z'."):
        consts.x.z

    # Pass through alias.
    with pytest.raises(MissingIdentifierError, match="Unknown identifier 'z.x'."):
        consts.z.x

    # Pass through bad alias.
    with pytest.raises(
        IdentifierError,
        match="Alias resolution failed: x.missing -> nothing. Unknown identifier 'nothing'.",
    ):
        consts.x.missing.y


def test_unsupported_attribute():
    class UnsupportedIdentifier(IdentifierDefinition):
        TYPE: ClassVar[str] = "tested_t"

    identifier_values = {
        scope("x"): UnsupportedIdentifier(),
        scope("y.z"): UnsupportedIdentifier(),
    }
    context = VmConstsContext(
        identifiers=IdentifierManager.from_dict(identifier_values),
        evaluator=dummy_evaluator,
        reference_manager=ReferenceManager(),
        flow_tracking_data=FlowTrackingDataActual(ap_tracking=RegTrackingData()),
        memory={},
        pc=0,
    )
    consts = VmConsts(context=context, accessible_scopes=[scope("")])

    # Identifier in root namespace.
    with pytest.raises(
        NotImplementedError, match="Unsupported identifier type 'tested_t' of identifier 'x'."
    ):
        consts.x

    # Identifier in sub namespace.
    with pytest.raises(
        NotImplementedError, match="Unsupported identifier type 'tested_t' of identifier 'y.z'."
    ):
        consts.y.z


def test_get_dunder_something():
    context = VmConstsContext(
        identifiers=IdentifierManager(),
        evaluator=dummy_evaluator,
        reference_manager=ReferenceManager(),
        flow_tracking_data=FlowTrackingDataActual(ap_tracking=RegTrackingData()),
        memory={},
        pc=0,
    )
    consts = VmConsts(context=context, accessible_scopes=[scope("")])
    with pytest.raises(
        AttributeError, match=re.escape("'VmConsts' object has no attribute '__something'")
    ):
        consts.__something


def test_unparsed():
    identifier_values = {
        scope("x"): LabelDefinition(10),
    }
    context = VmConstsContext(
        identifiers=IdentifierManager.from_dict(identifier_values),
        evaluator=dummy_evaluator,
        reference_manager=ReferenceManager(),
        flow_tracking_data=FlowTrackingDataActual(ap_tracking=RegTrackingData()),
        memory={},
        pc=0,
    )
    consts = VmConsts(context=context, accessible_scopes=[scope("")])

    with pytest.raises(IdentifierError, match="Unexpected '.' after 'x' which is label."):
        consts.x.z


def test_revoked_reference():
    reference_manager = ReferenceManager()
    ref_id = reference_manager.alloc_id(
        reference=Reference(
            pc=0,
            value=parse_expr("[ap + 1]"),
            ap_tracking_data=RegTrackingData(group=0, offset=2),
        )
    )

    identifier_values = {
        scope("x"): ReferenceDefinition(full_name=scope("x"), cairo_type=TypeFelt(), references=[]),
    }
    identifiers = IdentifierManager.from_dict(identifier_values)
    prime = 2**64 + 13
    ap = 100
    fp = 200
    memory: MaybeRelocatableDict = {}

    flow_tracking_data = FlowTrackingDataActual(
        ap_tracking=RegTrackingData(group=1, offset=4),
        reference_ids={scope("x"): ref_id},
    )
    context = VmConstsContext(
        identifiers=identifiers,
        evaluator=ExpressionEvaluator(prime, ap, fp, memory, identifiers).eval,
        reference_manager=reference_manager,
        flow_tracking_data=flow_tracking_data,
        memory=memory,
        pc=0,
    )
    consts = VmConsts(context=context, accessible_scopes=[ScopedName()])

    with pytest.raises(FlowTrackingError, match="Reference 'x' is revoked."):
        consts.x

    with pytest.raises(FlowTrackingError, match="Reference 'x' is revoked."):
        consts.x = 85
