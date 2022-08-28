from dataclasses import field

import marshmallow_dataclass

from starkware.cairo.lang.compiler.identifier_definition import LabelDefinition
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.identifier_manager_field import IdentifierManagerField
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.starkware_utils.marshmallow_dataclass_fields import additional_metadata

scope = ScopedName.from_string


def test_identifier_manager_field_serialization():
    @marshmallow_dataclass.dataclass
    class Foo:
        identifiers: IdentifierManager = field(
            metadata=additional_metadata(marshmallow_field=IdentifierManagerField())
        )

    Schema = marshmallow_dataclass.class_schema(Foo)

    foo = Foo(
        identifiers=IdentifierManager.from_dict(
            {
                scope("aa.b"): LabelDefinition(pc=1000),
            }
        )
    )
    serialized = Schema().dump(foo)
    assert serialized == {"identifiers": {"aa.b": {"pc": 1000, "type": "label"}}}

    assert Schema().load(serialized) == foo
