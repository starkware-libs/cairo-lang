import dataclasses
from typing import ClassVar, Optional, Tuple, Type

from services.everest.api.gateway.transaction import EverestTransaction
from starkware.starknet.business_logic.execution.objects import (
    CallInfo,
    ExecutionResourcesManager,
    ResourcesMapping,
)
from starkware.starknet.business_logic.state.state_api import SyncState
from starkware.starknet.business_logic.transaction.fee import calculate_tx_fee
from starkware.starknet.business_logic.transaction.objects import (
    InternalAccountTransaction,
    InternalDeclare,
    InternalDeployAccount,
    InternalInvokeFunction,
    InternalTransaction,
)
from starkware.starknet.business_logic.transaction.state_objects import FeeInfo
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.services.api.feeder_gateway.response_objects import FeeEstimationInfo
from starkware.starknet.services.api.gateway.transaction import (
    AccountTransaction,
    Declare,
    DeployAccount,
    DeprecatedDeclare,
    InvokeFunction,
)
from starkware.starkware_utils.config_base import Config


def format_fee_info(gas_price: int, overall_fee: int) -> FeeEstimationInfo:
    return FeeEstimationInfo(
        overall_fee=overall_fee, gas_price=gas_price, gas_usage=overall_fee // gas_price
    )


@dataclasses.dataclass(frozen=True)  # type: ignore[misc]
class InternalAccountTransactionForSimulate(InternalAccountTransaction):
    """
    Represents an internal transaction in the StarkNet network for the simulate transaction API.
    """

    # Simulation flags; should be replaced with actual values after construction.
    skip_validate: Optional[bool] = None

    # Override InternalAccountTransaction flag; enable query-version transactions to be created and
    # executed.
    only_query: ClassVar[bool] = True

    @classmethod
    def create_for_simulate(
        cls, external_tx: EverestTransaction, general_config: Config, skip_validate: bool
    ) -> InternalTransaction:
        """
        Returns an internal transaction for simulation with the related simulation flags.
        """
        internal_tx_without_flags = cls._from_external(
            external_tx=external_tx, general_config=general_config
        )
        return dataclasses.replace(internal_tx_without_flags, skip_validate=skip_validate)

    @classmethod
    def _from_external(
        cls, external_tx: EverestTransaction, general_config: Config
    ) -> InternalTransaction:
        """
        Returns an internal transaction for simulation, generated based on an external one.
        """
        # Downcast arguments to application-specific types.
        assert isinstance(external_tx, AccountTransaction)
        assert isinstance(general_config, StarknetGeneralConfig)

        internal_cls: Type[InternalAccountTransactionForSimulate]
        if isinstance(external_tx, InvokeFunction):
            internal_cls = InternalInvokeFunctionForSimulate
        elif isinstance(external_tx, (Declare, DeprecatedDeclare)):
            internal_cls = InternalDeclareForSimulate
        elif isinstance(external_tx, DeployAccount):
            internal_cls = InternalDeployAccountForSimulate
        else:
            raise NotImplementedError(f"Unexpected type {type(external_tx).__name__}.")

        return internal_cls._specific_from_external(
            external_tx=external_tx, general_config=general_config
        )

    def charge_fee(
        self, state: SyncState, resources: ResourcesMapping, general_config: StarknetGeneralConfig
    ) -> FeeInfo:
        """
        Overrides the charge fee method. Only calculates the actual fee and does not charge any fee.
        """
        actual_fee = calculate_tx_fee(
            gas_price=state.block_info.gas_price, resources=resources, general_config=general_config
        )

        return None, actual_fee

    def run_validate_entrypoint(
        self,
        remaining_gas: int,
        state: SyncState,
        resources_manager: ExecutionResourcesManager,
        general_config: StarknetGeneralConfig,
    ) -> Tuple[Optional[CallInfo], int]:
        """
        Overrides the run_validate_entrypoint method. Validates only if skip_validate is False.
        """
        assert self.skip_validate is not None, "skip_validate flag is not initialized."
        if self.skip_validate:
            return None, remaining_gas

        return super().run_validate_entrypoint(
            remaining_gas=remaining_gas,
            state=state,
            resources_manager=resources_manager,
            general_config=general_config,
        )


@dataclasses.dataclass(frozen=True)
class InternalInvokeFunctionForSimulate(
    InternalAccountTransactionForSimulate, InternalInvokeFunction
):
    """
    Represents an internal invoke function in the StarkNet network for the simulate transaction API.
    """


@dataclasses.dataclass(frozen=True)
class InternalDeclareForSimulate(InternalAccountTransactionForSimulate, InternalDeclare):
    """
    Represents an internal declare in the StarkNet network for the simulate transaction API.
    """


@dataclasses.dataclass(frozen=True)
class InternalDeployAccountForSimulate(
    InternalAccountTransactionForSimulate, InternalDeployAccount
):
    """
    Represents an internal deploy account in the StarkNet network for the simulate transaction API.
    """
