#!/usr/bin/env python3

import argparse
import asyncio
import functools
import json
import os
import sys

from services.external_api.base_client import RetryConfig
from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt, TypePointer
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.parser import parse_type
from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.lang.compiler.type_system import mark_type_resolved
from starkware.cairo.lang.compiler.type_utils import check_felts_only_type
from starkware.cairo.lang.version import __version__
from starkware.cairo.lang.vm.reconstruct_traceback import reconstruct_traceback
from starkware.starknet.compiler.compile import get_selector_from_name
from starkware.starknet.definitions import fields
from starkware.starknet.public.abi_structs import struct_definition_from_abi_entry
from starkware.starknet.services.api.contract_definition import ContractDefinition
from starkware.starknet.services.api.feeder_gateway.feeder_gateway_client import FeederGatewayClient
from starkware.starknet.services.api.gateway.gateway_client import GatewayClient
from starkware.starknet.services.api.gateway.transaction import Deploy, InvokeFunction
from starkware.starkware_utils.error_handling import StarkErrorCode


def get_gateway_client(args) -> GatewayClient:
    gateway_url = os.environ.get("STARKNET_GATEWAY_URL")
    if args.gateway_url is not None:
        gateway_url = args.gateway_url
    if gateway_url is None:
        raise Exception(
            f'gateway_url must be specified with the "{args.command}" subcommand.\n'
            "Consider passing --network or setting the STARKNET_NETWORK environment variable."
        )
    # Limit the number of retries.
    retry_config = RetryConfig(n_retries=1)
    return GatewayClient(url=gateway_url, retry_config=retry_config)


def get_feeder_gateway_client(args) -> FeederGatewayClient:
    feeder_gateway_url = os.environ.get("STARKNET_FEEDER_GATEWAY_URL")
    if args.feeder_gateway_url is not None:
        feeder_gateway_url = args.feeder_gateway_url
    if feeder_gateway_url is None:
        raise Exception(
            f'feeder_gateway_url must be specified with the "{args.command}" subcommand.\n'
            "Consider passing --network or setting the STARKNET_NETWORK environment variable."
        )
    # Limit the number of retries.
    retry_config = RetryConfig(n_retries=1)
    return FeederGatewayClient(url=feeder_gateway_url, retry_config=retry_config)


async def deploy(args, command_args):
    parser = argparse.ArgumentParser(description="Sends a deploy transaction to StarkNet.")
    parser.add_argument(
        "--address",
        type=str,
        help="An optional address specifying where the contract will be deployed. "
        "If the address is not specified, the contract will be deployed in a random address.",
    )
    parser.add_argument(
        "--contract",
        type=argparse.FileType("r"),
        help="The contract definition to deploy.",
        required=True,
    )
    parser.parse_args(command_args, namespace=args)

    gateway_client = get_gateway_client(args)

    try:
        address = (
            fields.ContractAddressField.get_random_value()
            if args.address is None
            else int(args.address, 16)
        )
    except ValueError:
        raise ValueError("Invalid address format.")

    contract_definition = ContractDefinition.loads(args.contract.read())
    tx = Deploy(contract_address=address, contract_definition=contract_definition)

    gateway_response = await gateway_client.add_transaction(tx=tx)
    assert (
        gateway_response["code"] == StarkErrorCode.TRANSACTION_RECEIVED.name
    ), f"Failed to send transaction. Response: {gateway_response}."
    # Don't end sentences with '.', to allow easy double-click copy-pasting of the values.
    print(
        f"""\
Deploy transaction was sent.
Contract address: 0x{address:064x}
Transaction ID: {gateway_response['tx_id']}"""
    )


async def invoke_or_call(args, command_args, call: bool):
    parser = argparse.ArgumentParser(description="Sends an invoke transaction to StarkNet.")
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
    if call:
        parser.add_argument(
            "--block_id",
            type=int,
            required=False,
            help="The ID of the block used as the context for the call operation. "
            "In case this argument is not given, uses the latest block.",
        )
    parser.parse_args(command_args, namespace=args)

    inputs = []
    for value in args.inputs:
        try:
            inputs.append(int(value, 16) if value.startswith("0x") else int(value))
        except ValueError:
            raise ValueError(
                f"Invalid input value: '{value}'. Expected a decimal or hexadecimal integer."
            )

    abi = json.load(args.abi)

    # Load types.
    identifiers = IdentifierManager()
    for abi_entry in abi:
        if abi_entry["type"] == "struct":
            struct_definition = struct_definition_from_abi_entry(abi_entry=abi_entry)
            identifiers.add_identifier(
                name=struct_definition.full_name, definition=struct_definition
            )

    try:
        address = int(args.address, 16)
    except ValueError:
        raise ValueError(f"Invalid address format: {args.address}.")
    for abi_entry in abi:
        if abi_entry["type"] == "function" and abi_entry["name"] == args.function:
            previous_felt_input = None
            current_inputs_ptr = 0
            for input_desc in abi_entry["inputs"]:
                typ = mark_type_resolved(parse_type(input_desc["type"]))
                typ_size = check_felts_only_type(cairo_type=typ, identifier_manager=identifiers)
                if typ_size is not None:
                    assert current_inputs_ptr + typ_size <= len(inputs), (
                        f"Expected at least {current_inputs_ptr + typ_size} inputs, "
                        f"got {len(inputs)}."
                    )

                    current_inputs_ptr += typ_size
                elif typ == TypePointer(pointee=TypeFelt()):
                    assert previous_felt_input is not None, (
                        f'The array argument {input_desc["name"]} of type felt* must be preceded '
                        "by a length argument of type felt."
                    )

                    current_inputs_ptr += previous_felt_input
                else:
                    raise Exception(f'Type {input_desc["type"]} is not supported.')
                previous_felt_input = inputs[current_inputs_ptr - 1] if typ == TypeFelt() else None
            break
    else:
        raise Exception(f"Function {args.function} not found.")
    selector = get_selector_from_name(args.function)
    assert (
        len(inputs) == current_inputs_ptr
    ), f"Wrong number of arguments. Expected {current_inputs_ptr}, got {len(inputs)}."
    calldata = inputs

    tx = InvokeFunction(contract_address=address, entry_point_selector=selector, calldata=calldata)

    gateway_response: dict
    if call:
        feeder_client = get_feeder_gateway_client(args)
        gateway_response = await feeder_client.call_contract(tx, args.block_id)
        print(*gateway_response["result"])
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
Transaction ID: {gateway_response['tx_id']}"""
        )


async def tx_status(args, command_args):
    parser = argparse.ArgumentParser(
        description="Queries the status of a transaction given its ID."
    )
    parser.add_argument("--id", type=int, required=True, help="The ID of the transaction to query.")
    parser.add_argument(
        "--contract",
        type=argparse.FileType("r"),
        required=False,
        help="An optional path to the compiled contract with debug information. "
        "If given, the contract will be used to add location information to errors.",
    )
    parser.add_argument(
        "--error_message", action="store_true", help="Only print the error message."
    )
    parser.parse_args(command_args, namespace=args)

    feeder_gateway_client = get_feeder_gateway_client(args)

    tx_status_response = await feeder_gateway_client.get_transaction_status(tx_id=args.id)

    # Print the error message with reconstructed location information in traceback, if necessary.
    has_error_message = (
        "tx_failure_reason" in tx_status_response
        and "error_message" in tx_status_response["tx_failure_reason"]
    )
    error_message = ""
    if has_error_message:
        error_message = tx_status_response["tx_failure_reason"]["error_message"]
        if args.contract is not None:
            program_json = json.load(args.contract)["program"]
            error_message = reconstruct_traceback(
                program=Program.load(program_json), traceback_txt=error_message
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
    parser.add_argument("--id", type=int, required=True, help="The ID of the transaction to query.")
    parser.parse_args(command_args, namespace=args)

    feeder_gateway_client = get_feeder_gateway_client(args)

    tx_as_dict = await feeder_gateway_client.get_transaction(tx_id=args.id)
    print(json.dumps(tx_as_dict, indent=4, sort_keys=True))


def handle_network_param(args):
    """
    Gives default values to the gateways if the network parameter is set.
    """
    network = os.environ.get("STARKNET_NETWORK") if args.network is None else args.network
    if network is not None:
        if network != "alpha":
            print(f"Unknown network '{network}'.")
            return 1

        dns = "alpha2.starknet.io"
        if args.gateway_url is None:
            args.gateway_url = f"https://{dns}/gateway"

        if args.feeder_gateway_url is None:
            args.feeder_gateway_url = f"https://{dns}/feeder_gateway"

    return 0


async def get_block(args, command_args):
    parser = argparse.ArgumentParser(
        description="Outputs the block corresponding to the given ID. "
        "In case no ID is given, outputs the latest block."
    )
    parser.add_argument(
        "--id",
        type=int,
        help="The ID of the block to display. In case this argument is not given, uses the latest "
        "block.",
    )
    parser.parse_args(command_args, namespace=args)

    feeder_gateway_client = get_feeder_gateway_client(args)

    block_as_dict = await feeder_gateway_client.get_block(block_id=args.id)
    print(json.dumps(block_as_dict, indent=4, sort_keys=True))


async def get_code(args, command_args):
    parser = argparse.ArgumentParser(
        description="Outputs the bytecode of the contract at the given address with respect to "
        "a specific block. In case no block ID is given, uses the latest block."
    )
    parser.add_argument(
        "--contract_address", type=str, help="The address of the contract.", required=True
    )
    parser.add_argument(
        "--block_id",
        type=int,
        help="The ID of the block to extract information from. "
        "In case this argument is not given, uses the latest block.",
    )
    parser.parse_args(command_args, namespace=args)

    feeder_gateway_client = get_feeder_gateway_client(args)

    code = await feeder_gateway_client.get_code(
        contract_address=int(args.contract_address, 16), block_id=args.block_id
    )
    print(json.dumps(code, indent=4, sort_keys=True))


async def get_contract_addresses(args, command_args):
    argparse.ArgumentParser(description="Outputs the addresses of the StarkNet system contracts.")

    feeder_gateway_client = get_feeder_gateway_client(args)
    contract_addresses = await feeder_gateway_client.get_contract_addresses()
    print(json.dumps(contract_addresses, indent=4, sort_keys=True))


async def get_storage_at(args, command_args):
    parser = argparse.ArgumentParser(
        description="Outputs the storage value of a contract in a specific key with respect to "
        "a specific block. In case no block ID is given, uses the latest block."
    )
    parser.add_argument(
        "--contract_address", type=str, help="The address of the contract.", required=True
    )
    parser.add_argument(
        "--key", type=int, help="The position in the contract's storage.", required=True
    )
    parser.add_argument(
        "--block_id",
        type=int,
        help="The ID of the block to extract information from. "
        "In case this argument is not given, uses the latest block.",
    )
    parser.parse_args(command_args, namespace=args)

    feeder_gateway_client = get_feeder_gateway_client(args)

    print(
        await feeder_gateway_client.get_storage_at(
            contract_address=int(args.contract_address, 16), key=args.key, block_id=args.block_id
        )
    )


async def main():
    subparsers = {
        "deploy": deploy,
        "invoke": functools.partial(invoke_or_call, call=False),
        "call": functools.partial(invoke_or_call, call=True),
        "tx_status": tx_status,
        "get_transaction": get_transaction,
        "get_block": get_block,
        "get_code": get_code,
        "get_storage_at": get_storage_at,
        "get_contract_addresses": get_contract_addresses,
    }
    parser = argparse.ArgumentParser(description="A tool to communicate with StarkNet.")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--network", type=str, help="The name of Network.")

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
        # Invoke the requested command.
        return await subparsers[args.command](args, unknown)
    except Exception as exc:
        print(f"Error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    asyncio.run(main())
