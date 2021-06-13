import marshmallow.fields as mfields

from starkware.starkware_utils.field_validators import validate_non_negative

# Fields data: validation data, dataclass metadata.
tx_id_marshmallow_field = mfields.Integer(
    strict=True, required=True, validate=validate_non_negative('tx_id'))

tx_id_field_metadata = dict(marshmallow_field=tx_id_marshmallow_field)
