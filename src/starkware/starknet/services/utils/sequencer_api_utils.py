from typing import Type

from services.everest.api.gateway.transaction import EverestTransaction
from starkware.starknet.business_logic.execution.objects import ResourcesMapping
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
from starkware.starknet.business_logic.utils import verify_version
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.services.api.feeder_gateway.response_objects import FeeEstimationInfo
from starkware.starknet.services.api.gateway.transaction import (
    AccountTransaction,
    Declare,
    DeployAccount,
    InvokeFunction,
)
from starkware.starkware_utils.config_base import Config


def format_fee_info(gas_price: int, overall_fee: int) -> FeeEstimationInfo:
    return FeeEstimationInfo(
        overall_fee=overall_fee, gas_price=gas_price, gas_usage=overall_fee // gas_price
    )


class InternalAccountTransactionForSimulate(InternalAccountTransaction):
    """
    Represents an internal transaction in the StarkNet network for the simulate transaction API.
    """

    @classmethod
    def from_external(
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
        elif isinstance(external_tx, Declare):
            internal_cls = InternalDeclareForSimulate
        elif isinstance(external_tx, DeployAccount):
            internal_cls = InternalDeployAccountForSimulate
        else:
            raise NotImplementedError(f"Unexpected type {type(external_tx).__name__}.")

        return internal_cls._specific_from_external(
            external_tx=external_tx, general_config=general_config
        )

    def verify_version(self):
        verify_version(version=self.version, only_query=True, old_supported_versions=[0])

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


class InternalInvokeFunctionForSimulate(
    InternalAccountTransactionForSimulate, InternalInvokeFunction
):
    """
    Represents an internal invoke function in the StarkNet network for the simulate transaction API.
    """


class InternalDeclareForSimulate(InternalAccountTransactionForSimulate, InternalDeclare):
    """
    Represents an internal declare in the StarkNet network for the simulate transaction API.
    """


class InternalDeployAccountForSimulate(
    InternalAccountTransactionForSimulate, InternalDeployAccount
):
    """
    Represents an internal deploy account in the StarkNet network for the simulate transaction API.
    """

    def verify_version(self):
        verify_version(version=self.version, only_query=True, old_supported_versions=[])
