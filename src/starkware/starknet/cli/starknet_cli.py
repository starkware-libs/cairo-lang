#!/usr/bin/env python3

import argparse
import asyncio
import dataclasses
import functools
import json
import math
import os
import sys
import traceback
from typing import Any, Dict, List, Optional, Tuple

from web3 import Web3

from services.everest.definitions import fields as everest_fields
from services.external_api.client import RetryConfig
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
from starkware.starknet.definitions.general_config import StarknetChainId, StarknetGeneralConfig
from starkware.starknet.public.abi import get_selector_from_name
from starkware.starknet.public.abi_structs import identifier_manager_from_abi
from starkware.starknet.services.api.contract_class import ContractClass
from starkware.starknet.services.api.feeder_gateway.feeder_gateway_client import (
    CastableToHash,
    FeederGatewayClient,
)
from starkware.starknet.services.api.feeder_gateway.response_objects import (
    LATEST_BLOCK_ID,
    PENDING_BLOCK_ID,
    BlockIdentifier,
)
from starkware.starknet.services.api.gateway.gateway_client import GatewayClient
from starkware.starknet.services.api.gateway.transaction import (
    DECLARE_SENDER_ADDRESS,
    Declare,
    Deploy,
    InvokeFunction,
    Transaction,
)
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

ABI_TYPE_NOT_FOUND_ERROR = "An ABI entry is missing a 'type' entry."
ABI_TYPE_NOT_SUPPORTED_ERROR_FORMAT = "Type '{typ}' is not supported."


class AbiFormatError(Exception):
    """
    A wrapper for ABI format errors.
    """


@dataclasses.dataclass
class InvokeFunctionArgs:
    address: int
    selector: int
    calldata: List[int]
    signature: List[int]


# Utilities.


def parse_block_identifiers(
    block_hash: Optional[CastableToHash],
    block_number: Optional[BlockIdentifier],
    default_block_number: Optional[BlockIdentifier] = None,
) -> Tuple[Optional[CastableToHash], Optional[BlockIdentifier]]:
    """
    In most cases, returns the input as given.
    If no block identifiers were given, set the value default_block_number instead of block_number.
    If the value for default_block_number is not provided - it defaults to "pending".
    """
    default_block_number = (
        PENDING_BLOCK_ID if default_block_number is None else default_block_number
    )
    if block_hash is None and block_number is None:
        return block_hash, default_block_number

    return block_hash, block_number


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
    assert value is not None, (
        "A wallet must be specified (using --wallet or the STARKNET_WALLET environment variable), "
        "unless specifically using --no_wallet."
    )

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


def parse_hex_arg(arg: str, arg_name: str) -> int:
    """
    Converts the given argument (hex string, starting with "0x") to an integer.
    """
    arg = arg.strip()
    assert arg.startswith("0x"), f"{arg_name} must start with '0x'. Got: '{arg}'."
    try:
        return int(arg, 16)
    except ValueError:
        raise ValueError(f"Invalid {arg_name} format: '{arg}'.")


def get_salt(salt: Optional[str]) -> int:
    """
    Validates the given salt and returns it as an integer.
    If salt is None, returns a random salt.
    """
    if salt is None:
        return fields.ContractAddressSalt.get_random_value()

    return parse_hex_arg(arg=salt, arg_name="salt")


async def compute_max_fee(
    args: argparse.Namespace, invoke_tx: InvokeFunction, is_account_contract_invocation: bool
) -> int:
    """
    Returns max_fee argument if passed, and estimates and returns the max fee otherwise.
    """
    if args.max_fee is not None:
        assert (
            args.max_fee >= 0
        ), f"The 'max_fee' argument, --max_fee, must be non-negative, got {args.max_fee}."
        return args.max_fee

    if is_account_contract_invocation:
        fee_info = await estimate_fee_inner(
            args=args,
            invoke_tx=invoke_tx,
            has_block_info=False,
        )
        max_fee = math.ceil(fee_info["overall_fee"] * FEE_MARGIN_OF_ESTIMATION)
        max_fee_eth = float(Web3.fromWei(max_fee, "ether"))

        print(f"Sending the transaction with max_fee: {max_fee_eth:.6f} ETH.")
    else:
        max_fee = 0

    return max_fee


def validate_arguments(
    inputs: List[int], abi_entry: Dict[str, Any], identifier_manager: IdentifierManager
):
    """
    Validates the arguments of an ABI entry of type 'function' or 'constructor'.
    """
    function_name = abi_entry["name"] if abi_entry["type"] == "function" else "constructor"
    previous_felt_input = None
    current_inputs_ptr = 0
    for input_desc in abi_entry["inputs"]:
        # ABI input entry validations.
        if "type" not in input_desc or "name" not in input_desc:
            raise AbiFormatError(
                f"An input in the 'inputs' entry of '{function_name}' is missing either "
                "the 'type' or the 'name' entry."
            )

        try:
            typ = mark_type_resolved(parse_type(input_desc["type"]))
            typ_size = check_felts_only_type(cairo_type=typ, identifier_manager=identifier_manager)
        except Exception as ex:
            raise AbiFormatError(ex) from ex

        if typ_size is not None:
            assert current_inputs_ptr + typ_size <= len(
                inputs
            ), f"Expected at least {current_inputs_ptr + typ_size} inputs, got {len(inputs)}."

            current_inputs_ptr += typ_size
        elif isinstance(typ, TypePointer):
            try:
                typ_size = check_felts_only_type(
                    cairo_type=typ.pointee, identifier_manager=identifier_manager
                )
            except Exception as ex:
                raise AbiFormatError(ex) from ex

            if typ_size is None:
                raise AbiFormatError(ABI_TYPE_NOT_SUPPORTED_ERROR_FORMAT.format(typ=typ.format()))
            assert previous_felt_input is not None, (
                f"The array argument {input_desc['name']} of type felt* must be preceded "
                "by a length argument of type felt."
            )

            current_inputs_ptr += previous_felt_input * typ_size
        else:
            raise AbiFormatError(ABI_TYPE_NOT_SUPPORTED_ERROR_FORMAT.format(typ=typ.format()))
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
    try:
        module_name, class_name = wallet.rsplit(".", maxsplit=1)
    except ValueError:
        raise Exception(
            f"Unable to find wallet '{wallet}': Wrong wallet format; expected module.class format."
        ) from None

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
    try:
        abi = json.load(args.abi)
    except Exception as ex:
        raise AbiFormatError(ex) from ex

    for abi_entry in abi:
        # ABI entry validation.
        if "type" not in abi_entry:
            raise AbiFormatError(ABI_TYPE_NOT_FOUND_ERROR)

        if abi_entry["type"] == "function":
            # ABI function entry validation.
            # Note that not all ABI entries contain the 'name' entry, e.g., a constructor entry.
            if "name" not in abi_entry:
                raise AbiFormatError("An ABI entry of type 'function' is missing a 'name' entry.")

            if abi_entry["name"] == args.function:
                validate_arguments(
                    inputs=inputs,
                    abi_entry=abi_entry,
                    identifier_manager=identifier_manager_from_abi(abi=abi),
                )
                break
    else:
        raise AbiFormatError(f"Function '{args.function}' not found.")

    return InvokeFunctionArgs(
        signature=cast_to_felts(values=args.signature),
        address=parse_hex_arg(arg=args.address, arg_name="address"),
        selector=get_selector_from_name(args.function),
        calldata=inputs,
    )


async def create_invoke_tx_for_deploy(
    args: argparse.Namespace,
    salt: int,
    class_hash: int,
    constructor_calldata: List[int],
    max_fee: int,
    call: bool,
) -> Tuple[InvokeFunction, int]:
    """
    Creates and returns an InvokeFunction transaction to deploy a contract with the given arguments,
    which is wrapped and signed by the wallet provider.
    """
    version = constants.QUERY_VERSION if call else constants.TRANSACTION_VERSION
    account = await load_account_from_args(args=args)
    wrapped_method, contract_address = await account.deploy_contract(
        class_hash=class_hash,
        salt=salt,
        constructor_calldata=constructor_calldata,
        deploy_from_zero=args.deploy_from_zero,
        chain_id=get_chain_id(args),
        max_fee=max_fee,
        version=version,
        nonce=args.nonce,
    )
    tx = InvokeFunction(
        contract_address=wrapped_method.address,
        entry_point_selector=wrapped_method.selector,
        calldata=wrapped_method.calldata,
        max_fee=wrapped_method.max_fee,
        version=version,
        signature=wrapped_method.signature,
    )
    return tx, contract_address


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
        dry_run=args.dry_run,
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
    invoke_tx: InvokeFunction,
    has_block_info: bool,
) -> Dict[str, Any]:
    """
    Estimates the fee of a transaction with the given parameters.
    Returns a response of the form:
        {"amount": <int>, "unit": "wei"}
    """
    feeder_client = get_feeder_gateway_client(args=args)
    return await feeder_client.estimate_fee(
        invoke_tx=invoke_tx,
        block_hash=args.block_hash if has_block_info else None,
        block_number=args.block_number if has_block_info else PENDING_BLOCK_ID,
    )


def assert_tx_received(gateway_response: Dict[str, str]):
    assert (
        gateway_response["code"] == StarkErrorCode.TRANSACTION_RECEIVED.name
    ), f"Failed to send transaction. Response: {gateway_response}."


# Subparsers.


async def declare(args, command_args):
    parser = argparse.ArgumentParser(description="Sends a declare transaction to StarkNet.")
    add_declare_tx_arguments(parser=parser)
    parser.parse_args(command_args, namespace=args)
    assert args.sender == DECLARE_SENDER_ADDRESS, f"--sender must be {DECLARE_SENDER_ADDRESS}."
    assert args.max_fee == 0, "--max_fee must be 0."
    assert args.nonce == 0, "--nonce must be 0."

    tx = Declare(
        contract_class=ContractClass.loads(data=args.contract.read()),
        sender_address=args.sender,
        max_fee=args.max_fee,
        version=constants.TRANSACTION_VERSION,
        signature=args.signature,
        nonce=args.nonce,
    )

    gateway_client = get_gateway_client(args)
    gateway_response = await gateway_client.add_transaction(tx=tx, token=args.token)
    assert_tx_received(gateway_response=gateway_response)
    # Don't end sentences with '.', to allow easy double-click copy-pasting of the values.
    print(
        f"""\
Declare transaction was sent.
Contract class hash: {gateway_response['class_hash']}
Transaction hash: {gateway_response['transaction_hash']}"""
    )


async def deploy(args, command_args):
    parser = argparse.ArgumentParser(description="Deploys a contract to StarkNet.")
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
        "--token", type=str, help="Used for deploying contracts in Alpha MainNet.", required=False
    )
    parser.add_argument("--class_hash", type=str, help="The class hash of the deployed contract.")
    parser.add_argument(
        "--nonce",
        type=int,
        help=(
            "Used for explicitly specifying the transaction nonce. "
            "If not specified, the current nonce of the account contract "
            "(as returned from StarkNet) will be used."
        ),
    )
    parser.add_argument(
        "--max_fee", type=int, help="The maximal fee to be paid for the deployment."
    )
    parser.add_argument(
        "--contract", type=argparse.FileType("r"), help="The contract class to deploy."
    )
    parser.add_argument(
        "--deploy_from_zero",
        action="store_true",
        help="Use 0 instead of the deployer address for the contract address computation.",
    )
    parser.parse_args(command_args, namespace=args)

    has_wallet = get_wallet_provider(args=args) is not None
    if has_wallet:
        assert args.contract is None, (
            "--contract should not be passed when deploying a contract while using a wallet. "
            "Try passing --class_hash instead or using the --no_wallet flag."
        )
        assert (
            args.class_hash is not None
        ), "--class_hash must be passed when deploying a contract while using a wallet."
        await deploy_with_invoke(args=args)
    else:
        assert (
            args.contract is not None
        ), "--contract must be passed when deploying a contract without using a wallet."
        assert (
            args.class_hash is None
        ), "--class_hash should not be passed when deploying a contract without using a wallet."
        await deploy_tx(args=args)


async def deploy_tx(args):
    inputs = cast_to_felts(args.inputs)
    salt = get_salt(salt=args.salt)

    contract_class = ContractClass.loads(data=args.contract.read())
    abi = contract_class.abi
    assert abi is not None, "Missing ABI in the given contract class."

    for abi_entry in abi:
        # ABI entry validation.
        if "type" not in abi_entry:
            raise AbiFormatError(ABI_TYPE_NOT_FOUND_ERROR)

        if abi_entry["type"] == "constructor":
            try:
                validate_arguments(
                    inputs=inputs,
                    abi_entry=abi_entry,
                    identifier_manager=identifier_manager_from_abi(abi=abi),
                )
                break
            except AbiFormatError as abi_error:
                raise AbiFormatError(f"Failed to parse the contract ABI: {abi_error}")
    else:
        assert len(inputs) == 0, "--inputs cannot be specified for contracts without a constructor."

    tx = Deploy(
        contract_address_salt=salt,
        contract_definition=contract_class,
        constructor_calldata=inputs,
        version=constants.TRANSACTION_VERSION,
    )

    gateway_client = get_gateway_client(args)
    gateway_response = await gateway_client.add_transaction(tx=tx, token=args.token)
    assert_tx_received(gateway_response=gateway_response)
    contract_address = int(gateway_response["address"], 16)
    # Don't end sentences with '.', to allow easy double-click copy-pasting of the values.
    print(
        f"""\
Deploy transaction was sent.
Contract address: 0x{contract_address:064x}
Transaction hash: {gateway_response['transaction_hash']}"""
    )


async def deploy_with_invoke(args: argparse.Namespace):
    salt = get_salt(salt=args.salt)
    class_hash = parse_hex_arg(arg=args.class_hash, arg_name="class_hash")
    constructor_calldata = cast_to_felts(values=args.inputs)
    invoke_tx, _ = await create_invoke_tx_for_deploy(
        args=args,
        salt=salt,
        class_hash=class_hash,
        constructor_calldata=constructor_calldata,
        max_fee=0,
        call=True,
    )
    max_fee = await compute_max_fee(
        args=args, invoke_tx=invoke_tx, is_account_contract_invocation=True
    )
    tx, contract_address = await create_invoke_tx_for_deploy(
        args=args,
        salt=salt,
        class_hash=class_hash,
        constructor_calldata=constructor_calldata,
        max_fee=max_fee,
        call=False,
    )

    gateway_client = get_gateway_client(args)
    gateway_response = await gateway_client.add_transaction(tx=tx)
    assert_tx_received(gateway_response=gateway_response)
    # Don't end sentences with '.', to allow easy double-click copy-pasting of the values.
    print(
        f"""\
Invoke transaction for contract deployment was sent.
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

    has_wallet = get_wallet_provider(args=args) is not None
    is_account_contract_invocation = has_wallet and not call
    if args.dry_run:
        assert (
            is_account_contract_invocation
        ), "--dry_run can only be used for account contract invoke."
    invoke_tx = await create_invoke_tx(
        args=args, invoke_tx_args=invoke_tx_args, max_fee=0, has_wallet=has_wallet, call=True
    )
    max_fee = await compute_max_fee(
        args=args,
        invoke_tx=invoke_tx,
        is_account_contract_invocation=is_account_contract_invocation,
    )
    tx = await create_invoke_tx(
        args=args, invoke_tx_args=invoke_tx_args, max_fee=max_fee, has_wallet=has_wallet, call=call
    )

    gateway_response: dict
    if call:
        args.block_hash, args.block_number = parse_block_identifiers(
            args.block_hash, args.block_number
        )

        feeder_client = get_feeder_gateway_client(args)
        gateway_response = await feeder_client.call_contract(
            invoke_tx=tx, block_hash=args.block_hash, block_number=args.block_number
        )
        print(*map(felt_formatter, gateway_response["result"]))
    else:
        if not args.dry_run:
            gateway_client = get_gateway_client(args)
            gateway_response = await gateway_client.add_transaction(tx=tx)
            assert_tx_received(gateway_response=gateway_response)
            # Don't end sentences with '.', to allow easy double-click copy-pasting of the values.
            print(
                f"""\
Invoke transaction was sent.
Contract address: 0x{invoke_tx_args.address:064x}
Transaction hash: {gateway_response['transaction_hash']}"""
            )
        else:
            print_invoke_tx(tx=tx, chain_id=get_chain_id(args))


def print_invoke_tx(tx: InvokeFunction, chain_id: int):
    sn_config_dict = StarknetGeneralConfig().dump()
    sn_config_dict["starknet_os_config"]["chain_id"] = StarknetChainId(chain_id).name
    sn_config = StarknetGeneralConfig.load(sn_config_dict)
    tx_hash = tx.calculate_hash(sn_config)
    out_dict = {
        "transaction": Transaction.Schema().dump(obj=tx),
        "transaction_hash": hex(tx_hash),
    }
    print(json.dumps(out_dict, indent=4))


async def estimate_fee(args: argparse.Namespace, command_args: List[str]):
    parser = argparse.ArgumentParser(description="Estimates the fee of a transaction.")
    add_invoke_tx_arguments(parser=parser, call=True)

    parser.parse_args(command_args, namespace=args)
    invoke_tx_args = parse_invoke_tx_args(args=args)
    has_wallet = get_wallet_provider(args=args) is not None
    invoke_tx = await create_invoke_tx(
        args=args, invoke_tx_args=invoke_tx_args, max_fee=0, has_wallet=has_wallet, call=True
    )
    fee_info = await estimate_fee_inner(args=args, invoke_tx=invoke_tx, has_block_info=True)

    fee_wei = fee_info["overall_fee"]
    fee_eth = float(Web3.fromWei(fee_wei, "ether"))
    print(
        f"""\
The estimated fee is: {fee_wei} WEI ({fee_eth:.6f} ETH).
Gas usage: {fee_info["gas_usage"]}
Gas price: {fee_info["gas_price"]} WEI"""
    )


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
                    addr = parse_hex_arg(arg=addr_str, arg_name="address")
                contracts[addr] = Program.load(data=json.load(open(path.strip()))["program"])
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
            "Outputs the block corresponding to the given identifier (hash or number). "
            "In case no identifier is given, outputs the pending block."
        )
    )
    add_block_identifier_arguments(
        parser=parser, block_role_description="display", with_block_prefix=False
    )

    parser.parse_args(command_args, namespace=args)
    args.hash, args.number = parse_block_identifiers(args.hash, args.number)

    feeder_gateway_client = get_feeder_gateway_client(args)
    block = await feeder_gateway_client.get_block(block_hash=args.hash, block_number=args.number)
    print(block.dumps(indent=4, sort_keys=True))


async def get_block_traces(args, command_args):
    parser = argparse.ArgumentParser(
        description=(
            "Outputs the transaction traces of the block corresponding to the given identifier "
            "(hash or number)."
        )
    )
    add_block_identifier_arguments(
        parser=parser,
        block_role_description="display",
        with_block_prefix=False,
    )

    parser.parse_args(command_args, namespace=args)
    args.hash, args.number = parse_block_identifiers(
        block_hash=args.hash, block_number=args.number, default_block_number=LATEST_BLOCK_ID
    )

    feeder_gateway_client = get_feeder_gateway_client(args)
    block_traces = await feeder_gateway_client.get_block_traces(
        block_hash=args.hash, block_number=args.number
    )
    print(block_traces.dumps(indent=4, sort_keys=True))


async def get_state_update(args, command_args):
    parser = argparse.ArgumentParser(description=("Outputs the state update of a given block"))
    add_block_identifier_arguments(parser=parser, block_role_description="display")

    parser.parse_args(command_args, namespace=args)
    args.block_hash, args.block_number = parse_block_identifiers(
        block_hash=args.block_hash,
        block_number=args.block_number,
        default_block_number=LATEST_BLOCK_ID,
    )

    feeder_gateway_client = get_feeder_gateway_client(args)
    block_state_updates = await feeder_gateway_client.get_state_update(
        block_hash=args.block_hash, block_number=args.block_number
    )
    print(json.dumps(block_state_updates, indent=4, sort_keys=True))


async def get_code(args, command_args):
    parser = argparse.ArgumentParser(
        description=(
            "Outputs the bytecode of the contract at the given address with respect to "
            "a specific block. In case no block identifier is given, uses the pending block."
        )
    )
    parser.add_argument(
        "--contract_address", type=str, help="The address of the contract.", required=True
    )
    add_block_identifier_arguments(parser=parser, block_role_description="extract information from")

    parser.parse_args(command_args, namespace=args)
    args.block_hash, args.block_number = parse_block_identifiers(args.block_hash, args.block_number)

    feeder_gateway_client = get_feeder_gateway_client(args)
    code = await feeder_gateway_client.get_code(
        contract_address=parse_hex_arg(arg=args.contract_address, arg_name="contract address"),
        block_hash=args.block_hash,
        block_number=args.block_number,
    )
    print(json.dumps(code, indent=4, sort_keys=True))


async def get_class_by_hash(args, command_args):
    parser = argparse.ArgumentParser(
        description="Outputs the contract class of the class with the given hash."
    )
    parser.add_argument(
        "--class_hash", type=str, help="The hash of the desired class.", required=True
    )

    parser.parse_args(command_args, namespace=args)

    feeder_gateway_client = get_feeder_gateway_client(args)
    contract_class = await feeder_gateway_client.get_class_by_hash(class_hash=args.class_hash)
    print(json.dumps(contract_class, indent=4, sort_keys=True))


async def get_full_contract(args, command_args):
    parser = argparse.ArgumentParser(
        description=(
            "Outputs the contract class of the contract at the given address with respect to "
            "a specific block. In case no block identifier is given, uses the pending block."
        )
    )
    parser.add_argument(
        "--contract_address", type=str, help="The address of the contract.", required=True
    )
    add_block_identifier_arguments(parser=parser, block_role_description="extract information from")

    parser.parse_args(command_args, namespace=args)
    args.block_hash, args.block_number = parse_block_identifiers(args.block_hash, args.block_number)

    feeder_gateway_client = get_feeder_gateway_client(args)
    contract_class = await feeder_gateway_client.get_full_contract(
        contract_address=parse_hex_arg(arg=args.contract_address, arg_name="contract address"),
        block_hash=args.block_hash,
        block_number=args.block_number,
    )
    print(json.dumps(contract_class, indent=4, sort_keys=True))


async def get_class_hash_at(args, command_args):
    parser = argparse.ArgumentParser(
        description=(
            "Outputs the class hash of the contract at the given address with respect to "
            "a specific block. In case no block identifier is given, uses the pending block."
        )
    )
    parser.add_argument(
        "--contract_address", type=str, help="The address of the contract.", required=True
    )
    add_block_identifier_arguments(parser=parser, block_role_description="extract information from")

    parser.parse_args(command_args, namespace=args)
    args.block_hash, args.block_number = parse_block_identifiers(args.block_hash, args.block_number)

    feeder_gateway_client = get_feeder_gateway_client(args)
    class_hash = await feeder_gateway_client.get_class_hash_at(
        contract_address=parse_hex_arg(arg=args.contract_address, arg_name="contract address"),
        block_hash=args.block_hash,
        block_number=args.block_number,
    )
    print(json.dumps(class_hash, indent=4, sort_keys=True))


async def get_contract_addresses(args, command_args):
    argparse.ArgumentParser(description="Outputs the addresses of the StarkNet system contracts.")

    feeder_gateway_client = get_feeder_gateway_client(args)
    contract_addresses = await feeder_gateway_client.get_contract_addresses()
    print(json.dumps(contract_addresses, indent=4, sort_keys=True))


async def get_storage_at(args, command_args):
    parser = argparse.ArgumentParser(
        description=(
            "Outputs the storage value of a contract in a specific key with respect to "
            "a specific block. In case no block identifier is given, uses the pending block."
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
    args.block_hash, args.block_number = parse_block_identifiers(args.block_hash, args.block_number)

    feeder_gateway_client = get_feeder_gateway_client(args)
    print(
        await feeder_gateway_client.get_storage_at(
            contract_address=parse_hex_arg(arg=args.contract_address, arg_name="contract address"),
            key=args.key,
            block_hash=args.block_hash,
            block_number=args.block_number,
        )
    )


# Add arguments.


def add_declare_tx_arguments(parser: argparse.ArgumentParser):
    """
    Adds the arguments: contract, sender, max_fee, signature, nonce, token.
    """
    parser.add_argument(
        "--contract",
        type=argparse.FileType("r"),
        help="The contract class to declare.",
        required=True,
    )
    parser.add_argument(
        "--sender",
        type=str,
        default=DECLARE_SENDER_ADDRESS,
        help="The address of the account contract sending the transaction.",
    )
    parser.add_argument(
        "--max_fee",
        type=int,
        default=0,
        help="The maximal fee to be paid for the declaration.",
    )
    parser.add_argument(
        "--signature",
        type=str,
        nargs="*",
        default=[],
        help="The signature information for the declaration.",
    )
    parser.add_argument(
        "--nonce",
        type=int,
        default=0,
        help=(
            "Used for explicitly specifying the transaction nonce. "
            "If not specified, the current nonce of the account contract "
            "(as returned from StarkNet) will be used."
        ),
    )
    parser.add_argument(
        "--token", type=str, help="Used for declaring contracts in Alpha MainNet.", required=False
    )


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
            "Used for explicitly specifying the transaction nonce. "
            "If not specified, the current nonce of the account contract "
            "(as returned from StarkNet) will be used."
        ),
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Prepare the transaction and print it without signing or sending it.",
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
    block_identifier_arguments = parser.add_mutually_exclusive_group(required=False)
    block_identifier_arguments.add_argument(
        f"--{identifier_prefix}hash",
        type=str,
        help=(f"The hash of the block to {block_role_description}. "),
    )
    block_identifier_arguments.add_argument(
        f"--{identifier_prefix}number",
        help=(
            f"The number of the block to {block_role_description}; "
            "Additional supported keywords: 'pending', 'latest';"
        ),
    )


async def main():
    subparsers = {
        "call": functools.partial(invoke_or_call, call=True),
        "declare": declare,
        "deploy": deploy,
        "deploy_account": deploy_account,
        "estimate_fee": estimate_fee,
        "get_block": get_block,
        "get_block_traces": get_block_traces,
        "get_class_by_hash": get_class_by_hash,
        "get_class_hash_at": get_class_hash_at,
        "get_code": get_code,
        "get_contract_addresses": get_contract_addresses,
        "get_full_contract": get_full_contract,
        "get_state_update": get_state_update,
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
    parser.add_argument(
        "--show_trace",
        action="store_true",
        help="Print the full Python error trace in case of an internal error.",
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
        if args.show_trace:
            print(file=sys.stderr)
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    asyncio.run(main())
