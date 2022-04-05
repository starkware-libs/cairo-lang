import functools
import os.path
from typing import Dict, Mapping

import marshmallow_dataclass

from starkware.cairo.lang.vm.cairo_pie import ExecutionResources
from starkware.python.utils import sub_counters
from starkware.starknet.business_logic.state.state import CarriedState
from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass

DIR = os.path.dirname(__file__)


@marshmallow_dataclass.dataclass(frozen=True)
class OsResources(ValidatedMarshmallowDataclass):
    execute_syscalls: Dict[str, ExecutionResources]


# Empirical costs; accounted during transaction execution.
os_resources: OsResources = OsResources.loads(
    data=open(os.path.join(DIR, "os_resources.json")).read()
)


def calculate_syscall_resources(syscall_counter: Mapping[str, int]) -> ExecutionResources:
    """
    Calculates and returns the additional resources needed for the OS to run the given syscalls;
    i.e., the resources of the function execute_syscalls().
    """
    supported_syscalls = os_resources.execute_syscalls.keys() & syscall_counter.keys()
    return functools.reduce(
        ExecutionResources.__add__,
        (
            os_resources.execute_syscalls[syscall_name] * syscall_counter[syscall_name]
            for syscall_name in supported_syscalls
        ),
        ExecutionResources.empty(),
    )


def get_tx_syscall_counter(state: CarriedState) -> Mapping[str, int]:
    """
    Returns the most-recent transaction's syscall counter (recent w.r.t. application on the given
    state).
    """
    if state.parent_state is None:
        return state.syscall_counter

    return sub_counters(state.syscall_counter, state.parent_state.syscall_counter)
