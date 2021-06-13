import dataclasses
from typing import Dict, Optional

from starkware.cairo.lang.compiler.ast.cairo_types import (
    CairoType, TypeFelt, TypePointer, TypeStruct, TypeTuple)
from starkware.cairo.lang.compiler.ast.code_elements import CodeElementFunction
from starkware.cairo.lang.compiler.ast.visitor import Visitor
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.identifier_definition import (
    DefinitionError, FutureIdentifierDefinition, IdentifierDefinition, StructDefinition)
from starkware.cairo.lang.compiler.identifier_manager import IdentifierError, IdentifierManager
from starkware.cairo.lang.compiler.identifier_utils import get_struct_definition
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.scoped_name import ScopedName


class IdentifierAwareVisitor(Visitor):
    """
    A base class for visitors that require identifier related functionalities.
    """

    def __init__(self, identifiers: Optional[IdentifierManager] = None):
        super().__init__()
        if identifiers is None:
            identifiers = IdentifierManager()
        self.identifiers = identifiers
        self.identifier_locations: Dict[ScopedName, Location] = {}

    def handle_missing_future_definition(self, name: ScopedName, location):
        raise PreprocessorError(
            f"Identifier '{name}' not found by IdentifierCollector.",
            location=location)

    def add_name_definition(
            self, name: ScopedName, identifier_definition: IdentifierDefinition, location,
            require_future_definition=True):
        """
        Adds a definition of an identifier named 'name' at 'location'.
        The identifier must already be found as a FutureIdentifierDefinition in 'self.identifiers'
        and be of a compatible type, unless it's a temporary variable.
        """

        future_definition = self.identifiers.get_by_full_name(name)
        if future_definition is None:
            if require_future_definition:
                self.handle_missing_future_definition(name=name, location=location)
        else:
            if not isinstance(future_definition, FutureIdentifierDefinition):
                raise PreprocessorError(f"Redefinition of '{name}'.", location=location)
            if not isinstance(identifier_definition, future_definition.identifier_type):
                raise PreprocessorError(
                    f"Identifier '{name}' expected to be of type "
                    f"'{future_definition.identifier_type.__name__}', not "
                    f"'{type(identifier_definition).__name__}'.",
                    location=location)

        self.identifiers.add_identifier(name, identifier_definition)
        self.identifier_locations[name] = location

    def get_struct_definition(
            self, name: ScopedName, location: Optional[Location]) -> StructDefinition:
        """
        Returns the struct definition that corresponds to the given identifier.
        location is used if there is an error.
        """

        try:
            res = self.identifiers.search(
                accessible_scopes=self.accessible_scopes, name=name)
            res.assert_fully_parsed()
        except IdentifierError as exc:
            raise PreprocessorError(str(exc), location=location)

        struct_def = res.identifier_definition
        if not isinstance(struct_def, StructDefinition):
            raise PreprocessorError(
                f"""\
Expected '{res.canonical_name}' to be a {StructDefinition.TYPE}. Found: '{struct_def.TYPE}'.""",
                location=location)

        return struct_def

    def try_get_struct_definition(self, name: ScopedName) -> Optional[StructDefinition]:
        """
        Same as get_struct_definition() except that None is returned in case of a failure.
        """
        try:
            return self.get_struct_definition(name, None)
        except PreprocessorError:
            return None

    def get_canonical_struct_name(self, scoped_name: ScopedName, location: Optional[Location]):
        """
        Returns the canonical name for the struct given by scoped_name in the current
        accessible_scopes.
        This function also works for structs that do not have a StructDefinition yet.

        For example when parsing:
            struct S:
                member a : S*
            end
        We have to lookup S before S is defined in the identifier manager.

        location is used if there is an error.
        """
        result = self.identifiers.search(
            self.accessible_scopes, scoped_name)
        canonical_name = result.get_canonical_name()
        identifier_def = result.identifier_definition

        identifier_type = identifier_def.TYPE
        if isinstance(identifier_def, FutureIdentifierDefinition):
            identifier_type = identifier_def.identifier_type.TYPE  # type: ignore

        if identifier_type != StructDefinition.TYPE:
            raise PreprocessorError(
                f"""\
Expected '{scoped_name}' to be a {StructDefinition.TYPE}. Found: '{identifier_type}'.""",
                location=location)

        return canonical_name

    def resolve_type(self, cairo_type: CairoType) -> CairoType:
        """
        Resolves a CairoType instance to fully qualified name.
        """
        if isinstance(cairo_type, TypeFelt):
            return cairo_type
        elif isinstance(cairo_type, TypePointer):
            return dataclasses.replace(cairo_type, pointee=self.resolve_type(cairo_type.pointee))
        elif isinstance(cairo_type, TypeStruct):
            if cairo_type.is_fully_resolved:
                return cairo_type
            try:
                return dataclasses.replace(
                    cairo_type,
                    scope=self.get_canonical_struct_name(
                        scoped_name=cairo_type.scope, location=cairo_type.location),
                    is_fully_resolved=True)
            except IdentifierError as exc:
                raise PreprocessorError(str(exc), location=cairo_type.location)
        elif isinstance(cairo_type, TypeTuple):
            return dataclasses.replace(
                cairo_type,
                members=[self.resolve_type(subtype) for subtype in cairo_type.members])
        else:
            raise NotImplementedError(f'Type {type(cairo_type).__name__} is not supported.')

    def get_struct_size(self, struct_name: ScopedName, location: Optional[Location]):
        return self.get_struct_definition(name=struct_name, location=location).size

    def get_size(self, cairo_type: CairoType):
        """
        Returns the size of the given type.
        """
        if isinstance(cairo_type, (TypeFelt, TypePointer)):
            return 1
        elif isinstance(cairo_type, TypeStruct):
            if cairo_type.is_fully_resolved:
                try:
                    return get_struct_definition(
                        struct_name=cairo_type.scope, identifier_manager=self.identifiers).size
                except DefinitionError as exc:
                    raise PreprocessorError(str(exc), location=cairo_type.location)
            else:
                return self.get_struct_size(
                    struct_name=cairo_type.scope, location=cairo_type.location)
        elif isinstance(cairo_type, TypeTuple):
            return sum(self.get_size(member_type) for member_type in cairo_type.members)
        else:
            raise NotImplementedError(f'Type {type(cairo_type).__name__} is not supported.')

    def inside_a_struct(self) -> bool:
        if len(self.parents) == 0:
            return False

        parent = self.parents[-1]
        if not isinstance(parent, CodeElementFunction):
            return False

        return parent.element_type == 'struct'
