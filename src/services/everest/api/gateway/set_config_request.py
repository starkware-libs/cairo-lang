from dataclasses import field
from typing import Optional

import marshmallow.fields as mfields
import marshmallow_dataclass

from starkware.starkware_utils.error_handling import StarkErrorCode, stark_assert
from starkware.starkware_utils.field_validators import (
    validate_alternative_endpoint,
    validate_failure_description_endpoint,
)
from starkware.starkware_utils.marshmallow_dataclass_fields import additional_metadata
from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass


@marshmallow_dataclass.dataclass
class AlternativeEndpointSettingRequest(ValidatedMarshmallowDataclass):
    """
    In order to use this request, StarkWare must configure your setup to support dynamically
    configuring the endpoint for alternative transactions.

    AlternativeEndpointSettingRequest is sent from the client to the gateway
    when the configuration of the alternative transaction request endpoint is changed.
    The client should provide either of the following:
    A bearer token, or client and server certificates.

    :param url: The URL of the endpoint.
    :type url: str
    :param failure_description_url: The URL address that receives the failure description.
    :type failure_description_url: str
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
    failure_description_url: Optional[str] = field(
        metadata=additional_metadata(
            marshmallow_field=mfields.String(
                validate=validate_failure_description_endpoint, allow_none=True
            ),
        ),
        default=None,
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
