import dataclasses
from dataclasses import field
from enum import Enum, auto
from typing import Any, Dict, List, Optional

import marshmallow
import marshmallow_dataclass

from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.preprocessor.flow import ReferenceManager
from starkware.cairo.lang.compiler.program import HintedProgram, Program
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.python.utils import as_non_optional
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.public.abi import AbiType
from starkware.starkware_utils.error_handling import stark_assert
from starkware.starkware_utils.subsequence import is_subsequence
from starkware.starkware_utils.validated_dataclass import (
    ValidatedDataclass,
    ValidatedMarshmallowDataclass,
)

# An ordered list of the supported builtins.
SUPPORTED_BUILTINS = ["pedersen", "range_check", "ecdsa", "bitwise", "ec_op", "poseidon"]

# Utilites.


def validate_builtins(builtins: Optional[List[str]]):
    if builtins is None:
        return

    stark_assert(
        is_subsequence(builtins, SUPPORTED_BUILTINS),
        code=StarknetErrorCode.INVALID_CONTRACT_CLASS,
        message=f"{builtins} is not a subsequence of {SUPPORTED_BUILTINS}.",
    )


# Objects.


class EntryPointType(Enum):
    EXTERNAL = 0
    L1_HANDLER = auto()
    CONSTRUCTOR = auto()


@dataclasses.dataclass(frozen=True)
class ContractEntryPoint(ValidatedDataclass):
    # A field element that encodes the signature of the called function.
    selector: int = field(metadata=fields.entry_point_selector_metadata)
    function_idx: int = field(metadata=fields.entry_point_function_idx_metadata)


@marshmallow_dataclass.dataclass(frozen=True)
class ContractClass(ValidatedMarshmallowDataclass):
    """
    Represents a contract class in the StarkNet network.
    """

    contract_class_version: str
    sierra_program: List[int] = field(metadata=fields.felt_as_hex_list_metadata)
    entry_points_by_type: Dict[EntryPointType, List[ContractEntryPoint]]
    abi: str


@dataclasses.dataclass(frozen=True)
class CompiledClassEntryPoint(ValidatedDataclass):
    # A field element that encodes the signature of the called function.
    selector: int = field(metadata=fields.entry_point_selector_metadata)
    # The offset of the instruction that should be called within the contract bytecode.
    offset: int = field(metadata=fields.entry_point_offset_metadata)
    # Builtins used by the entry point.
    builtins: Optional[List[str]]


@marshmallow_dataclass.dataclass(frozen=True)
class CompiledClassBase(ValidatedMarshmallowDataclass):
    program: HintedProgram
    entry_points_by_type: Dict[EntryPointType, List[CompiledClassEntryPoint]]

    def __post_init__(self):
        super().__post_init__()

        for entry_points in self.entry_points_by_type.values():
            stark_assert(
                all(
                    entry_points[i].selector < entry_points[i + 1].selector
                    for i in range(len(entry_points) - 1)
                ),
                code=StarknetErrorCode.INVALID_CONTRACT_CLASS,
                message="Entry points must be unique and sorted.",
            )

        constructor_eps = self.entry_points_by_type.get(EntryPointType.CONSTRUCTOR)
        stark_assert(
            constructor_eps is not None,
            code=StarknetErrorCode.INVALID_CONTRACT_CLASS,
            message="The contract is missing constructor endpoints. Wrong compiler version?",
        )

        stark_assert(
            len(as_non_optional(constructor_eps)) <= 1,
            code=StarknetErrorCode.INVALID_CONTRACT_CLASS,
            message="A contract may have at most 1 constructor.",
        )

    def validate(self):
        validate_builtins(builtins=self.program.builtins)
        for entry_points in self.entry_points_by_type.values():
            for entry_point in entry_points:
                validate_builtins(builtins=entry_point.builtins)

        stark_assert(
            self.program.prime == DEFAULT_PRIME,
            code=StarknetErrorCode.INVALID_CONTRACT_CLASS,
            message=(
                f"Invalid value for field prime: {self.program.prime}. Expected: {DEFAULT_PRIME}."
            ),
        )

    @property
    def n_entry_points(self) -> int:
        """
        Returns the number of entry points (note that functions with multiple decorators are
        counted more than once).
        """
        return sum(len(eps) for eps in self.entry_points_by_type.values())


@marshmallow_dataclass.dataclass(frozen=True)
class CompiledClass(CompiledClassBase):
    """
    Represents a compiled contract class in the StarkNet network.
    """

    def __post_init__(self):
        super().__post_init__()

        stark_assert(
            len(self.program.builtins) == 0,
            code=StarknetErrorCode.INVALID_CONTRACT_CLASS,
            message="Builtins should be specified per entry point.",
        )

        for entry_points in self.entry_points_by_type.values():
            for entry_point in entry_points:
                stark_assert(
                    entry_point.builtins is not None,
                    code=StarknetErrorCode.INVALID_CONTRACT_CLASS,
                    message=f"Missing builtins for entry point {entry_point.selector}.",
                )

    def get_runnable_program(self, entrypoint_builtins: List[str]) -> Program:
        """
        Converts the HintedProgram into a Program object that can be run by the Python CairoRunner.
        """
        return Program(
            prime=self.program.prime,
            data=self.program.data,
            # Buitlins for the entrypoint to execute.
            builtins=entrypoint_builtins,
            hints=self.program.hints,
            compiler_version=self.program.compiler_version,
            # Fill missing fields with empty values.
            main_scope=ScopedName(),
            identifiers=IdentifierManager(),
            reference_manager=ReferenceManager(),
            attributes=[],
            debug_info=None,
        )


@marshmallow_dataclass.dataclass(frozen=True)
class DeprecatedCompiledClass(CompiledClassBase):
    """
    Represents a contract in the StarkNet network that was compiled by the old (pythonic) compiler.
    """

    program: Program
    abi: Optional[AbiType] = None

    @marshmallow.decorators.post_dump
    def remove_none_builtins(self, data: Dict[str, Any], many: bool, **kwargs) -> Dict[str, Any]:
        """
        Needed for backward compatibility of hash computation for deprecated contracts.
        """
        for entry_points in data["entry_points_by_type"].values():
            for entry_point in entry_points:
                # Verify that builtins is None and remove it.
                stark_assert(
                    entry_point.pop("builtins") is None,
                    code=StarknetErrorCode.INVALID_CONTRACT_CLASS,
                    message="Entry point should not have builtins in deprecated contracts.",
                )

        return data

    def remove_debug_info(self) -> "DeprecatedCompiledClass":
        """
        Sets debug_info in the Cairo contract program to None.
        Returns an altered DeprecatedCompiledClass instance.
        """
        altered_program = dataclasses.replace(self.program, debug_info=None)
        return dataclasses.replace(self, program=altered_program)
