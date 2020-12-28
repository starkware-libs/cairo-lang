import dataclasses
from abc import ABC, abstractmethod
from dataclasses import field
from typing import ClassVar, Dict, List, Optional, Type, Union

import marshmallow
import marshmallow.fields as mfields
import marshmallow_dataclass

from starkware.cairo.lang.compiler.debug_info import DebugInfo
from starkware.cairo.lang.compiler.identifier_definition import (
    ConstDefinition, IdentifierDefinition, LabelDefinition, MemberDefinition, ReferenceDefinition)
from starkware.cairo.lang.compiler.identifier_manager import (
    IdentifierManager, MissingIdentifierError)
from starkware.cairo.lang.compiler.identifier_manager_field import IdentifierManagerField
from starkware.cairo.lang.compiler.preprocessor.flow import FlowTrackingDataActual, ReferenceManager
from starkware.cairo.lang.compiler.references import Reference
from starkware.cairo.lang.compiler.scoped_name import ScopedName, ScopedNameAsStr


@dataclasses.dataclass
class CairoHint:
    code: str
    accessible_scopes: List[ScopedName] = field(
        metadata=dict(marshmallow_field=mfields.List(ScopedNameAsStr)))
    flow_tracking_data: FlowTrackingDataActual


class ProgramBase(ABC):
    @abstractmethod
    def stripped(self) -> 'StrippedProgram':
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

    def stripped(self) -> 'StrippedProgram':
        return self


@marshmallow_dataclass.dataclass
class Program(ProgramBase):
    prime: int
    data: List[int]
    hints: Dict[int, CairoHint]
    builtins: List[str]
    main_scope: ScopedName = field(metadata=dict(marshmallow_field=ScopedNameAsStr()))
    identifiers: IdentifierManager = field(
        metadata=dict(marshmallow_field=IdentifierManagerField()))
    # Holds all the allocated references in the program.
    reference_manager: ReferenceManager
    debug_info: Optional[DebugInfo] = None
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema

    def stripped(self) -> StrippedProgram:
        assert self.main is not None
        return StrippedProgram(
            prime=self.prime,
            data=self.data,
            builtins=self.builtins,
            main=self.main,
        )

    def get_identifier(
            self, name: Union[str, ScopedName], expected_type: Type[IdentifierDefinition]):
        scoped_name = name if isinstance(name, ScopedName) else ScopedName.from_string(name)
        result = self.identifiers.search(
            accessible_scopes=[self.main_scope],
            name=scoped_name)
        result.assert_fully_parsed()
        identifier_definition = result.identifier_definition
        assert isinstance(identifier_definition, expected_type), (
            f"'{scoped_name}' is expected to be {expected_type.TYPE}, " +   # type: ignore
            f'found {identifier_definition.TYPE}.')  # type: ignore
        return identifier_definition

    def get_label(self, name: Union[str, ScopedName]):
        return self.get_identifier(name, LabelDefinition).pc

    def get_const(self, name: Union[str, ScopedName]):
        return self.get_identifier(name, ConstDefinition).value

    def get_member_offset(self, name: Union[str, ScopedName]):
        return self.get_identifier(name, MemberDefinition).offset

    def get_reference_binds(self, name: Union[str, ScopedName]) -> List[Reference]:
        """
        Returns all the references associated with the given name. Returns more than one value if
        the reference was rebound.
        """
        return self.get_identifier(name, ReferenceDefinition).references

    @property
    def main(self) -> Optional[int]:  # type: ignore
        try:
            return self.get_label('main')
        except MissingIdentifierError:
            return None

    @property
    def start(self) -> int:
        try:
            return self.get_label('__start__')
        except MissingIdentifierError:
            return 0
