from dataclasses import field

import marshmallow_dataclass

from starkware.cairo.lang.vm.relocatable import (
    MaybeRelocatable,
    MaybeRelocatableDict,
    RelocatableValue,
)
from starkware.cairo.lang.vm.relocatable_fields import (
    MaybeRelocatableDictField,
    MaybeRelocatableField,
)
from starkware.starkware_utils.marshmallow_dataclass_fields import additional_metadata
from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass


@marshmallow_dataclass.dataclass(frozen=True)
class DummyStruct(ValidatedMarshmallowDataclass):
    val: MaybeRelocatable = field(
        metadata=additional_metadata(marshmallow_field=MaybeRelocatableField())
    )
    dct: MaybeRelocatableDict = field(
        metadata=additional_metadata(marshmallow_field=MaybeRelocatableDictField())
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
