import functools
import operator
from abc import abstractmethod
from typing import Iterable, Iterator, Optional, Type

from services.everest.api.gateway.transaction import EverestTransaction
from services.everest.business_logic.state import StateSelectorBase
from services.everest.business_logic.state_api import StateProxy
from services.everest.business_logic.transaction_execution_objects import (
    EverestTransactionExecutionInfo,
)
from starkware.starkware_utils.config_base import Config
from starkware.starkware_utils.one_of_schema_tracker import SubclassSchemaTracker


class EverestInternalStateTransaction(SubclassSchemaTracker):
    """
    Base class of application-specific internal transaction base classes.
    Contains the API of an internal transaction that can apply changes on the state.
    """

    @abstractmethod
    async def apply_state_updates(
        self, state: StateProxy, general_config: Config
    ) -> Optional[EverestTransactionExecutionInfo]:
        """
        Applies the transaction on the state in an atomic manner.
        Returns an object containing information about the execution of the transaction, or None -
        can be decided per application.
        The arguments must be downcasted (by asserting their type) to the application-specific
        corresponding types.
        """

    @abstractmethod
    def get_state_selector(self, general_config: Config) -> StateSelectorBase:
        """
        Returns the state selector of the transaction (i.e., subset of state Merkle leaves it
        affects).
        The arguments must be downcasted (by asserting their type) to the application-specific
        corresponding types.
        """

    @staticmethod
    @abstractmethod
    def get_state_selector_of_many(
        txs: Iterable["EverestInternalStateTransaction"], general_config: Config
    ) -> StateSelectorBase:
        """
        Returns the state selector of a collection of transactions (i.e., union of selectors).
        The implementation of this method must be to downcast the return type.
        """

    @staticmethod
    def _get_state_selector_of_many(
        txs: Iterable["EverestInternalStateTransaction"],
        general_config: Config,
        state_selector_cls: Type[StateSelectorBase],
    ) -> StateSelectorBase:
        return functools.reduce(
            operator.__or__,
            (tx.get_state_selector(general_config=general_config) for tx in txs),
            state_selector_cls.empty(),
        )


class EverestInternalTransaction(EverestInternalStateTransaction):
    """
    Base class of application-specific internal transaction base classes.
    Contains the API of an internal transaction that can apply changes on the state
    and be converted from/to an external transaction.
    """

    @property
    @classmethod
    @abstractmethod
    def related_external_cls(cls) -> Type[EverestTransaction]:
        """
        Returns the corresponding external transaction class. Used in converting between
        external/internal types.
        Subclasses should define it as a class variable.
        """

    @property
    def external_name(self) -> str:
        return self.related_external_cls.__name__

    @classmethod
    @abstractmethod
    def from_external(
        cls, external_tx: EverestTransaction, general_config: Config
    ) -> "EverestInternalTransaction":
        """
        Returns an internal transaction genearated based on an external one.
        """

    @abstractmethod
    def to_external(self) -> EverestTransaction:
        """
        Returns an external transaction genearated based on an internal one.
        """

    @abstractmethod
    def verify_signatures(self):
        """
        Verifies the signatures in the transaction.
        """


class HasInnerTxs:
    @abstractmethod
    def _txs(self) -> Iterator[EverestInternalTransaction]:
        raise NotImplementedError("_txs is not implemented for {type(self).__name__}.")
