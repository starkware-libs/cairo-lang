#!/usr/bin/env python3

import argparse
import asyncio
import dataclasses
import functools
import json
import math
import os
import sys
from typing import Any, Dict, List, Optional

from web3 import Web3

from services.everest.definitions import fields as everest_fields
from services.external_api.base_client import RetryConfig
from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt, TypePointer
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.parser import parse_type
from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.lang.compiler.type_system import mark_type_resolved
from starkware.cairo.lang.compiler.type_utils import check_felts_only_type
from starkware.cairo.lang.tracer.tracer_data import field_element_repr
from starkware.cairo.lang.version import __version__
from starkware.cairo.lang.vm.crypto import get_crypto_lib_context_manager
from starkware.python.utils import from_bytes
from starkware.starknet.cli.reconstruct_starknet_traceback import reconstruct_starknet_traceback
from starkware.starknet.definitions import constants, fields
from starkware.starknet.definitions.general_config import StarknetChainId
from starkware.starknet.public.abi import get_selector_from_name
from starkware.starknet.public.abi_structs import identifier_manager_from_abi
from starkware.starknet.services.api.contract_definition import ContractDefinition
from starkware.starknet.services.api.feeder_gateway.feeder_gateway_client import FeederGatewayClient
from starkware.starknet.services.api.gateway.gateway_client import GatewayClient
from starkware.starknet.services.api.gateway.transaction import Deploy, InvokeFunction
from starkware.starknet.utils.api_utils import cast_to_felts
from starkware.starknet.wallets.account import DEFAULT_ACCOUNT_DIR, Account
from starkware.starknet.wallets.starknet_context import StarknetContext
from starkware.starkware_utils.error_handling import StarkErrorCode

NETWORKS = {
    "alpha-goerli": "alpha4.starknet.io",
    "alpha-mainnet": "alpha-mainnet.starknet.io",
}

CHAIN_IDS = {
    "alpha-goerli": StarknetChainId.TESTNET.value,
    "alpha-mainnet": StarknetChainId.MAINNET.value,
}

FEE_MARGIN_OF_ESTIMATION = 1.1


@dataclasses.dataclass
class InvokeFunctionArgs:
    address: int
    selector: int
    calldata: List[int]
    signature: List[int]


# Utilities.


def felt_formatter(hex_felt: str) -> str:
    return field_element_repr(val=int(hex_felt, 16), prime=everest_fields.FeltField.upper_bound)


def get_optional_arg_value(args, arg_name: str, environment_var: str) -> Optional[str]:
    """
    Returns the value of the given argument from args. If the argument was not specified, returns
    the value of the environment variable.
    """
    arg_value = getattr(args, arg_name)
    if arg_value is not None:
        return arg_value
    return os.environ.get(environment_var)


def get_arg_value(args, arg_name: str, environment_var: str) -> str:
    """
    Same as get_optional_arg_value, except that if the value is not defined, an exception is
    raised.
    """
    value = get_optional_arg_value(args=args, arg_name=arg_name, environment_var=environment_var)
    if value is None:
        raise Exception(
            f'{arg_name} must be specified with the "{args.command}" subcommand.\n'
            "Consider passing --network or setting the STARKNET_NETWORK environment variable."
        )
    return value


def get_chain_id(args) -> int:
    chain_id = get_arg_value(args=args, arg_name="chain_id", environment_var="STARKNET_CHAIN_ID")

    if chain_id.startswith("0x"):
        chain_id_int = int(chain_id, 16)
    else:
        chain_id_int = from_bytes(chain_id.encode())

    assert chain_id_int in CHAIN_IDS.values(), f"Unsupported chain ID: {chain_id}."
    return chain_id_int


def get_network_id(args) -> str:
    """
    Returns a textual identifier of the network. Used for account management.
    By default this is the same as the network name (one of the keys of NETWORKS).
    """
    return get_arg_value(args=args, arg_name="network_id", environment_var="STARKNET_NETWORK_ID")


def get_wallet_provider(args) -> Optional[str]:
    """
    Returns the name of the wallet provider (of the form "module.class") as defined by the user.
    """
    value = get_optional_arg_value(args=args, arg_name="wallet", environment_var="STARKNET_WALLET")
    if value == "":
        # An empty string means no wallet should be used (direct contract call).
        return None
    return value


def get_account_dir(args) -> str:
    """
    Returns the directory containing the wallet files. By default, DEFAULT_ACCOUNT_DIR is used.
    """
    value = get_optional_arg_value(
        args=args, arg_name="account_dir", environment_var="STARKNET_ACCOUNT_DIR"
    )
    if value is None:
        return DEFAULT_ACCOUNT_DIR
    return value


def get_gateway_client(args) -> GatewayClient:
    gateway_url = get_arg_value(
        args=args, arg_name="gateway_url", environment_var="STARKNET_GATEWAY_URL"
    )
    # Limit the number of retries.
    retry_config = RetryConfig(n_retries=1)
    return GatewayClient(url=gateway_url, retry_config=retry_config)


def get_feeder_gateway_client(args) -> FeederGatewayClient:
    feeder_gateway_url = get_arg_value(
        args=args, arg_name="feeder_gateway_url", environment_var="STARKNET_FEEDER_GATEWAY_URL"
    )
    # Limit the number of retries.
    retry_config = RetryConfig(n_retries=1)
    return FeederGatewayClient(url=feeder_gateway_url, retry_config=retry_config)


def get_starknet_context(args) -> StarknetContext:
    """
    Returns the StarknetContext object based on the CLI arguments.
    """
    return StarknetContext(
        network_id=get_network_id(args),
        account_dir=get_account_dir(args),
        gateway_client=get_gateway_client(args),
        feeder_gateway_client=get_feeder_gateway_client(args),
    )


def get_network(args) -> Optional[str]:
    """
    Returns the StarkNet network, if specified. The network should be one of the keys in the
    NETWORKS dictionary.
    """
    return os.environ.get("STARKNET_NETWORK") if args.network is None else args.network


def parse_address(addr_str: str) -> int:
    """
    Converts the given address (hex string, starting with "0x") to an integer.
    """
    addr_str = addr_str.strip()
    assert addr_str.startswith("0x"), f"The address must start with '0x'. Got: {addr_str}."
    try:
        return int(addr_str, 16)
    except ValueError:
        raise ValueError(f"Invalid address format: {addr_str}.")


def validate_arguments(
    inputs: List[int], abi_entry: Dict[str, Any], identifier_manager: IdentifierManager
):
    previous_felt_input = None
    current_inputs_ptr = 0
    for input_desc in abi_entry["inputs"]:
        typ = mark_type_resolved(parse_type(input_desc["type"]))
        typ_size = check_felts_only_type(cairo_type=typ, identifier_manager=identifier_manager)
        if typ_size is not None:
            assert current_inputs_ptr + typ_size <= len(inputs), (
                f"Expected at least {current_inputs_ptr + typ_size} inputs, " f"got {len(inputs)}."
            )

            current_inputs_ptr += typ_size
        elif isinstance(typ, TypePointer):
            typ_size = check_felts_only_type(
                cairo_type=typ.pointee, identifier_manager=identifier_manager
            )
            assert typ_size is not None, f"Type '{typ.format()}' is not supported."
            assert previous_felt_input is not None, (
                f'The array argument {input_desc["name"]} of type felt* must be preceded '
                "by a length argument of type felt."
            )

            current_inputs_ptr += previous_felt_input * typ_size
        else:
            raise Exception(f"Type {typ.format()} is not supported.")
        previous_felt_input = inputs[current_inputs_ptr - 1] if typ == TypeFelt() else None

    assert (
        len(inputs) == current_inputs_ptr
    ), f"Wrong number of arguments. Expected {current_inputs_ptr}, got {len(inputs)}."


async def load_account_from_args(args) -> Account:
    wallet = get_wallet_provider(args)
    assert wallet is not None, f'--wallet must be specified with the "{args.command}" subcommand.'
    return await load_account(
        starknet_context=get_starknet_context(args),
        wallet=wallet,
        account_name=args.account,
    )


async def load_account(
    starknet_context: StarknetContext, wallet: str, account_name: str
) -> Account:
    """
    Constructs an Account instance for the given account name.

    wallet: the name of the python module and class (module.class).
    """
    module_name, class_name = wallet.rsplit(".", maxsplit=1)

    # Load the module.
    try:
        module_classes = __import__(module_name, fromlist=[class_name])
    except ModuleNotFoundError as e:
        if e.name == module_name:
            raise Exception(
                f"Unable to find wallet '{wallet}': Module '{module_name}' was not found."
            ) from None
        else:
            # Raise the original exception.
            raise

    # Load the wallet class.
    try:
        account_class = getattr(module_classes, class_name)
    except AttributeError:
        raise Exception(
            f"Unable to find wallet '{wallet}': Class '{class_name}' was not found."
        ) from None

    return await account_class.create(starknet_context=starknet_context, account_name=account_name)


def handle_network_param(args):
    """
    Gives default values to the gateways if the network parameter is set.
    """
    network = get_network(args)
    if network is not None:
        if network not in NETWORKS:
            networks_str = ", ".join(NETWORKS.keys())
            print(
                f"Unknown network '{network}'. Supported networks: {networks_str}.",
                file=sys.stderr,
            )
            return 1

        dns = NETWORKS[network]
        if args.gateway_url is None:
            args.gateway_url = f"https://{dns}/gateway"

        if args.feeder_gateway_url is None:
            args.feeder_gateway_url = f"https://{dns}/feeder_gateway"

        if args.network_id is None:
            args.network_id = network

        if args.chain_id is None:
            args.chain_id = hex(CHAIN_IDS[network])

    return 0


def parse_invoke_tx_args(args: argparse.Namespace) -> InvokeFunctionArgs:
    """
    Parses the arguments and validates that the function name is in the abi.
    """
    inputs = cast_to_felts(values=args.inputs)

    abi = json.load(args.abi)
    for abi_entry in abi:
        if abi_entry["type"] == "function" and abi_entry["name"] == args.function:
            validate_arguments(
                inputs=inputs,
                abi_entry=abi_entry,
                identifier_manager=identifier_manager_from_abi(abi=abi),
            )
            break
    else:
        raise Exception(f"Function {args.function} not found.")

    return InvokeFunctionArgs(
        signature=cast_to_felts(values=args.signature),
        address=parse_address(args.address),
        selector=get_selector_from_name(args.function),
        calldata=inputs,
    )


async def create_invoke_tx(
    args: argparse.Namespace,
    invoke_tx_args: InvokeFunctionArgs,
    max_fee: int,
    has_wallet: bool,
    call: bool,
) -> InvokeFunction:
    """
    Creates and returns an InvokeFunction transaction with the given parameters.
    If a wallet provider was provided in args, that transaction will be wrapped and signed.
    """
    assert max_fee >= 0, f"The 'max_fee' argument, --max_fee, must be non-negative, got {max_fee}."

    version = constants.QUERY_VERSION if call else constants.TRANSACTION_VERSION
    if not has_wallet:
        assert args.nonce is None, "--nonce cannot be used in direct calls."
        return InvokeFunction(
            contract_address=invoke_tx_args.address,
            entry_point_selector=invoke_tx_args.selector,
            calldata=invoke_tx_args.calldata,
            max_fee=max_fee,
            version=version,
            signature=invoke_tx_args.signature,
        )

    account = await load_account_from_args(args=args)
    assert invoke_tx_args.signature == [], (
        "Signature cannot be passed explicitly when using an account contract. "
        "Consider making a direct contract call using --no_wallet."
    )
    wrapped_method = await account.sign_invoke_transaction(
        contract_address=invoke_tx_args.address,
        selector=invoke_tx_args.selector,
        calldata=invoke_tx_args.calldata,
        chain_id=get_chain_id(args),
        max_fee=max_fee,
        version=version,
        nonce=args.nonce,
    )
    return InvokeFunction(
        contract_address=wrapped_method.address,
        entry_point_selector=wrapped_method.selector,
        calldata=wrapped_method.calldata,
        max_fee=wrapped_method.max_fee,
        version=version,
        signature=wrapped_method.signature,
    )


async def estimate_fee_inner(
    args: argparse.Namespace,
    invoke_tx_args: InvokeFunctionArgs,
    has_wallet: bool,
    has_block_info: bool,
) -> Dict[str, Any]:
    """
    Estimates the fee of a transaction with the given parameters.
    Returns a response of the form:
        {"amount": <int>, "unit": "wei"}
    """
    invoke_tx = await create_invoke_tx(
        args=args, invoke_tx_args=invoke_tx_args, max_fee=0, has_wallet=has_wallet, call=True
    )
    feeder_client = get_feeder_gateway_client(args=args)
    return await feeder_client.estimate_fee(
        invoke_tx=invoke_tx,
        block_hash=args.block_hash if has_block_info else None,
        block_number=args.block_number if has_block_info else None,
    )


# Subparsers.


async def deploy(args, command_args):
    parser = argparse.ArgumentParser(description="Sends a deploy transaction to StarkNet.")
    parser.add_argument(
        "--salt",
        type=str,
        help=(
            "An optional salt controlling where the contract will be deployed. "
            "The contract deployment address is determined by the hash "
            "of contract, salt and caller. "
            "If the salt is not supplied, the contract will be deployed with a random salt."
        ),
    )
    parser.add_argument(
        "--inputs", type=str, nargs="*", default=[], help="The inputs to the constructor."
    )
    parser.add_argument(
        "--contract",
        type=argparse.FileType("r"),
        help="The contract definition to deploy.",
        required=True,
    )
    parser.add_argument(
        "--token", type=str, help="Used for deploying contracts in Alpha MainNet.", required=False
    )
    parser.parse_args(command_args, namespace=args)
    inputs = cast_to_felts(args.inputs)

    gateway_client = get_gateway_client(args)
    if args.salt is not None and not args.salt.startswith("0x"):
        raise ValueError(f"salt must start with '0x'. Got: {args.salt}.")

    try:
        salt = (
            fields.ContractAddressSalt.get_random_value()
            if args.salt is None
            else int(args.salt, 16)
        )
    except ValueError:
        raise ValueError("Invalid salt format.")

    contract_definition = ContractDefinition.loads(args.contract.read())
    abi = contract_definition.abi
    assert abi is not None, "Missing ABI in the given contract definition."

    for abi_entry in abi:
        if abi_entry["type"] == "constructor":
            validate_arguments(
                inputs=inputs,
                abi_entry=abi_entry,
                identifier_manager=identifier_manager_from_abi(abi=abi),
            )
            break
    else:
        assert len(inputs) == 0, "--inputs cannot be specified for contracts without a constructor."

    tx = Deploy(
        contract_address_salt=salt,
        contract_definition=contract_definition,
        constructor_calldata=inputs,
    )

    gateway_response = await gateway_client.add_transaction(tx=tx, token=args.token)
    contract_address = int(gateway_response["address"], 16)
    assert (
        gateway_response["code"] == StarkErrorCode.TRANSACTION_RECEIVED.name
    ), f"Failed to send transaction. Response: {gateway_response}."
    # Don't end sentences with '.', to allow easy double-click copy-pasting of the values.
    print(
        f"""\
Deploy transaction was sent.
Contract address: 0x{contract_address:064x}
Transaction hash: {gateway_response['transaction_hash']}"""
    )


async def deploy_account(args, command_args):
    parser = argparse.ArgumentParser(
        description="Initialize the account and deploy the account contract to StarkNet."
    )
    # Use parse_args to add the --help flag for the subcommand.
    parser.parse_args(command_args, namespace=args)
    account = await load_account_from_args(args)
    await account.deploy()


async def invoke_or_call(args: argparse.Namespace, command_args: List[str], call: bool):
    parser = argparse.ArgumentParser(description="Sends an invoke transaction to StarkNet.")
    add_invoke_tx_arguments(parser=parser, call=call)
    parser.add_argument(
        "--max_fee", type=int, help="The maximal fee to be paid for the function invocation."
    )

    parser.parse_args(command_args, namespace=args)

    invoke_tx_args = parse_invoke_tx_args(args=args)
    address = invoke_tx_args.address

    has_wallet = get_wallet_provider(args=args) is not None
    max_fee = args.max_fee
    if max_fee is None:
        if has_wallet:
            fee_info = await estimate_fee_inner(
                args=args, invoke_tx_args=invoke_tx_args, has_wallet=has_wallet, has_block_info=call
            )
            max_fee = math.ceil(fee_info["amount"] * FEE_MARGIN_OF_ESTIMATION)
            max_fee_eth = float(Web3.fromWei(max_fee, "ether"))

            print(f"Sending the transaction with max_fee: {max_fee_eth:.6f} ETH.")
        else:
            max_fee = 0

    tx = await create_invoke_tx(
        args=args, invoke_tx_args=invoke_tx_args, max_fee=max_fee, has_wallet=has_wallet, call=call
    )

    gateway_response: dict
    if call:
        feeder_client = get_feeder_gateway_client(args)
        gateway_response = await feeder_client.call_contract(
            invoke_tx=tx, block_hash=args.block_hash, block_number=args.block_number
        )
        print(*map(felt_formatter, gateway_response["result"]))
    else:
        gateway_client = get_gateway_client(args)
        gateway_response = await gateway_client.add_transaction(tx=tx)
        assert (
            gateway_response["code"] == StarkErrorCode.TRANSACTION_RECEIVED.name
        ), f"Failed to send transaction. Response: {gateway_response}."
        # Don't end sentences with '.', to allow easy double-click copy-pasting of the values.
        print(
            f"""\
Invoke transaction was sent.
Contract address: 0x{address:064x}
Transaction hash: {gateway_response['transaction_hash']}"""
        )


async def estimate_fee(args: argparse.Namespace, command_args: List[str]):
    parser = argparse.ArgumentParser(description="Estimates the fee of a transaction.")
    add_invoke_tx_arguments(parser=parser, call=True)

    parser.parse_args(command_args, namespace=args)
    invoke_tx_args = parse_invoke_tx_args(args=args)
    has_wallet = get_wallet_provider(args=args) is not None

    fee_info = await estimate_fee_inner(
        args=args, invoke_tx_args=invoke_tx_args, has_wallet=has_wallet, has_block_info=True
    )

    fee_wei = fee_info["amount"]
    fee_eth = float(Web3.fromWei(fee_wei, "ether"))
    print(f"The estimated fee is: {fee_wei} WEI ({fee_eth:.6f} ETH).")


async def tx_status(args, command_args):
    parser = argparse.ArgumentParser(
        description="Queries the status of a transaction given its ID."
    )
    parser.add_argument(
        "--hash", type=str, required=True, help="The hash of the transaction to query."
    )
    parser.add_argument(
        "--contracts",
        type=str,
        required=False,
        help=(
            "Optional paths to compiled contracts with debug information. "
            "If given, the contracts will be used to add location information to errors. "
            "Format: '<addr>:<path.json>,<addr2>:<path2.json>'. "
            "If '<addr>:' is omitted, the path refers to the original contract that was called "
            "(usually, the account contract)."
        ),
    )
    parser.add_argument(
        "--error_message", action="store_true", help="Only print the error message."
    )
    parser.parse_args(command_args, namespace=args)

    feeder_gateway_client = get_feeder_gateway_client(args)

    tx_status_response = await feeder_gateway_client.get_transaction_status(tx_hash=args.hash)

    # Print the error message with reconstructed location information in traceback, if necessary.
    has_error_message = (
        "tx_failure_reason" in tx_status_response
        and "error_message" in tx_status_response["tx_failure_reason"]
    )
    error_message = ""
    if has_error_message:
        error_message = tx_status_response["tx_failure_reason"]["error_message"]
        if args.contracts is not None:
            contracts: Dict[Optional[int], Program] = {}
            for addr_and_path in args.contracts.split(","):
                addr_and_path_split = addr_and_path.split(":")
                if len(addr_and_path_split) == 1:
                    addr, path = None, addr_and_path_split[0]
                else:
                    addr_str, path = addr_and_path_split
                    addr = parse_address(addr_str)
                contracts[addr] = Program.load(json.load(open(path.strip()))["program"])
            error_message = reconstruct_starknet_traceback(
                contracts=contracts, traceback_txt=error_message
            )
            tx_status_response["tx_failure_reason"]["error_message"] = error_message

    if args.error_message:
        print(error_message)
    else:
        print(json.dumps(tx_status_response, indent=4, sort_keys=True))


async def get_transaction(args, command_args):
    parser = argparse.ArgumentParser(
        description="Outputs the transaction information given its ID."
    )
    parser.add_argument(
        "--hash", type=str, required=True, help="The hash of the transaction to query."
    )
    parser.parse_args(command_args, namespace=args)

    feeder_gateway_client = get_feeder_gateway_client(args)

    tx_info = await feeder_gateway_client.get_transaction(tx_hash=args.hash)
    print(tx_info.dumps(indent=4, sort_keys=True))


async def get_transaction_trace(args, command_args):
    parser = argparse.ArgumentParser(description="Outputs the transaction trace given its ID.")
    parser.add_argument(
        "--hash", type=str, required=True, help="The hash of the transaction to query."
    )
    parser.parse_args(command_args, namespace=args)

    feeder_gateway_client = get_feeder_gateway_client(args)

    tx_trace = await feeder_gateway_client.get_transaction_trace(tx_hash=args.hash)
    print(tx_trace.dumps(indent=4, sort_keys=True))


async def get_transaction_receipt(args, command_args):
    parser = argparse.ArgumentParser(description="Outputs the transaction receipt given its ID.")
    parser.add_argument(
        "--hash", type=str, required=True, help="The hash of the transaction to query."
    )
    parser.parse_args(command_args, namespace=args)

    feeder_gateway_client = get_feeder_gateway_client(args)

    tx_receipt = await feeder_gateway_client.get_transaction_receipt(tx_hash=args.hash)
    print(tx_receipt.dumps(indent=4, sort_keys=True))


async def get_block(args, command_args):
    parser = argparse.ArgumentParser(
        description=(
            "Outputs the block corresponding to the given ID. "
            "In case no ID is given, outputs the latest block."
        )
    )
    add_block_identifier_arguments(
        parser=parser, block_role_description="display", with_block_prefix=False
    )

    parser.parse_args(command_args, namespace=args)

    feeder_gateway_client = get_feeder_gateway_client(args)

    block = await feeder_gateway_client.get_block(block_hash=args.hash, block_number=args.number)
    print(block.dumps(indent=4, sort_keys=True))


async def get_state_update(args, command_args):
    parser = argparse.ArgumentParser(description=("Outputs the state update of a given block"))
    add_block_identifier_arguments(
        parser=parser, block_role_description="display", with_block_prefix=True
    )

    parser.parse_args(command_args, namespace=args)
    feeder_gateway_client = get_feeder_gateway_client(args)

    block_state_updates = await feeder_gateway_client.get_state_update(
        block_hash=args.block_hash, block_number=args.block_number
    )
    print(json.dumps(block_state_updates, indent=4, sort_keys=True))


async def get_code(args, command_args):
    parser = argparse.ArgumentParser(
        description=(
            "Outputs the bytecode of the contract at the given address with respect to "
            "a specific block. In case no block ID is given, uses the latest block."
        )
    )
    parser.add_argument(
        "--contract_address", type=str, help="The address of the contract.", required=True
    )
    add_block_identifier_arguments(parser=parser, block_role_description="extract information from")

    parser.parse_args(command_args, namespace=args)

    feeder_gateway_client = get_feeder_gateway_client(args)

    code = await feeder_gateway_client.get_code(
        contract_address=int(args.contract_address, 16),
        block_hash=args.block_hash,
        block_number=args.block_number,
    )
    print(json.dumps(code, indent=4, sort_keys=True))


async def get_full_contract(args, command_args):
    parser = argparse.ArgumentParser(
        description=(
            "Outputs the contract definition of the contract at the given address with respect to "
            "a specific block. In case no block ID is given, uses the latest block."
        )
    )
    parser.add_argument(
        "--contract_address", type=str, help="The address of the contract.", required=True
    )
    add_block_identifier_arguments(parser=parser, block_role_description="extract information from")

    parser.parse_args(command_args, namespace=args)

    feeder_gateway_client = get_feeder_gateway_client(args)

    contract_definition = await feeder_gateway_client.get_full_contract(
        contract_address=int(args.contract_address, 16),
        block_hash=args.block_hash,
        block_number=args.block_number,
    )
    print(json.dumps(contract_definition, indent=4, sort_keys=True))


async def get_contract_addresses(args, command_args):
    argparse.ArgumentParser(description="Outputs the addresses of the StarkNet system contracts.")

    feeder_gateway_client = get_feeder_gateway_client(args)
    contract_addresses = await feeder_gateway_client.get_contract_addresses()
    print(json.dumps(contract_addresses, indent=4, sort_keys=True))


async def get_storage_at(args, command_args):
    parser = argparse.ArgumentParser(
        description=(
            "Outputs the storage value of a contract in a specific key with respect to "
            "a specific block. In case no block ID is given, uses the latest block."
        )
    )
    parser.add_argument(
        "--contract_address", type=str, help="The address of the contract.", required=True
    )
    parser.add_argument(
        "--key", type=int, help="The position in the contract's storage.", required=True
    )
    add_block_identifier_arguments(parser=parser, block_role_description="extract information from")

    parser.parse_args(command_args, namespace=args)

    feeder_gateway_client = get_feeder_gateway_client(args)

    print(
        await feeder_gateway_client.get_storage_at(
            contract_address=int(args.contract_address, 16),
            key=args.key,
            block_hash=args.block_hash,
            block_number=args.block_number,
        )
    )


# Add arguments.


def add_invoke_tx_arguments(parser: argparse.ArgumentParser, call: bool):
    """
    Adds the arguments: address, abi, function, inputs, nonce, signature.
    """
    parser.add_argument(
        "--address", type=str, required=True, help="The address of the invoked contract."
    )
    parser.add_argument(
        "--abi", type=argparse.FileType("r"), required=True, help="The Cairo contract ABI."
    )
    parser.add_argument(
        "--function", type=str, required=True, help="The name of the invoked function."
    )
    parser.add_argument(
        "--inputs", type=str, nargs="*", default=[], help="The inputs to the invoked function."
    )
    parser.add_argument(
        "--nonce",
        type=int,
        help=(
            "Allows to explicitly specify the transaction nonce. "
            "If not specified, the current nonce of the account contract "
            "(as returned from StarkNet) will be used."
        ),
    )
    parser.add_argument(
        "--signature",
        type=str,
        nargs="*",
        default=[],
        help="The signature information for the invoked function.",
    )

    if call:
        add_block_identifier_arguments(
            parser=parser, block_role_description="be used as the context for the call operation"
        )


def add_block_identifier_arguments(
    parser: argparse.ArgumentParser, block_role_description: str, with_block_prefix: bool = True
):
    identifier_prefix = "block_" if with_block_prefix else ""
    parser.add_argument(
        f"--{identifier_prefix}hash",
        type=str,
        help=(
            f"The hash of the block to {block_role_description}. "
            "In case this argument and block_number are not given, uses the latest block."
        ),
    )
    parser.add_argument(
        f"--{identifier_prefix}number",
        help=(
            f"The number of the block to {block_role_description}; "
            "Additional supported keywords: 'pending';"
            "In case this argument and block_hash are not given, uses the latest block."
        ),
    )


async def main():
    subparsers = {
        "call": functools.partial(invoke_or_call, call=True),
        "deploy": deploy,
        "deploy_account": deploy_account,
        "estimate_fee": estimate_fee,
        "get_block": get_block,
        "get_state_update": get_state_update,
        "get_code": get_code,
        "get_contract_addresses": get_contract_addresses,
        "get_full_contract": get_full_contract,
        "get_storage_at": get_storage_at,
        "get_transaction": get_transaction,
        "get_transaction_receipt": get_transaction_receipt,
        "get_transaction_trace": get_transaction_trace,
        "invoke": functools.partial(invoke_or_call, call=False),
        "tx_status": tx_status,
    }
    parser = argparse.ArgumentParser(description="A tool to communicate with StarkNet.")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--network", type=str, help="The name of the StarkNet network.")
    parser.add_argument(
        "--network_id",
        type=str,
        help="A textual identifier of the network. Used for account management.",
    )
    parser.add_argument(
        "--chain_id",
        type=str,
        help="The chain id (either as a hex number or as a string).",
    )
    parser.add_argument(
        "--wallet",
        type=str,
        help="The name of the wallet, including the python module and wallet class.",
    )
    parser.add_argument(
        "--no_wallet",
        dest="wallet",
        action="store_const",
        # Set wallet explicitly to an empty string, rather than None, to override the
        # environment variables.
        const="",
        help="Perform a direct contract call without an account contract.",
    )
    parser.add_argument(
        "--account",
        type=str,
        default="__default__",
        help=(
            "The name of the account. If not given, the default account "
            "(as defined by the wallet) is used."
        ),
    )
    parser.add_argument(
        "--account_dir",
        type=str,
        help=f"The directory containing the account files (default: '{DEFAULT_ACCOUNT_DIR}').",
    )
    parser.add_argument(
        "--flavor",
        type=str,
        choices=["Debug", "Release", "RelWithDebInfo"],
        help="Build flavor.",
    )

    parser.add_argument("--gateway_url", type=str, help="The URL of a StarkNet gateway.")
    parser.add_argument(
        "--feeder_gateway_url", type=str, help="The URL of a StarkNet feeder gateway."
    )
    parser.add_argument("command", choices=subparsers.keys())

    args, unknown = parser.parse_known_args()

    ret = handle_network_param(args)
    if ret != 0:
        return ret

    try:
        with get_crypto_lib_context_manager(args.flavor):
            # Invoke the requested command.
            return await subparsers[args.command](args, unknown)
    except Exception as exc:
        print(f"Error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    asyncio.run(main())
