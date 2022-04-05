import dataclasses
from abc import ABC, abstractmethod
from typing import List, Optional

from starkware.starknet.wallets.starknet_context import StarknetContext

DEFAULT_ACCOUNT_DIR = "~/.starknet_accounts"


@dataclasses.dataclass
class WrappedMethod:
    address: int
    selector: int
    calldata: List[int]
    max_fee: int
    signature: List[int]


class Account(ABC):
    @classmethod
    @abstractmethod
    async def create(cls, starknet_context: StarknetContext, account_name: str) -> "Account":
        """
        Constructs an instance of the class.
        """

    @abstractmethod
    async def deploy(self):
        """
        Initializes the account. For example, this may include choosing a new random private key
        and deploying the account contract to the network.
        """

    @abstractmethod
    async def sign_invoke_transaction(
        self,
        contract_address: int,
        selector: int,
        calldata: List[int],
        chain_id: int,
        max_fee: int,
        version: int,
        nonce: Optional[int],
    ) -> WrappedMethod:
        """
        Given a transaction to execute (or call) within the context of the account,
        prepares the required information for invoking it through the account contract.
        nonce is the nonce to be used in the transaction. If not specified, the current nonce
        is queried from the StarkNet system.
        """
