from typing import Callable, ClassVar, Type

import marshmallow_oneofschema

from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass


class EverestTransaction(ValidatedMarshmallowDataclass):
    """
    Base class of application-specific external transaction base classes.
    Contains the API of an external transaction.
    """

    Schema: ClassVar[Type[marshmallow_oneofschema.OneOfSchema]]

    def log_additional_data(self, logger: Callable[[str], None]) -> None:
        """
        Logs additional data that isn't present in the __repr__ or __str__ functions.
        """



class EverestAddTransactionRequest(ValidatedMarshmallowDataclass):
    tx: EverestTransaction
    tx_id: int
