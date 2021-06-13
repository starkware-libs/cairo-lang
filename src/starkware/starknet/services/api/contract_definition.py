import dataclasses
from dataclasses import field
from typing import Any, ClassVar, List, Optional, Type

import marshmallow
import marshmallow_dataclass

from starkware.cairo.lang.compiler.program import Program
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starkware_utils.error_handling import stark_assert
from starkware.starkware_utils.validated_dataclass import (
    ValidatedDataclass, ValidatedMarshmallowDataclass)


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
    entry_points: List[ContractEntryPoint]
    abi: Optional[List[Any]] = None
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema

    def __post_init__(self):
        super().__post_init__()

        stark_assert(
            len(self.entry_points) == len(set([ep.selector for ep in self.entry_points])),
            code=StarknetErrorCode.MULTIPLE_ENTRY_POINTS_MATCH_SELECTOR,
            message='Entry points must be unique.')
