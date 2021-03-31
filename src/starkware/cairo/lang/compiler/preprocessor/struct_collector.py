import dataclasses
from typing import Dict, List, Optional

from starkware.cairo.lang.compiler.ast.arguments import IdentifierList
from starkware.cairo.lang.compiler.ast.cairo_types import CairoType
from starkware.cairo.lang.compiler.ast.code_elements import (
    CodeBlock, CodeElement, CodeElementEmptyLine, CodeElementFunction, CodeElementMember)
from starkware.cairo.lang.compiler.ast.formatting_utils import LocationField
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.identifier_definition import MemberDefinition, StructDefinition
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.preprocessor.identifier_aware_visitor import (
    IdentifierAwareVisitor)
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.preprocessor.preprocessor_utils import assert_no_modifier
from starkware.cairo.lang.compiler.scoped_name import ScopedName


@dataclasses.dataclass
class MemberInfo:
    """
    Represents a member that wasn't assigned an offset yet.
    """
    name: str
    cairo_type: CairoType  # Unresolved type.
    location: Optional[Location] = LocationField


class StructCollector(IdentifierAwareVisitor):
    """
    Collects all the visited struct definitions.
    """

    def __init__(self, identifiers: IdentifierManager):
        super().__init__(identifiers=identifiers)

    def _visit_default(self, obj):
        assert isinstance(obj, (CodeBlock, CodeElement)), \
            f'Received unexpected object of type {type(obj).__name__}.'

    def add_struct_definition(
            self, members_list: List[MemberInfo], struct_name: ScopedName,
            location: Optional[Location]):

        offset = 0
        members: Dict[str, MemberDefinition] = {}
        for member_info in members_list:
            cairo_type = self.resolve_type(member_info.cairo_type)

            name = member_info.name
            if name in members:
                raise PreprocessorError(
                    f"Redefinition of '{struct_name + name}'.",
                    location=member_info.location)

            members[name] = MemberDefinition(
                offset=offset, cairo_type=cairo_type, location=member_info.location)
            offset += self.get_size(cairo_type)

        self.add_name_definition(
            struct_name,
            StructDefinition(
                full_name=struct_name,
                members=members,
                size=offset,
                location=location,
            ),
            location=location)

    def create_struct_from_identifier_list(
            self, identifier_list: Optional[IdentifierList], struct_name: ScopedName,
            location: Optional[Location]):
        """
        Creates a struct based on the given 'identifier_list'.
        """
        members_list: List[MemberInfo] = []
        if identifier_list is not None:
            for arg in identifier_list.identifiers:
                assert_no_modifier(arg)
                members_list.append(MemberInfo(
                    name=arg.identifier.name,
                    cairo_type=arg.get_type(),
                    location=arg.location))

            location = identifier_list.location

        self.add_struct_definition(
            members_list=members_list, struct_name=struct_name, location=location)

    def handle_struct_definition(
            self, struct_name: ScopedName, code_block: CodeBlock, location):
        members_list: List[MemberInfo] = []
        for commented_code_element in code_block.code_elements:
            elm = commented_code_element.code_elm

            if isinstance(elm, CodeElementEmptyLine):
                continue

            if not isinstance(elm, CodeElementMember):
                raise PreprocessorError(
                    'Unexpected statement inside a struct definition.',
                    location=getattr(elm, 'location', location))

            assert_no_modifier(elm.typed_identifier)

            if elm.typed_identifier.expr_type is None:
                raise PreprocessorError(
                    'Struct members must be explicitly typed (e.g., member x : felt).',
                    location=elm.typed_identifier.location)

            identifier = elm.typed_identifier.identifier

            members_list.append(MemberInfo(
                name=identifier.name,
                cairo_type=elm.typed_identifier.get_type(),
                location=identifier.location))

        self.add_struct_definition(
            members_list=members_list, struct_name=struct_name, location=location)

    def visit_CodeElementFunction(self, elm: CodeElementFunction):
        new_scope = self.current_scope + elm.name
        if elm.element_type == 'struct':
            self.handle_struct_definition(
                struct_name=new_scope, code_block=elm.code_block, location=elm.identifier.location)
            return

        # Process code_elements.
        with self.scoped(new_scope, parent=elm):
            # Create the Args, ImplicitArgs and Return structs.
            self.create_struct_from_identifier_list(
                identifier_list=elm.arguments,
                struct_name=new_scope + CodeElementFunction.ARGUMENT_SCOPE,
                location=elm.identifier.location,
            )
            self.create_struct_from_identifier_list(
                identifier_list=elm.implicit_arguments,
                struct_name=new_scope + CodeElementFunction.IMPLICIT_ARGUMENT_SCOPE,
                location=elm.identifier.location,
            )
            self.create_struct_from_identifier_list(
                identifier_list=elm.returns,
                struct_name=new_scope + CodeElementFunction.RETURN_SCOPE,
                location=elm.identifier.location,
            )

            self.visit(elm.code_block)
