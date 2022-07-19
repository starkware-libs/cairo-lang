import json
import os
import shutil
from typing import List, Optional, Tuple

from services.external_api.client import JsonObject
from starkware.crypto.signature.signature import get_random_private_key, private_to_stark_key, sign
from starkware.starknet.core.os.contract_address.contract_address import (
    calculate_contract_address_from_hash,
)
from starkware.starknet.core.os.transaction_hash.transaction_hash import (
    TransactionHashPrefix,
    calculate_transaction_hash_common,
)
from starkware.starknet.definitions import constants, fields
from starkware.starknet.public.abi import EXECUTE_ENTRY_POINT_SELECTOR, get_selector_from_name
from starkware.starknet.services.api.feeder_gateway.response_objects import PENDING_BLOCK_ID
from starkware.starknet.services.api.gateway.transaction import Deploy, InvokeFunction
from starkware.starknet.third_party.open_zeppelin.starknet_contracts import account_contract
from starkware.starknet.wallets.account import Account, WrappedMethod
from starkware.starknet.wallets.starknet_context import StarknetContext
from starkware.starkware_utils.error_handling import StarkErrorCode

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
    async def create(
        cls, starknet_context: StarknetContext, account_name: str
    ) -> "OpenZeppelinAccount":
        return cls(starknet_context=starknet_context, account_name=account_name)

    @property
    def account_file(self):
        return os.path.join(
            os.path.expanduser(self.starknet_context.account_dir), ACCOUNT_FILE_NAME
        )

    async def deploy(self):
        # Read the account file.
        if os.path.exists(self.account_file):
            # Make a backup of the file.
            shutil.copy(self.account_file, self.account_file + ".backup")
            accounts = json.load(open(self.account_file))
        else:
            accounts = {}

        accounts_for_network = accounts.setdefault(self.starknet_context.network_id, {})

        assert self.account_name not in accounts_for_network, (
            f"Account '{self.account_name}' for network '{self.starknet_context.network_id}' "
            "already exists."
        )

        private_key = get_random_private_key()
        public_key = private_to_stark_key(private_key)

        # Deploy the contract.
        salt = fields.ContractAddressSalt.get_random_value()

        tx = Deploy(
            contract_address_salt=salt,
            contract_definition=account_contract,
            constructor_calldata=[public_key],
            version=constants.TRANSACTION_VERSION,
        )

        gateway_response = await self.starknet_context.gateway_client.add_transaction(tx=tx)
        assert (
            gateway_response["code"] == StarkErrorCode.TRANSACTION_RECEIVED.name
        ), f"Failed to send deploy transaction. Response: {gateway_response}."
        contract_address = int(gateway_response["address"], 16)

        accounts_for_network[self.account_name] = {
            "private_key": hex(private_key),
            "public_key": hex(public_key),
            "address": hex(contract_address),
        }

        # Don't end sentences with '.', to allow easy double-click copy-pasting of the values.
        print(
            f"""\
Sent deploy account contract transaction.

NOTE: This is a modified version of the OpenZeppelin account contract. The signature is computed
differently.

Contract address: 0x{contract_address:064x}
Public key: 0x{public_key:064x}
Transaction hash: {gateway_response['transaction_hash']}
"""
        )
        os.makedirs(name=os.path.dirname(self.account_file), exist_ok=True)
        with open(self.account_file, "w") as f:
            json.dump(accounts, f, indent=4)
            f.write("\n")

    def get_account_information(self) -> JsonObject:
        assert os.path.exists(self.account_file), (
            f"The account file '{self.account_file}' was not found.\n"
            "Did you deploy your account contract (using 'starnet deploy_account')?"
        )

        accounts = json.load(open(self.account_file))
        accounts_for_network = accounts.get(self.starknet_context.network_id, {})
        if self.account_name not in accounts_for_network:
            raise AccountNotFoundException(
                f"Account '{self.account_name}' for network '{self.starknet_context.network_id}' "
                "was not found."
            )
        return accounts_for_network[self.account_name]

    async def sign_invoke_transaction(
        self,
        contract_address: int,
        selector: int,
        calldata: List[int],
        chain_id: int,
        max_fee: Optional[int],
        version: int,
        nonce: Optional[int],
        dry_run: bool = False,
    ) -> WrappedMethod:
        account = self.get_account_information()
        account_address = int(account["address"], 16)

        private_key: Optional[int]
        if "private_key" in account:
            private_key = int(account["private_key"], 16)
        else:
            assert dry_run, f"Missing private_key for {hex(account_address)}."
            private_key = None

        if nonce is None:
            # Obtain the current nonce. Note that you can't invoke a function again before the
            # previous transaction was accepted.
            nonce = await self.get_current_nonce(account_address=account_address)

        return sign_invoke_transaction(
            signer_address=account_address,
            private_key=private_key,
            contract_address=contract_address,
            selector=selector,
            calldata=calldata,
            chain_id=chain_id,
            max_fee=max_fee,
            version=version,
            nonce=nonce,
        )

    async def deploy_contract(
        self,
        class_hash: int,
        salt: int,
        constructor_calldata: List[int],
        deploy_from_zero: bool,
        chain_id: int,
        max_fee: Optional[int],
        version: int,
        nonce: Optional[int],
    ) -> Tuple[WrappedMethod, int]:
        account = self.get_account_information()
        account_address = int(account["address"], 16)
        deploy_from_zero_felt = 1 if deploy_from_zero else 0
        calldata = [
            class_hash,
            salt,
            len(constructor_calldata),
            *constructor_calldata,
            deploy_from_zero_felt,
        ]

        wrapped_invocation = await self.sign_invoke_transaction(
            contract_address=account_address,
            selector=DEPLOY_CONTRACT_SELECTOR,
            calldata=calldata,
            chain_id=chain_id,
            max_fee=max_fee,
            version=version,
            nonce=nonce,
        )
        contract_address = calculate_contract_address_from_hash(
            salt=salt,
            class_hash=class_hash,
            constructor_calldata=constructor_calldata,
            deployer_address=0 if deploy_from_zero else account_address,
        )
        return wrapped_invocation, contract_address

    async def get_current_nonce(self, account_address: int) -> int:
        get_nonce_tx = InvokeFunction(
            contract_address=account_address,
            entry_point_selector=GET_NONCE_SELECTOR,
            calldata=[],
            max_fee=0,
            version=constants.QUERY_VERSION,
            signature=[],
        )
        res = await self.starknet_context.feeder_gateway_client.call_contract(
            invoke_tx=get_nonce_tx, block_hash=None, block_number=PENDING_BLOCK_ID
        )
        (nonce_hex,) = res["result"]
        return int(nonce_hex, 16)


def sign_invoke_transaction(
    signer_address: int,
    private_key: Optional[int],
    contract_address: int,
    selector: int,
    calldata: List[int],
    chain_id: int,
    max_fee: Optional[int],
    version: int,
    nonce: int,
) -> WrappedMethod:
    """
    Calculates the transaction's hash and then computes the signature using the private key.
    Returns a WrappedMethod with the signature of the sender.
    """
    data_offset = 0
    data_len = len(calldata)
    call_entry = [contract_address, selector, data_offset, data_len]
    call_array_len = 1
    wrapped_method_calldata = [call_array_len, *call_entry, len(calldata), *calldata, nonce]
    max_fee = 0 if max_fee is None else max_fee
    hash_value = calculate_transaction_hash_common(
        tx_hash_prefix=TransactionHashPrefix.INVOKE,
        version=version,
        contract_address=signer_address,
        entry_point_selector=EXECUTE_ENTRY_POINT_SELECTOR,
        calldata=wrapped_method_calldata,
        max_fee=max_fee,
        chain_id=chain_id,
        additional_data=[],
    )
    if private_key is None:
        signature = []
    else:
        signature = list(sign(msg_hash=hash_value, priv_key=private_key))
    return WrappedMethod(
        address=signer_address,
        selector=EXECUTE_ENTRY_POINT_SELECTOR,
        calldata=wrapped_method_calldata,
        max_fee=max_fee,
        signature=signature,
    )
