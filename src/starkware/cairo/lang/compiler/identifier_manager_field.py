from marshmallow import fields

from starkware.cairo.lang.compiler.identifier_definition import IdentifierDefinitionSchema
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.scoped_name import ScopedName


class IdentifierManagerField(fields.Field):
    """
    A field that behaves like an IdentifierManager, but serializes to a dictionary of identifiers.
    """

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        identifier_definition_schema = IdentifierDefinitionSchema()
        return {
            str(name): identifier_definition_schema.dump(identifier_definition)
            for name, identifier_definition in value.as_dict().items()
        }

    def _deserialize(self, value, attr, data, **kwargs) -> IdentifierManager:
        identifier_definition_schema = IdentifierDefinitionSchema()
        return IdentifierManager.from_dict({
            ScopedName.from_string(name): identifier_definition_schema.load(
                serialized_identifier_definition)
            for name, serialized_identifier_definition in value.items()
        })
