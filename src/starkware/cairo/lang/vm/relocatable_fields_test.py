from dataclasses import field
from typing import ClassVar, Dict, Type

import marshmallow
import marshmallow_dataclass

from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.cairo.lang.vm.relocatable_fields import (
    MaybeRelocatableDictField, MaybeRelocatableField)


@marshmallow_dataclass.dataclass
class DummyStruct:
    val: MaybeRelocatable = field(metadata=dict(marshmallow_field=MaybeRelocatableField()))
    dct: Dict[MaybeRelocatable, MaybeRelocatable] = field(
        metadata=dict(marshmallow_field=MaybeRelocatableDictField()))
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema


def test_relocatable_fields_serialize_deserialize():
    obj = DummyStruct(
        val=RelocatableValue(3, 5),
        dct={
            100: RelocatableValue(0, 8),
            RelocatableValue(4, 5): 7,
            RelocatableValue(1, 2): RelocatableValue(3, 4),
        },
    )
    assert DummyStruct.Schema().load(DummyStruct.Schema().dump(obj)) == obj
