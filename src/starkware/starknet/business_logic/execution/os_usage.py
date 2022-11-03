import functools
import os.path
from typing import Mapping

import marshmallow_dataclass

from starkware.cairo.lang.vm.cairo_pie import ExecutionResources
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass

DIR = os.path.dirname(__file__)


@marshmallow_dataclass.dataclass(frozen=True)
class OsResources(ValidatedMarshmallowDataclass):
    # Mapping from every syscall to its execution resources in the OS (e.g., amount of Cairo steps).
    execute_syscalls: Mapping[str, ExecutionResources]
    # Mapping from every transaction to its extra execution resources in the OS,
    # i.e., resources that don't count during the execution itself.
    execute_txs_inner: Mapping[TransactionType, ExecutionResources]


# Empirical costs; accounted during transaction execution.
os_resources: OsResources = OsResources.loads(
    data=open(os.path.join(DIR, "os_resources.json")).read()
)


def get_additional_os_resources(
    syscall_counter: Mapping[str, int], tx_type: TransactionType
) -> ExecutionResources:
    # Calculate the additional resources needed for the OS to run the given syscalls;
    # i.e., the resources of the function execute_syscalls().
    os_additional_resources = functools.reduce(
        ExecutionResources.__add__,
        (
            os_resources.execute_syscalls[syscall_name] * syscall_counter[syscall_name]
            for syscall_name in syscall_counter.keys()
        ),
        ExecutionResources.empty(),
    )

    # Calculate the additional resources needed for the OS to run the given transaction;
    # i.e., the resources of the StarkNet OS function execute_transactions_inner().
    return os_additional_resources + os_resources.execute_txs_inner[tx_type]
