import json
import os
import shutil
from typing import Awaitable, Callable, List, Optional, Tuple

from services.external_api.client import JsonObject
from starkware.crypto.signature.signature import get_random_private_key, private_to_stark_key, sign
from starkware.starknet.core.os.class_hash import compute_class_hash
from starkware.starknet.core.os.contract_address.contract_address import (
    calculate_contract_address,
    calculate_contract_address_from_hash,
)
from starkware.starknet.core.os.transaction_hash.transaction_hash import (
    TransactionHashPrefix,
    calculate_declare_transaction_hash,
    calculate_deploy_account_transaction_hash,
    calculate_transaction_hash_common,
)
from starkware.starknet.definitions import fields
from starkware.starknet.public.abi import get_selector_from_name
from starkware.starknet.services.api.contract_class import ContractClass
from starkware.starknet.services.api.gateway.transaction import (
    Declare,
    DeployAccount,
    InvokeFunction,
)
from starkware.starknet.third_party.open_zeppelin.starknet_contracts import account_contract
from starkware.starknet.wallets.account import Account
from starkware.starknet.wallets.starknet_context import StarknetContext

ACCOUNT_FILE_NAME = "starknet_open_zeppelin_accounts.json"
DEPLOY_CONTRACT_SELECTOR = get_selector_from_name("deploy_contract")
GET_NONCE_SELECTOR = get_selector_from_name("get_nonce")


class AccountNotFoundException(Exception):
    pass


class OpenZeppelinAccount(Account):
    def __init__(self, starknet_context: StarknetContext, account_name: str):
        self.account_name = account_name
        self.starknet_context = starknet_context

    @classmethod
    def create(cls, starknet_context: StarknetContext, account_name: str) -> "OpenZeppelinAccount":
        return cls(starknet_context=starknet_context, account_name=account_name)

    @property
    def account_file(self):
        return os.path.join(
            os.path.expanduser(self.starknet_context.account_dir), ACCOUNT_FILE_NAME
        )

    async def declare(
        self,
        contract_class: ContractClass,
        chain_id: int,
        max_fee: int,
        version: int,
        nonce_callback: Callable[[int], Awaitable[int]],
        dry_run: bool = False,
    ) -> Declare:
        account_address, private_key = self._get_account_address_and_private_key(dry_run=dry_run)
        return sign_declare_tx(
            contract_class=contract_class,
            private_key=private_key,
            sender_address=account_address,
            chain_id=chain_id,
            max_fee=max_fee,
            version=version,
            nonce=await nonce_callback(account_address),
        )

    def _get_accounts(self) -> dict:
        # Read the account file.
        if os.path.exists(self.account_file):
            # First, load the file, and make sure it's in JSON format.
            accounts = json.load(open(self.account_file))
            # Make a backup of the file.
            shutil.copy(self.account_file, self.account_file + ".backup")
        else:
            accounts = {}
        return accounts

    def _get_account_given_accounts(self, accounts: dict) -> JsonObject:
        accounts_for_network = accounts.get(self.starknet_context.network_id, {})
        if self.account_name not in accounts_for_network:
            raise AccountNotFoundException(
                f"Account '{self.account_name}' for network '{self.starknet_context.network_id}' "
                "was not found. You can create a new account using the 'new_account' command."
            )
        return accounts_for_network[self.account_name]

    def new_account(self) -> int:
        # Read the account file.
        accounts = self._get_accounts()
        accounts_for_network = accounts.setdefault(self.starknet_context.network_id, {})
        assert self.account_name not in accounts_for_network, (
            f"Account '{self.account_name}' for network '{self.starknet_context.network_id}' "
            "already exists."
        )

        private_key = get_random_private_key()
        public_key = private_to_stark_key(private_key)
        salt = fields.ContractAddressSalt.get_random_value()
        contract_address = calculate_contract_address(
            salt=salt,
            contract_class=account_contract,
            constructor_calldata=[public_key],
            deployer_address=0,
        )

        accounts_for_network[self.account_name] = {
            "private_key": hex(private_key),
            "public_key": hex(public_key),
            "salt": hex(salt),
            "address": hex(contract_address),
            "deployed": False,
        }

        # Don't end sentences with '.', to allow easy double-click copy-pasting of the values.
        print(
            f"""\
Account address: 0x{contract_address:064x}
Public key: 0x{public_key:064x}
Move the appropriate amount of funds to the account, and then deploy the account
by invoking the 'starknet deploy_account' command.

NOTE: This is a modified version of the OpenZeppelin account contract. The signature is computed
differently.
"""
        )

        os.makedirs(name=os.path.dirname(self.account_file), exist_ok=True)
        with open(self.account_file, "w") as f:
            json.dump(accounts, f, indent=4)
            f.write("\n")

        return contract_address

    async def deploy_account(
        self, max_fee: int, version: int, chain_id: int, dry_run: bool = False
    ) -> Tuple[DeployAccount, int]:
        # Read the account file.
        accounts = self._get_accounts()
        account_to_deploy = self._get_account_given_accounts(accounts=accounts)
        tx = sign_deploy_account_tx(
            private_key=int(account_to_deploy["private_key"], 16),
            public_key=int(account_to_deploy["public_key"], 16),
            class_hash=compute_class_hash(account_contract),
            salt=int(account_to_deploy["salt"], 16),
            max_fee=max_fee,
            version=version,
            chain_id=chain_id,
        )
        contract_address = int(account_to_deploy["address"], 16)

        if dry_run:
            return tx, contract_address

        assert account_to_deploy["deployed"] is False, (
            f"Account '{self.account_name}' for network '{self.starknet_context.network_id}' "
            "is already deployed."
        )
        account_to_deploy["deployed"] = True
        os.makedirs(name=os.path.dirname(self.account_file), exist_ok=True)
        with open(self.account_file, "w") as f:
            json.dump(accounts, f, indent=4)
            f.write("\n")

        return tx, contract_address

    def _get_deployed_account_info(self) -> JsonObject:
        assert os.path.exists(self.account_file), (
            f"The account file '{self.account_file}' was not found.\n"
            "Did you deploy your account contract (using 'starknet new_account' "
            "and 'starknet deploy_account')?"
        )

        accounts = self._get_accounts()
        account = self._get_account_given_accounts(accounts=accounts)
        assert account["deployed"], (
            f"Account '{self.account_name}' for network '{self.starknet_context.network_id}' "
            "is not deployed; use 'starknet deploy_account' command."
        )

        return account

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
        account_address, private_key = self._get_account_address_and_private_key(dry_run=dry_run)
        return sign_invoke_tx(
            signer_address=account_address,
            private_key=private_key,
            contract_address=contract_address,
            selector=selector,
            calldata=calldata,
            chain_id=chain_id,
            max_fee=max_fee,
            version=version,
            nonce=await nonce_callback(account_address),
        )

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
        account = self._get_deployed_account_info()
        account_address = int(account["address"], 16)
        deploy_from_zero_felt = 1 if deploy_from_zero else 0
        calldata = [
            class_hash,
            salt,
            len(constructor_calldata),
            *constructor_calldata,
            deploy_from_zero_felt,
        ]

        tx = await self.invoke(
            contract_address=account_address,
            selector=DEPLOY_CONTRACT_SELECTOR,
            calldata=calldata,
            chain_id=chain_id,
            max_fee=max_fee,
            version=version,
            nonce_callback=nonce_callback,
        )

        contract_address = calculate_contract_address_from_hash(
            salt=salt,
            class_hash=class_hash,
            constructor_calldata=constructor_calldata,
            deployer_address=0 if deploy_from_zero else account_address,
        )

        return tx, contract_address

    def _get_account_address_and_private_key(self, dry_run: bool) -> Tuple[int, Optional[int]]:
        account = self._get_deployed_account_info()
        account_address = int(account["address"], 16)

        private_key: Optional[int]
        if "private_key" in account:
            private_key = int(account["private_key"], 16)
        else:
            assert dry_run, f"Missing private_key for {hex(account_address)}."
            private_key = None

        return account_address, private_key


def sign_declare_tx(
    contract_class: ContractClass,
    private_key: Optional[int],
    sender_address: int,
    chain_id: int,
    max_fee: int,
    version: int,
    nonce: int,
) -> Declare:
    hash_value = calculate_declare_transaction_hash(
        contract_class=contract_class,
        chain_id=chain_id,
        sender_address=sender_address,
        max_fee=max_fee,
        version=version,
        nonce=nonce,
    )

    return Declare(
        contract_class=contract_class,
        sender_address=sender_address,
        max_fee=max_fee,
        signature=(
            [] if private_key is None else list(sign(msg_hash=hash_value, priv_key=private_key))
        ),
        nonce=nonce,
        version=version,
    )


def sign_invoke_tx(
    signer_address: int,
    private_key: Optional[int],
    contract_address: int,
    selector: int,
    calldata: List[int],
    chain_id: int,
    max_fee: int,
    version: int,
    nonce: int,
) -> InvokeFunction:
    """
    Given a function to invoke (contract address, selector, calldata) and account identifiers
    (signer address, private key) prepares and signs an OpenZeppelin account invocation to this
    function.
    """
    data_offset = 0
    data_len = len(calldata)
    call_entry = [contract_address, selector, data_offset, data_len]
    call_array_len = 1
    wrapped_method_calldata = [call_array_len, *call_entry, len(calldata), *calldata]

    hash_value = calculate_transaction_hash_common(
        tx_hash_prefix=TransactionHashPrefix.INVOKE,
        version=version,
        contract_address=signer_address,
        entry_point_selector=0,
        calldata=wrapped_method_calldata,
        max_fee=max_fee,
        chain_id=chain_id,
        additional_data=[nonce],
    )

    return InvokeFunction(
        contract_address=signer_address,
        calldata=wrapped_method_calldata,
        max_fee=max_fee,
        nonce=nonce,
        signature=(
            [] if private_key is None else list(sign(msg_hash=hash_value, priv_key=private_key))
        ),
        version=version,
    )


def sign_deploy_account_tx(
    private_key: Optional[int],
    public_key: int,
    class_hash: int,
    salt: int,
    max_fee: int,
    version: int,
    chain_id: int,
    nonce: int = 0,
) -> DeployAccount:
    contract_address = calculate_contract_address_from_hash(
        salt=salt,
        class_hash=class_hash,
        constructor_calldata=[public_key],
        deployer_address=0,
    )
    hash_value = calculate_deploy_account_transaction_hash(
        contract_address=contract_address,
        class_hash=class_hash,
        constructor_calldata=[public_key],
        salt=salt,
        max_fee=max_fee,
        version=version,
        chain_id=chain_id,
        nonce=nonce,
    )

    return DeployAccount(
        class_hash=class_hash,
        constructor_calldata=[public_key],
        contract_address_salt=salt,
        max_fee=max_fee,
        nonce=nonce,
        signature=(
            [] if private_key is None else list(sign(msg_hash=hash_value, priv_key=private_key))
        ),
        version=version,
    )
