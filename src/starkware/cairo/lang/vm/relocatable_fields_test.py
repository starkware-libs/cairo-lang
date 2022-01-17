from dataclasses import field
from typing import Dict

import marshmallow_dataclass

from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.cairo.lang.vm.relocatable_fields import (
    MaybeRelocatableDictField,
    MaybeRelocatableField,
)


@marshmallow_dataclass.dataclass(frozen=True)
class DummyStruct:
    val: MaybeRelocatable = field(metadata=dict(marshmallow_field=MaybeRelocatableField()))
    dct: Dict[MaybeRelocatable, MaybeRelocatable] = field(
        metadata=dict(marshmallow_field=MaybeRelocatableDictField())
    )


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
