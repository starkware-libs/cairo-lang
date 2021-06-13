from typing import ClassVar, Type

import marshmallow_oneofschema

from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass


class EverestTransaction(ValidatedMarshmallowDataclass):
    """
    Base class of application-specific external transaction base classes.
    Contains the API of an external transaction.
    """

    Schema: ClassVar[Type[marshmallow_oneofschema.OneOfSchema]]


class EverestAddTransactionRequest(ValidatedMarshmallowDataclass):
    tx: EverestTransaction
    tx_id: int
