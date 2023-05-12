from abc import abstractmethod
from typing import Callable, ClassVar, Type, TypeVar

import marshmallow_oneofschema

from services.everest.api.gateway.transaction_type import TransactionTypeBase
from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass


class EverestTransaction(ValidatedMarshmallowDataclass):
    """
    Base class of application-specific external transaction base classes.
    Contains the API of an external transaction.
    """

    Schema: ClassVar[Type[marshmallow_oneofschema.OneOfSchema]]

    @property
    @classmethod
    @abstractmethod
    def tx_type(cls) -> TransactionTypeBase:
        """
        Returns the corresponding TransactionType enum, used in Schema.
        Subclasses should define it as a class variable.
        """

    def log_additional_data(self, logger: Callable[[str], None]) -> None:
        """
        Logs additional data that isn't present in the __repr__ or __str__ functions.
        """



class EverestAddTransactionRequest(ValidatedMarshmallowDataclass):
    tx: EverestTransaction
    tx_id: int


TEverestTransaction = TypeVar("TEverestTransaction", bound=EverestTransaction)
