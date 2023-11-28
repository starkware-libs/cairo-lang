import dataclasses
import inspect
from abc import abstractmethod
from dataclasses import field
from typing import ClassVar, Dict, Iterable, Set, Type, cast

from services.everest.api.gateway.transaction import EverestTransaction
from services.everest.business_logic.internal_transaction import (
    EverestInternalStateTransaction,
    EverestInternalTransaction,
)
from starkware.starknet.business_logic.fact_state.contract_state_objects import StateSelector
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starknet.services.api.gateway.transaction import Transaction
from starkware.starkware_utils.config_base import Config

# Do not use `__post_init__` on internal transactions.
# An inconsistency may happen during upgrade: a transaction may pass the Gateway,
# then an upgrade happens, then reach the Batcher. When a transaction reaches the Batcher,
# we do not want it to fail while being built (read from DB).


# Mypy has a problem with dataclasses that contain unimplemented abstract methods.
# See https://github.com/python/mypy/issues/5374 for details on this problem.
@dataclasses.dataclass(frozen=True)  # type: ignore[misc]
class InternalTransaction(EverestInternalTransaction):
    """
    StarkNet internal transaction base class.
    """

    # A unique identifier of the transaction in the StarkNet network.
    hash_value: int = field(metadata=fields.transaction_hash_metadata)

    # A mapping of external to internal type.
    # Used for creating an internal transaction from an external one (and vice versa) using only
    # base classes.
    external_to_internal_cls: ClassVar[Dict[Type[Transaction], Type["InternalTransaction"]]] = {}

    @classmethod
    def __init_subclass__(cls, **kwargs):
        """
        Registers the related external type class variable to the external-to-internal class
        mapping.
        """
        super().__init_subclass__(**kwargs)  # type: ignore[call-arg]

        if inspect.isabstract(cls) or not isinstance(cls.related_external_cls, type):
            # Only record relevant types: concrete classes (leaves of inheritance),
            # and ones that have a related external type.
            return

        # Record only the first class with this related external type.
        recorded_cls = cls.external_to_internal_cls.setdefault(
            cls.related_external_cls, cls  # type: ignore[arg-type]
        )

        # Check that this class is indeed that class or a subclass of it.
        assert issubclass(
            cls, recorded_cls
        ), f"Internal class {cls.__name__} must be a subclass of {recorded_cls.__name__}."

    @property
    @classmethod
    @abstractmethod
    def tx_type(cls) -> TransactionType:
        """
        Returns the corresponding transaction type enum. Used in the base class' schema.
        Subclasses should define it as a class variable.
        """

    @property
    @classmethod
    @abstractmethod
    def related_external_cls(cls) -> Type[Transaction]:
        """
        Returns the corresponding external transaction class. Used in converting between
        external/internal types.
        Subclasses should define it as a class variable.
        """

    @property
    def external_name(self) -> str:
        return self.related_external_cls.__name__

    @classmethod
    def from_external(
        cls, external_tx: EverestTransaction, general_config: Config
    ) -> "InternalTransaction":
        """
        Returns an internal transaction generated based on an external one.
        """
        # Downcast arguments to application-specific types.
        assert isinstance(external_tx, Transaction)
        assert isinstance(general_config, StarknetGeneralConfig)

        internal_cls = cls.external_to_internal_cls.get(type(external_tx))
        if internal_cls is None:
            raise NotImplementedError(f"Unsupported transaction type {type(external_tx).__name__}.")

        return internal_cls._specific_from_external(
            external_tx=external_tx, general_config=general_config
        )

    @abstractmethod
    def to_external(self) -> Transaction:
        """
        Returns an external transaction generated based on an internal one.
        """

    def verify_signatures(self):
        """
        Verifies the signatures in the transaction.
        Unused in StarkNet.
        """

    @abstractmethod
    def get_state_selector(self, general_config: Config) -> StateSelector:
        """
        See base class for documentation.
        Declared here for return type downcast.
        """

    @staticmethod
    def get_state_selector_of_many(
        txs: Iterable[EverestInternalStateTransaction], general_config: Config
    ) -> StateSelector:
        """
        Returns the state selector of a collection of transactions (i.e., union of selectors).
        """
        # Downcast arguments to application-specific types.
        assert isinstance(general_config, StarknetGeneralConfig)
        txs = cast(Iterable[InternalTransaction], txs)

        contract_addresses: Set[int] = set()
        class_hashes: Set[int] = set()

        for tx in txs:
            state_selector = tx.get_state_selector(general_config=general_config)
            contract_addresses.update(state_selector.contract_addresses)
            class_hashes.update(state_selector.class_hashes)

        frozen_contract_addresses = frozenset(contract_addresses)
        frozen_class_hashes = frozenset(class_hashes)
        return StateSelector(
            contract_addresses=frozen_contract_addresses, class_hashes=frozen_class_hashes
        )

    @classmethod
    @abstractmethod
    def _specific_from_external(
        cls, external_tx: Transaction, general_config: StarknetGeneralConfig
    ) -> "InternalTransaction":
        """
        Returns an internal transaction generated based on an external one, where the input
        arguments are downcasted to application-specific types.
        """
