import dataclasses
from typing import Any, List

from starkware.starknet.business_logic.execution.objects import (
    Event,
    L2ToL1MessageInfo,
    TransactionExecutionInfo,
)
from starkware.starknet.services.api.feeder_gateway.response_objects import FunctionInvocation
from starkware.starkware_utils.validated_dataclass import ValidatedDataclass

Dataclass = Any


@dataclasses.dataclass(frozen=True)
class StarknetTransactionExecutionInfo(ValidatedDataclass):
    """
    A lean version of TransactionExecutionInfo class, containing merely the information relevant
    for the user.
    """

    result: tuple
    call_info: FunctionInvocation
    # High-level events emitted by the main call through an @event decorated function.
    main_call_events: List[Dataclass]
    # All low-level events (emitted through emit_event syscall, including those corresponding to
    # high-level ones).
    raw_events: List[Event]
    l2_to_l1_messages: List[L2ToL1MessageInfo]

    @classmethod
    def from_internal(
        cls,
        tx_execution_info: TransactionExecutionInfo,
        result: tuple,
        main_call_events: List[Dataclass],
    ) -> "StarknetTransactionExecutionInfo":
        return cls(
            result=result,
            main_call_events=main_call_events,
            raw_events=tx_execution_info.get_sorted_events(),
            l2_to_l1_messages=tx_execution_info.get_sorted_l2_to_l1_messages(),
            call_info=FunctionInvocation.from_internal_version(
                call_info=tx_execution_info.call_info
            ),
        )
