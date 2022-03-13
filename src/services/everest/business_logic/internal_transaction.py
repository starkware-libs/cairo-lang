import functools
import operator
from abc import abstractmethod
from typing import Any, ClassVar, Dict, Iterable, Optional, Type

import marshmallow
import marshmallow_dataclass
from marshmallow_oneofschema import OneOfSchema

from services.everest.api.gateway.transaction import EverestTransaction
from services.everest.business_logic.state import CarriedStateBase, StateSelectorBase
from starkware.starkware_utils.config_base import Config
from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass


class SchemaTracker:
    """
    Tracks a set of classes and provides a OneOfSchema which can be used to serialize them.
    """

    def __init__(self):
        self.classes: Dict[str, Any] = {}
        classes = self.classes

        class TransactionSchema(OneOfSchema):

            type_schemas: Dict[str, Type[marshmallow.Schema]] = {}

            def get_obj_type(self, obj):
                name = type(obj).__name__
                assert name in classes.keys() and classes[name] == type(
                    obj
                ), f"Trying to serialized the object {obj} that was not registered first."
                # We register the Schema object here, since it might not exists when the object
                # itself is registered.
                if name not in self.type_schemas.keys():
                    self.type_schemas[name] = obj.Schema
                return name

        self.Schema = TransactionSchema

    def add_class(self, cls: type):
        cls_name = cls.__name__
        if cls_name in self.classes:
            assert (
                self.classes[cls_name] == cls
            ), f"Trying to register two classes with the same name {cls_name}"
        else:
            self.classes[cls_name] = cls


class EverestTransactionExecutionInfo(ValidatedMarshmallowDataclass):
    """
    Base class of classes containing information generated from an execution of a transaction on
    the state. Each Everest application may implement it specifically.
    Note that this object will only be relevant if the transaction executed successfully.
    """


@marshmallow_dataclass.dataclass(frozen=True)
class TransactionExecutionInfo(EverestTransactionExecutionInfo):
    """
    A non-abstract derived class for completeness of AggregatedScope. Used by StarkEx and Perpetual.
    """


class EverestInternalStateTransaction(ValidatedMarshmallowDataclass):
    """
    Base class of application-specific internal transaction base classes.
    Contains the API of an internal transaction that can apply changes on the state.
    """

    schema_tracker: ClassVar[Optional[SchemaTracker]] = None

    @classmethod
    def track_subclasses(cls):
        """
        Creates a OneOfSchema schema for this class, and adds each subclass to this schema.
        """
        cls.schema_tracker = SchemaTracker()
        cls.Schema = cls.schema_tracker.Schema

    @classmethod
    def __init_subclass__(cls, **kwargs):
        """
        Registers the given cls class as a subclass of its first parent that called
        track_subclasses (if such a parent exists).
        """
        super().__init_subclass__(**kwargs)  # type: ignore[call-arg]
        if cls.schema_tracker is None:
            return
        cls.schema_tracker.add_class(cls)

    @abstractmethod
    async def apply_state_updates(
        self, state: CarriedStateBase, general_config: Config
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
