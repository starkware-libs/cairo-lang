import functools
import os.path
from typing import Mapping

import marshmallow_dataclass

from starkware.cairo.lang.vm.cairo_pie import ExecutionResources
from starkware.python.utils import sub_counters
from starkware.starknet.business_logic.state.state import CarriedState
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


def calculate_syscall_resources(syscall_counter: Mapping[str, int]) -> ExecutionResources:
    """
    Calculates and returns the additional resources needed for the OS to run the given syscalls;
    i.e., the resources of the function execute_syscalls().
    """
    return functools.reduce(
        ExecutionResources.__add__,
        (
            os_resources.execute_syscalls[syscall_name] * syscall_counter[syscall_name]
            for syscall_name in syscall_counter.keys()
        ),
        ExecutionResources.empty(),
    )


def calculate_execute_txs_inner_resources(tx_type: TransactionType) -> ExecutionResources:
    """
    Calculates and returns the additional resources needed for the OS to run the given transaction;
    i.e., the resources of the StarkNet OS function execute_transactions_inner().
    """
    return (
        ExecutionResources.empty()
        if tx_type not in os_resources.execute_txs_inner
        else os_resources.execute_txs_inner[tx_type]
    )


def get_tx_syscall_counter(state: CarriedState) -> Mapping[str, int]:
    """
    Returns the most-recent transaction's syscall counter (recent w.r.t. application on the given
    state).
    """
    return sub_counters(state.syscall_counter, state.non_optional_parent_state.syscall_counter)
