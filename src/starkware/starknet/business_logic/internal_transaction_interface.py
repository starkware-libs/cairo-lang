import logging
from abc import abstractmethod
from typing import Iterable, Optional, cast

from services.everest.business_logic.internal_transaction import EverestInternalStateTransaction
from services.everest.business_logic.state import CarriedStateBase
from starkware.starknet.business_logic.execution.objects import TransactionExecutionInfo
from starkware.starknet.business_logic.state.state import CarriedState, StateSelector
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starkware_utils.config_base import Config
from starkware.starkware_utils.error_handling import StarkException

logger = logging.getLogger(__name__)


class InternalStateTransaction(EverestInternalStateTransaction):
    """
    StarkNet internal state transaction.
    This is the API of transactions that update the state,
    but do not necessarily have an external transaction counterpart.
    See for example, SyntheticTransaction.
    """

    @staticmethod
    def get_state_selector_of_many(
        txs: Iterable["EverestInternalStateTransaction"], general_config: Config
    ) -> StateSelector:
        """
        Returns the state selector of a collection of transactions (i.e., union of selectors).
        """
        # Downcast arguments to application-specific types.
        assert isinstance(general_config, StarknetGeneralConfig)

        state_selector = EverestInternalStateTransaction._get_state_selector_of_many(
            txs=txs, general_config=general_config, state_selector_cls=StateSelector
        )
        return cast(StateSelector, state_selector)

    async def apply_state_updates(
        self, state: CarriedStateBase, general_config: Config
    ) -> Optional[TransactionExecutionInfo]:
        """
        Applies the transaction on the commitment tree state in an atomic manner.
        """
        # Downcast arguments to application-specific types.
        assert isinstance(state, CarriedState)
        assert isinstance(general_config, StarknetGeneralConfig)

        with state.copy_and_apply() as state_to_update:
            try:
                execution_info = await self._apply_specific_state_updates(
                    state=state_to_update, general_config=general_config
                )
            except StarkException:
                # Raise StarkException-s as-is, so failure information is not lost.
                raise
            except Exception as exception:
                # Wrap all exceptions with StarkException, so the Batcher can continue running
                #   even after unexpected errors.
                logger.error(f"Unexpected failure; exception details: {exception}.", exc_info=True)
                raise StarkException(
                    code=StarknetErrorCode.UNEXPECTED_FAILURE, message=str(exception)
                )

        return execution_info

    @abstractmethod
    async def _apply_specific_state_updates(
        self, state: CarriedState, general_config: StarknetGeneralConfig
    ) -> Optional[TransactionExecutionInfo]:
        pass
