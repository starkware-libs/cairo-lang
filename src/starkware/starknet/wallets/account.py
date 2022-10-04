from abc import ABC, abstractmethod
from typing import Awaitable, Callable, List, Tuple

from starkware.starknet.services.api.contract_class import ContractClass
from starkware.starknet.services.api.gateway.transaction import (
    Declare,
    DeployAccount,
    InvokeFunction,
)
from starkware.starknet.wallets.starknet_context import StarknetContext

DEFAULT_ACCOUNT_DIR = "~/.starknet_accounts"


class Account(ABC):
    @classmethod
    @abstractmethod
    def create(cls, starknet_context: StarknetContext, account_name: str) -> "Account":
        """
        Constructs an instance of the class.
        """

    @abstractmethod
    def new_account(self) -> int:
        """
        Initializes the account. For example, this may include choosing a new random private key.
        Returns the contract address of the new account.
        """

    @abstractmethod
    async def deploy_account(
        self, max_fee: int, version: int, chain_id: int, dry_run: bool = False
    ) -> Tuple[DeployAccount, int]:
        """
        Prepares the deployment of the initialized account contract to the network.
        Returns the transaction and the new account address.
        """

    @abstractmethod
    async def invoke(
        self,
        contract_address: int,
        selector: int,
        calldata: List[int],
        chain_id: int,
        max_fee: int,
        version: int,
        nonce_callback: Callable[[int], Awaitable[int]],
        dry_run: bool = False,
    ) -> InvokeFunction:
        """
        Given a function (contract address, selector, calldata) to invoke (or call) within the
        context of the account, prepares the required information for invoking it through the
        account contract.
        nonce_callback is a callback that gets the address of the contract and returns the next
        nonce to use.
        """

    @abstractmethod
    async def deploy_contract(
        self,
        class_hash: int,
        salt: int,
        constructor_calldata: List[int],
        deploy_from_zero: bool,
        chain_id: int,
        max_fee: int,
        version: int,
        nonce_callback: Callable[[int], Awaitable[int]],
    ) -> Tuple[InvokeFunction, int]:
        """
        Prepares the required information for invoking a contract deployment function through
        the account contract.
        Returns the signed transaction and the deployed contract address.
        """

    @abstractmethod
    async def declare(
        self,
        contract_class: ContractClass,
        chain_id: int,
        max_fee: int,
        version: int,
        nonce_callback: Callable[[int], Awaitable[int]],
        dry_run: bool = False,
    ) -> Declare:
        """
        Prepares the required information for declaring a contract class through the account
        contract.
        """
