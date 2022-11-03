import dataclasses
from typing import Dict, List, Optional, Tuple, Type

from starkware.cairo.lang.compiler.ast.cairo_types import (
    CairoType,
    TypeCodeoffset,
    TypeFelt,
    TypeFunction,
    TypeIdentifier,
    TypePointer,
    TypeStruct,
    TypeTuple,
)
from starkware.cairo.lang.compiler.ast.code_elements import CodeElementFunction
from starkware.cairo.lang.compiler.ast.rvalue import RvalueFuncCall
from starkware.cairo.lang.compiler.ast.visitor import Visitor
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.identifier_definition import (
    DefinitionError,
    FunctionDefinition,
    FutureIdentifierDefinition,
    IdentifierDefinition,
    StructDefinition,
    TypeDefinition,
)
from starkware.cairo.lang.compiler.identifier_manager import IdentifierError, IdentifierManager
from starkware.cairo.lang.compiler.identifier_utils import get_struct_definition
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.scoped_name import ScopedName


class IdentifierAwareVisitor(Visitor):
    """
    A base class for visitors that require identifier related functionalities.
    """

    def __init__(
        self,
        identifiers: Optional[IdentifierManager] = None,
        identifier_locations: Dict[ScopedName, Location] = None,
        accessible_scopes: Optional[List[ScopedName]] = None,
    ):
        super().__init__(accessible_scopes=accessible_scopes)
        if identifiers is None:
            identifiers = IdentifierManager()
        if identifier_locations is None:
            identifier_locations = {}
        self.identifiers = identifiers
        self.identifier_locations = identifier_locations

    def handle_missing_future_definition(self, name: ScopedName, location):
        raise PreprocessorError(
            f"Identifier '{name}' not found by IdentifierCollector.", location=location
        )

    def add_name_definition(
        self,
        name: ScopedName,
        identifier_definition: IdentifierDefinition,
        location,
        require_future_definition=True,
    ):
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
                    f"Identifier '{name}' expected to be "
                    f"'{future_definition.identifier_type.TYPE}', not "
                    f"'{identifier_definition.TYPE}'.",
                    location=location,
                )

        self.identifiers.add_identifier(name, identifier_definition)
        self.identifier_locations[name] = location

    def get_identifier_definition(
        self,
        name: ScopedName,
        supported_types: Tuple[Type[IdentifierDefinition], ...],
        location: Optional[Location],
    ) -> IdentifierDefinition:
        """
        Returns the definition that corresponds to the given identifier.
        Verifies that it's one of the given types.
        location is used if there is an error.
        """

        try:
            res = self.identifiers.search(accessible_scopes=self.accessible_scopes, name=name)
            res.assert_fully_parsed()
        except IdentifierError as exc:
            raise PreprocessorError(str(exc), location=location)

        identifier_definition = res.identifier_definition
        if not isinstance(identifier_definition, supported_types):
            possible_types = " or ".join(
                supported_type.TYPE for supported_type in supported_types  # type: ignore
            )
            raise PreprocessorError(
                f"""\
Expected '{res.canonical_name}' to be {possible_types}. Found: '{identifier_definition.TYPE}'.""",
                location=location,
            )

        return identifier_definition

    def get_struct_definition(
        self,
        name: ScopedName,
        location: Optional[Location],
    ) -> StructDefinition:
        """
        Returns the struct definition that corresponds to the given identifier.
        location is used if there is an error.
        """
        res = self.get_identifier_definition(
            name=name, supported_types=(StructDefinition,), location=location
        )
        assert isinstance(res, StructDefinition)
        return res

    def get_type_definition(
        self,
        name: ScopedName,
        location: Optional[Location],
    ) -> TypeDefinition:
        """
        Returns the type definition that corresponds to the given identifier.
        location is used if there is an error.
        """
        res = self.get_identifier_definition(
            name=name, supported_types=(TypeDefinition,), location=location
        )
        assert isinstance(res, TypeDefinition)
        return res

    def get_type_or_struct_definition_members(
        self, name: ScopedName, location: Optional[Location]
    ) -> List[Tuple[Optional[str], CairoType]]:
        """
        Returns the members of the type definition (assuming it's a named tuple) or struct
        definition.
        """
        definition = self.get_identifier_definition(
            name=name, supported_types=(TypeDefinition, StructDefinition), location=location
        )

        if isinstance(definition, TypeDefinition):
            if not isinstance(definition.cairo_type, TypeTuple):
                raise PreprocessorError(
                    "Only tuple types are currently supported.",
                    location=location,
                )

            return [
                (member.name, self.resolve_type(member.typ))
                for member in definition.cairo_type.members
            ]
        elif isinstance(definition, StructDefinition):
            return [
                (name, member_def.cairo_type) for name, member_def in definition.members.items()
            ]
        else:
            raise NotImplementedError(
                f"Unexpected type for definition: {type(definition).__name__}."
            )

    def try_get_struct_definition(self, name: ScopedName) -> Optional[StructDefinition]:
        """
        Same as get_struct_definition() except that None is returned in case of a failure.
        """
        try:
            return self.get_struct_definition(name, None)
        except PreprocessorError:
            return None

    def verify_possibly_future_struct(
        self,
        identifier_definition: IdentifierDefinition,
        scoped_name: ScopedName,
        location: Optional[Location],
    ):
        """
        Checks that the given IdentifierSearchResult represents a struct.
        This function also works for structs that do not have a StructDefinition yet
        (FutureDefinition).

        For example when parsing:
            struct S {
                a: S*,
            }
        We have to lookup S before S is defined in the identifier manager.

        scoped_name and location are used if there is an error.
        """
        identifier_type = identifier_definition.TYPE
        if isinstance(identifier_definition, FutureIdentifierDefinition):
            identifier_type = identifier_definition.identifier_type.TYPE  # type: ignore

        if identifier_type != StructDefinition.TYPE:
            raise PreprocessorError(
                f"""\
Expected '{scoped_name}' to be a {StructDefinition.TYPE}. Found: '{identifier_type}'.""",
                location=location,
            )

    def resolve_type(self, cairo_type: CairoType) -> CairoType:
        """
        Resolves a CairoType instance to fully qualified name.
        """
        if isinstance(cairo_type, (TypeFelt, TypeCodeoffset, TypeStruct)):
            return cairo_type
        elif isinstance(cairo_type, TypePointer):
            return dataclasses.replace(cairo_type, pointee=self.resolve_type(cairo_type.pointee))
        elif isinstance(cairo_type, TypeIdentifier):
            try:
                result = self.identifiers.search(self.accessible_scopes, cairo_type.name)
                result.assert_fully_parsed()
                if isinstance(result.identifier_definition, TypeDefinition):
                    return self.resolve_type(result.identifier_definition.cairo_type)

                if isinstance(result.identifier_definition, FunctionDefinition):
                    return TypeFunction(scope=result.get_canonical_name())

                if (
                    isinstance(result.identifier_definition, FutureIdentifierDefinition)
                    and result.identifier_definition.identifier_type is TypeDefinition
                ):
                    raise PreprocessorError(
                        "Cannot use a type before its definition.", location=cairo_type.location
                    )

                self.verify_possibly_future_struct(
                    identifier_definition=result.identifier_definition,
                    scoped_name=cairo_type.name,
                    location=cairo_type.location,
                )

                return TypeStruct(
                    scope=result.get_canonical_name(),
                    location=cairo_type.location,
                )
            except IdentifierError as exc:
                raise PreprocessorError(str(exc), location=cairo_type.location)
        elif isinstance(cairo_type, TypeTuple):
            verify_tuple_type(cairo_type=cairo_type)
            return dataclasses.replace(
                cairo_type,
                members=[
                    dataclasses.replace(member, typ=self.resolve_type(member.typ))
                    for member in cairo_type.members
                ],
            )
        else:
            raise NotImplementedError(f"Type {type(cairo_type).__name__} is not supported.")

    def get_size_by_type_name(self, type_name: ScopedName, location: Optional[Location]):
        res = self.get_identifier_definition(
            name=type_name, supported_types=(StructDefinition, TypeDefinition), location=location
        )
        assert isinstance(res, (StructDefinition, TypeDefinition))
        if isinstance(res, StructDefinition):
            return res.size
        else:
            return self.get_size(res.cairo_type)

    def get_size(self, cairo_type: CairoType):
        """
        Returns the size of the given type.
        """
        if isinstance(cairo_type, (TypeFelt, TypePointer, TypeCodeoffset)):
            return 1
        elif isinstance(cairo_type, TypeIdentifier):
            return self.get_size_by_type_name(
                type_name=cairo_type.name, location=cairo_type.location
            )
        elif isinstance(cairo_type, TypeStruct):
            try:
                return get_struct_definition(
                    struct_name=cairo_type.scope, identifier_manager=self.identifiers
                ).size
            except DefinitionError as exc:
                raise PreprocessorError(str(exc), location=cairo_type.location)
        elif isinstance(cairo_type, TypeTuple):
            return sum(self.get_size(member_type) for member_type in cairo_type.types)
        else:
            raise NotImplementedError(f"Type {type(cairo_type).__name__} is not supported.")

    def inside_a_struct(self) -> bool:
        if len(self.parents) == 0:
            return False

        parent = self.parents[-1]
        if not isinstance(parent, CodeElementFunction):
            return False

        return parent.element_type == "struct"

    def get_return_type(self, func_call: RvalueFuncCall) -> CairoType:
        """
        Returns the return type of 'func_call'.
        """
        return self.get_type_definition(
            name=ScopedName.from_string(func_call.func_ident.name)
            + CodeElementFunction.RETURN_SCOPE,
            location=func_call.location,
        ).cairo_type


def verify_tuple_type(cairo_type: TypeTuple):
    """
    Verifies that:
    1. Either all or none of the members are named.
    2. There are no duplicate names in a tuple type.
    Raises a PreprocessorError otherwise.
    Does not check the inner types.
    """
    is_named = set((member.name is not None) for member in cairo_type.members)
    if is_named == {True, False}:
        raise PreprocessorError(
            "All fields in a named tuple must have a name.", location=cairo_type.location
        )

    names = set()
    for member in cairo_type.members:
        member_name = member.name
        if member_name is None:
            continue
        if member_name in names:
            raise PreprocessorError(
                "Named tuple cannot have two entries with the same name.",
                location=member.location,
            )
        names.add(member_name)
