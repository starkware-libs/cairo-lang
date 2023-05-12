import dataclasses
import string
from abc import ABC, abstractmethod
from dataclasses import field
from typing import Any, Dict, List, Optional, Type, Union

import marshmallow
import marshmallow.fields as mfields
import marshmallow_dataclass

from starkware.cairo.lang.compiler.debug_info import DebugInfo
from starkware.cairo.lang.compiler.identifier_definition import (
    ConstDefinition,
    LabelDefinition,
    ReferenceDefinition,
    TIdentifierDefinition,
)
from starkware.cairo.lang.compiler.identifier_manager import (
    IdentifierManager,
    MissingIdentifierError,
)
from starkware.cairo.lang.compiler.identifier_manager_field import IdentifierManagerField
from starkware.cairo.lang.compiler.preprocessor.flow import FlowTrackingDataActual, ReferenceManager
from starkware.cairo.lang.compiler.preprocessor.preprocessor import AttributeScope
from starkware.cairo.lang.compiler.references import Reference
from starkware.cairo.lang.compiler.scoped_name import ScopedName, ScopedNameAsStr
from starkware.starkware_utils.marshmallow_dataclass_fields import IntAsHex, additional_metadata
from starkware.starkware_utils.serializable_dataclass import SerializableMarshmallowDataclass


@dataclasses.dataclass
class CairoHint:
    code: str
    accessible_scopes: List[ScopedName] = field(
        metadata=additional_metadata(marshmallow_field=mfields.List(ScopedNameAsStr))
    )
    flow_tracking_data: FlowTrackingDataActual


class ProgramBase(ABC):
    @abstractmethod
    def stripped(self) -> "StrippedProgram":
        """
        Returns the program as a StrippedProgram.
        """

    prime: int
    data: List[int]
    builtins: List[str]
    main: Optional[int]


@dataclasses.dataclass
class StrippedProgram(ProgramBase):
    """
    Cairo program minimal information (stripped from hints, identifiers, etc.). The absence of
    hints is crucial for security reasons. Can be used for verifying execution.
    """

    prime: int
    data: List[int]
    builtins: List[str]
    main: int

    def stripped(self) -> "StrippedProgram":
        return self

    def run_validity_checks(self):
        assert isinstance(self.prime, int) and self.prime > 2**63, "Invalid prime."
        assert isinstance(self.data, list) and all(
            isinstance(x, int) and 0 <= x < self.prime for x in self.data
        ), "Invalid program data."
        assert (
            isinstance(self.builtins, list)
            and all(is_valid_builtin_name(builtin) for builtin in self.builtins)
            and len(set(self.builtins)) == len(self.builtins)
        ), "Invalid builtin list."
        assert isinstance(self.main, int) and 0 <= self.main < len(
            self.data
        ), "Invalid main() address."


@marshmallow_dataclass.dataclass(repr=False)
class Program(ProgramBase, SerializableMarshmallowDataclass):
    prime: int = field(metadata=additional_metadata(marshmallow_field=IntAsHex(required=True)))
    data: List[int] = field(
        metadata=additional_metadata(marshmallow_field=mfields.List(IntAsHex(), required=True))
    )
    builtins: List[str]
    hints: Dict[int, List[CairoHint]]
    compiler_version: Optional[str] = field(
        metadata=dict(marshmallow_field=mfields.String(required=False, load_default=None))
    )
    main_scope: ScopedName = field(
        metadata=additional_metadata(marshmallow_field=ScopedNameAsStr())
    )
    identifiers: IdentifierManager = field(
        metadata=additional_metadata(marshmallow_field=IdentifierManagerField())
    )
    # Holds all the allocated references in the program.
    reference_manager: ReferenceManager
    attributes: List[AttributeScope] = field(default_factory=list)
    debug_info: Optional[DebugInfo] = None

    @marshmallow.post_dump
    def remove_version(self, data: Dict[Any, Any], many: bool = False):
        if data["compiler_version"] is None:
            del data["compiler_version"]
        return data

    def stripped(self) -> StrippedProgram:
        assert self.main is not None
        return StrippedProgram(
            prime=self.prime,
            data=self.data,
            builtins=self.builtins,
            main=self.main,
        )

    def get_identifier(
        self,
        name: Union[str, ScopedName],
        expected_type: Type[TIdentifierDefinition],
        full_name_lookup: Optional[bool] = None,
    ) -> TIdentifierDefinition:
        scoped_name = name if isinstance(name, ScopedName) else ScopedName.from_string(name)
        if full_name_lookup is True:
            result = self.identifiers.root.get(scoped_name)
        else:
            result = self.identifiers.search(accessible_scopes=[self.main_scope], name=scoped_name)
        result.assert_fully_parsed()
        identifier_definition = result.identifier_definition
        assert isinstance(identifier_definition, expected_type), (
            f"'{scoped_name}' is expected to be {expected_type.TYPE}, "
            + f"found {identifier_definition.TYPE}."
        )
        return identifier_definition

    def get_label(
        self, name: Union[str, ScopedName], full_name_lookup: Optional[bool] = None
    ) -> int:
        return self.get_identifier(
            name=name, expected_type=LabelDefinition, full_name_lookup=full_name_lookup
        ).pc

    def get_const(
        self, name: Union[str, ScopedName], full_name_lookup: Optional[bool] = None
    ) -> int:
        return self.get_identifier(
            name=name, expected_type=ConstDefinition, full_name_lookup=full_name_lookup
        ).value

    def get_reference_binds(self, name: Union[str, ScopedName]) -> List[Reference]:
        """
        Returns all the references associated with the given name. Returns more than one value if
        the reference was rebound.
        """
        return self.get_identifier(name, ReferenceDefinition).references

    @property
    def main(self) -> Optional[int]:  # type: ignore
        try:
            return self.get_label("main")
        except MissingIdentifierError:
            return None

    @property
    def start(self) -> int:
        try:
            return self.get_label("__start__")
        except MissingIdentifierError:
            return 0


def is_valid_builtin_name(name: str) -> bool:
    """
    Returns true if name may be used as a builtin name.
    """
    return (
        isinstance(name, str)
        and len(name) < 1000
        and set(name) <= {*string.ascii_lowercase, *string.digits, "_"}
    )
