import dataclasses
from dataclasses import field
from enum import Enum, auto
from typing import Any, Dict, List, Optional

import marshmallow_dataclass

from starkware.cairo.lang.compiler.program import Program
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starkware_utils.error_handling import stark_assert
from starkware.starkware_utils.subsequence import is_subsequence
from starkware.starkware_utils.validated_dataclass import (
    ValidatedDataclass,
    ValidatedMarshmallowDataclass,
)

# An ordered list of the supported builtins.
SUPPORTED_BUILTINS = ["pedersen", "range_check", "ecdsa", "bitwise"]


class EntryPointType(Enum):
    EXTERNAL = 0
    L1_HANDLER = auto()


@dataclasses.dataclass(frozen=True)
class ContractEntryPoint(ValidatedDataclass):
    # A field element that encodes the signature of the called function.
    selector: int = field(metadata=fields.entry_point_selector_metadata)
    # The offset of the instruction that should be called within the contract bytecode.
    offset: int = field(metadata=fields.entry_point_offset_metadata)


@marshmallow_dataclass.dataclass(frozen=True)
class ContractDefinition(ValidatedMarshmallowDataclass):
    """
    Represents a contract in the StarkNet network.
    """

    program: Program
    entry_points_by_type: Dict[EntryPointType, List[ContractEntryPoint]]
    abi: Optional[List[Any]] = None

    def __post_init__(self):
        super().__post_init__()

        for entry_points in self.entry_points_by_type.values():
            stark_assert(
                len(entry_points) == len(set([ep.selector for ep in entry_points])),
                code=StarknetErrorCode.MULTIPLE_ENTRY_POINTS_MATCH_SELECTOR,
                message="Entry points must be unique.",
            )

    def validate(self):
        stark_assert(
            is_subsequence(self.program.builtins, SUPPORTED_BUILTINS),
            code=StarknetErrorCode.INVALID_CONTRACT_DEFINITION,
            message=f"{self.program.builtins} is not a subsequence of {SUPPORTED_BUILTINS}.",
        )
