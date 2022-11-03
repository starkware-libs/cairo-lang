from dataclasses import field
from typing import Optional

import marshmallow.fields as mfields
import marshmallow_dataclass

from starkware.starkware_utils.error_handling import StarkErrorCode, stark_assert
from starkware.starkware_utils.field_validators import validate_alternative_endpoint
from starkware.starkware_utils.marshmallow_dataclass_fields import additional_metadata
from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass


@marshmallow_dataclass.dataclass
class AlternativeEndpointSettingRequest(ValidatedMarshmallowDataclass):
    """
    This request is sent when the endpoint that receives the alternative transaction request
    is changed.
    The client should provide one of the following options:
        - Bearer token
        - Certificates: server certificate and client certificate

    :param url: The URL address of the endpoint.
    :type url: str
    :param bearer_token: The Bearer token.
    :type bearer_token: Optional[str]
    :param server_certificate: The server certificate.
    :type server_certificate: Optional[str]
    :param client_certificate: The client certificate.
    :type client_certificate: Optional[str]
    :param client_key: The client private key.
    :type client_key: Optional[str]
    """

    url: str = field(
        metadata=additional_metadata(
            marshmallow_field=mfields.String(validate=validate_alternative_endpoint),
        )
    )
    bearer_token: Optional[str] = field(
        metadata=additional_metadata(
            marshmallow_field=mfields.String(allow_none=True), description="Bearer token"
        ),
        default=None,
    )
    server_certificate: Optional[str] = field(
        metadata=additional_metadata(
            marshmallow_field=mfields.String(allow_none=True), description="Server certificates"
        ),
        default=None,
    )
    client_certificate: Optional[str] = field(
        metadata=additional_metadata(
            marshmallow_field=mfields.String(allow_none=True), description="Client certificates"
        ),
        default=None,
    )
    client_key: Optional[str] = field(
        metadata=additional_metadata(
            marshmallow_field=mfields.String(allow_none=True), description="Client private key"
        ),
        default=None,
    )

    def __post_init__(self):
        super().__post_init__()
        self._validate_set_config()

    def _validate_set_config(self) -> None:
        """
        Verifies at one of the two is given: Bearer token or certificates.
        If Bearer token is given -> certificates should be None.
        If certificates are given -> Bearer token should be None.
        """
        if self.bearer_token is None:
            stark_assert(
                (self.client_certificate is not None)
                and (self.server_certificate is not None)
                and (self.client_key is not None),
                code=StarkErrorCode.SCHEMA_VALIDATION_ERROR,
                message=f"Neither bearer token nor certificates is provided correctly.",
            )
        else:
            stark_assert(
                (self.client_certificate is None)
                and (self.server_certificate is None)
                and (self.client_key is None),
                code=StarkErrorCode.SCHEMA_VALIDATION_ERROR,
                message=f"Endpoint should not provide both bearer token and certificates.",
            )
