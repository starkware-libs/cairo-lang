import dataclasses
from dataclasses import field
from enum import Enum, auto
from typing import Dict, List, Optional

import marshmallow_dataclass

from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.program import Program
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.public.abi import AbiType, get_selector_from_name
from starkware.starkware_utils.error_handling import stark_assert
from starkware.starkware_utils.subsequence import is_subsequence
from starkware.starkware_utils.validated_dataclass import (
    ValidatedDataclass,
    ValidatedMarshmallowDataclass,
)

# An ordered list of the supported builtins.
SUPPORTED_BUILTINS = ["pedersen", "range_check", "ecdsa", "bitwise"]
CONSTRUCTOR_SELECTOR = get_selector_from_name("constructor")


class EntryPointType(Enum):
    EXTERNAL = 0
    L1_HANDLER = auto()
    CONSTRUCTOR = auto()


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
    abi: Optional[AbiType] = None

    def __post_init__(self):
        super().__post_init__()

        for entry_points in self.entry_points_by_type.values():
            stark_assert(
                all(
                    entry_points[i].selector < entry_points[i + 1].selector
                    for i in range(len(entry_points) - 1)
                ),
                code=StarknetErrorCode.INVALID_CONTRACT_DEFINITION,
                message="Entry points must be unique and sorted.",
            )

        constructor_eps = self.entry_points_by_type.get(EntryPointType.CONSTRUCTOR)
        stark_assert(
            constructor_eps is not None,
            code=StarknetErrorCode.INVALID_CONTRACT_DEFINITION,
            message="The contract is missing constructor endpoints. Wrong compiler version?",
        )

        stark_assert(
            len(constructor_eps) <= 1,  # type: ignore
            code=StarknetErrorCode.INVALID_CONTRACT_DEFINITION,
            message="A contract may have at most 1 constructor.",
        )

    def validate(self):
        stark_assert(
            is_subsequence(self.program.builtins, SUPPORTED_BUILTINS),
            code=StarknetErrorCode.INVALID_CONTRACT_DEFINITION,
            message=f"{self.program.builtins} is not a subsequence of {SUPPORTED_BUILTINS}.",
        )

        stark_assert(
            self.program.prime == DEFAULT_PRIME,
            code=StarknetErrorCode.SECURITY_ERROR,
            message=(
                f"Invalid value for field prime: {self.program.prime}. Expected: {DEFAULT_PRIME}."
            ),
        )

    def remove_debug_info(self) -> "ContractDefinition":
        """
        Sets debug_info in the Cairo contract program to None.
        Returns an altered ContractDefinition instance.
        """
        altered_program = dataclasses.replace(self.program, debug_info=None)
        return dataclasses.replace(self, program=altered_program)

    @property
    def n_entry_points(self) -> int:
        """
        Returns the number of entry points (note that functions with multiple decorators are
        counted more than once).
        """
        return sum(len(eps) for eps in self.entry_points_by_type.values())
