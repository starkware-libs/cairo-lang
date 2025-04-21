import functools
import json
import os.path
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Mapping

import marshmallow_dataclass
from marshmallow.decorators import post_dump, pre_load

from starkware.cairo.lang.vm.cairo_pie import ExecutionResourcesStone
from starkware.python.utils import snake_to_camel_case
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass

DIR = os.path.dirname(__file__)


@marshmallow_dataclass.dataclass(frozen=True)
class CallDataFactor(ValidatedMarshmallowDataclass):
    resources: ExecutionResourcesStone
    scaling_factor: int

    @classmethod
    def empty(cls) -> "CallDataFactor":
        return CallDataFactor(
            resources=ExecutionResourcesStone.empty(),
            scaling_factor=1,
        )

    @pre_load
    def add_scaling_factor_field(
        self, data: Dict[str, Any], many: bool, **kwargs
    ) -> Dict[str, Any]:
        """
        If only resources are provided (without scaling factor),
        converts them into scaling factor format where:
        - scaling factor = 1
        - resources = provided resources
        """
        if "scaling_factor" not in data:
            new_data: Dict[str, Any] = dict()
            new_data["scaling_factor"] = 1
            new_data["resources"] = data
            return new_data
        else:
            return data

    @post_dump
    def remove_trivial_scaling_factor(
        self, data: Dict[str, Any], many: bool, **kwargs
    ) -> Dict[str, Any]:
        """
        Ensures `dump` behaves like `load`:
        - If `scaling factor` is trivial, remove it.
        - Otherwise, return the full dictionary.
        """
        if data["scaling_factor"] == 1:
            return data["resources"]
        return data


@marshmallow_dataclass.dataclass(frozen=True)
class ResourcesParams(ValidatedMarshmallowDataclass):
    constant: ExecutionResourcesStone
    calldata_factor: CallDataFactor

    @classmethod
    def empty(cls) -> "ResourcesParams":
        return cls(
            constant=ExecutionResourcesStone.empty(),
            calldata_factor=CallDataFactor.empty(),
        )

    @pre_load
    def add_constant_and_calldata_factor_fields(
        self, data: Dict[str, Any], many: bool, **kwargs
    ) -> Dict[str, Any]:
        """
        If only raw resources are provided (without constant and calldata factor structure),
        converts them into resource params format where:
        - constant = provided resources
        - calldata factor = empty resources
        """

        if "calldata_factor" not in data and "constant" not in data:
            new_data = dict()
            new_data["calldata_factor"] = ExecutionResourcesStone.empty().dump()
            new_data["constant"] = data
            return new_data
        elif ("calldata_factor" in data) ^ ("constant" in data):
            raise ValueError(
                "Either both 'calldata_factor' and 'constant' should be provided or neither."
                f"data = {data}"
            )
        else:
            return data

    @post_dump
    def remove_trivial_calldata_factor(
        self, data: Dict[str, Any], many: bool, **kwargs
    ) -> Dict[str, Any]:
        """
        Ensures `dump` behaves like `load`:
        - If `calldata_factor` is empty, remove it.
        - Otherwise, return the full dictionary.
        """
        if "calldata_factor" in data and data["calldata_factor"] == CallDataFactor.empty().dump():
            return data["constant"]
        return data


@marshmallow_dataclass.dataclass(frozen=True)
class OsResources(ValidatedMarshmallowDataclass):
    # Mapping from every syscall to its execution resources in the OS (e.g., amount of Cairo steps).
    execute_syscalls: Mapping[str, ResourcesParams]
    # Mapping from every transaction to its extra execution resources in the OS,
    # i.e., resources that don't count during the execution itself.
    execute_txs_inner: Mapping[TransactionType, ResourcesParams]
    compute_os_kzg_commitment_info: ExecutionResourcesStone

    def into_blockifier_json_object(self) -> Dict[str, Any]:
        """
        Converts the object to a JSON object suitable for the blockifier by transforming all keys
        from Python's snake_case to Rust-style CamelCase and excluding the unsupported DEPLOY
        transaction types.
        """

        os_resources_json_object = self.dump()

        # Convert inner keys to CamelCase.

        # SCREAMING_SNAKE_CASE / snake_case -> CamelCase.
        for inner_dict_key in ("execute_syscalls", "execute_txs_inner"):
            transformed_values = {
                snake_to_camel_case(k.lower()): v
                for k, v in os_resources_json_object[inner_dict_key].items()
            }
            sorted_values = dict(sorted(transformed_values.items()))
            os_resources_json_object[inner_dict_key] = sorted_values

        return os_resources_json_object


@lru_cache()
def get_os_resources() -> OsResources:
    # Empirical costs; accounted during transaction execution.
    constants = json.loads(
        Path(DIR).parent.parent.joinpath("definitions/versioned_constants.json").open().read()
    )

    return OsResources.load(data=constants["os_resources"])


def get_tx_additional_os_resources(
    syscall_counter: Mapping[str, int], tx_type: TransactionType
) -> ExecutionResourcesStone:
    os_resources = get_os_resources()
    # Calculate the additional resources needed for the OS to run the given syscalls;
    # i.e., the resources of the function execute_syscalls().
    os_additional_resources = functools.reduce(
        ExecutionResourcesStone.__add__,
        (
            os_resources.execute_syscalls[syscall_name].constant * syscall_counter[syscall_name]
            for syscall_name in syscall_counter.keys()
        ),
        ExecutionResourcesStone.empty(),
    )
    if tx_type is TransactionType.DEPLOY:
        return os_additional_resources

    # Calculate the additional resources needed for the OS to run the given transaction;
    # i.e., the resources of the StarkNet OS function execute_transactions_inner().
    return os_additional_resources + os_resources.execute_txs_inner[tx_type].constant
