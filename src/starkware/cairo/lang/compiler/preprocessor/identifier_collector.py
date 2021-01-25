from typing import Optional

from starkware.cairo.lang.compiler.ast.code_elements import (
    CodeBlock, CodeElement, CodeElementConst, CodeElementFunction, CodeElementIf, CodeElementImport,
    CodeElementLabel, CodeElementLocalVariable, CodeElementMember, CodeElementReference,
    CodeElementReturnValueReference, CodeElementTemporaryVariable, CodeElementUnpackBinding)
from starkware.cairo.lang.compiler.ast.visitor import Visitor
from starkware.cairo.lang.compiler.constants import SIZE_CONSTANT
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.identifier_definition import (
    AliasDefinition, ConstDefinition, FutureIdentifierDefinition, IdentifierDefinition,
    LabelDefinition, MemberDefinition, ReferenceDefinition)
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.preprocessor.local_variables import N_LOCALS_CONSTANT
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.scoped_name import ScopedName


def _get_identifier(obj):
    """
    Gets the name of the identifier defined by an object with either an 'identifier' attribute or
    a 'typed_identifier' attribute.
    """
    if hasattr(obj, 'identifier'):
        return obj.identifier
    if hasattr(obj, 'typed_identifier'):
        return obj.typed_identifier
    raise AttributeError(
        f"Object of type '{type(obj).__name__}' has no 'identifier' or 'typed_identifier'.")


class AnonymousLabelGenerator:
    """
    Generates anonymous labels.
    """

    def __init__(self):
        # Stores a counter for naming anonymous labels.
        self.anon_label_counter = 0

    def get(self):
        label_name = f'_anon_label{self.anon_label_counter}'
        self.anon_label_counter += 1
        return label_name

    def __eq__(self, other):
        if not isinstance(other, AnonymousLabelGenerator):
            return False
        return self.anon_label_counter == other.anon_label_counter


class IdentifierCollector(Visitor):
    """
    Collects all the identifiers in a code element.
    Uses a partial visitor.
    """
    # A dict from code element types to the identifier type they define.
    IDENTIFIER_DEFINERS = {
        CodeElementConst: ConstDefinition,
        CodeElementLabel: LabelDefinition,
        CodeElementMember: MemberDefinition,
        CodeElementReference: ReferenceDefinition,
        CodeElementLocalVariable: ReferenceDefinition,
        CodeElementTemporaryVariable: ReferenceDefinition,
        CodeElementReturnValueReference: ReferenceDefinition,
    }

    def __init__(self):
        super().__init__()
        self.anon_label_gen = AnonymousLabelGenerator()
        self.identifiers = IdentifierManager()

    def add_identifier(
            self, name: ScopedName, identifier_definition: IdentifierDefinition,
            location: Optional[Location]):
        """
        Adds an identifier with name 'name' and the given identifier definition at location
        'location'.
        """
        existing_definition = self.identifiers.get_by_full_name(name)
        if existing_definition is not None:
            if not isinstance(existing_definition, FutureIdentifierDefinition) or \
                    not isinstance(identifier_definition, FutureIdentifierDefinition):
                raise PreprocessorError(f"Redefinition of '{name}'.", location=location)
            if (existing_definition.identifier_type, identifier_definition.identifier_type) != (
                    ReferenceDefinition, ReferenceDefinition):
                # Redefinition is only allowed in reference rebinding.
                raise PreprocessorError(f"Redefinition of '{name}'.", location=location)

        self.identifiers.add_identifier(name, identifier_definition)

    def add_future_identifier(
            self, name: ScopedName, identifier_type: type, location: Optional[Location]):
        """
        Adds a future identifier with name 'name' of type 'identifier_type' at location 'location'.
        """

        self.add_identifier(
            name=name,
            identifier_definition=FutureIdentifierDefinition(identifier_type=identifier_type),
            location=location)

    def visit(self, obj):
        if type(obj) in self.IDENTIFIER_DEFINERS:
            definition_type = self.IDENTIFIER_DEFINERS[type(obj)]
            identifier = _get_identifier(obj)
            self.add_future_identifier(
                self.current_scope + identifier.name,
                definition_type,
                identifier.location)
        return super().visit(obj)

    def _visit_default(self, obj):
        assert isinstance(obj, (CodeBlock, CodeElement)), \
            f'Received unexpected object of type {type(obj).__name__}.'

    def visit_CodeElementFunction(self, elm: CodeElementFunction):
        """
        Registers the function's identifier, arguments and return values, and then recursively
        visits the code block contained in the function.
        """
        function_scope = self.current_scope + elm.name
        args_scope = function_scope + CodeElementFunction.ARGUMENT_SCOPE
        rets_scope = function_scope + CodeElementFunction.RETURN_SCOPE

        self.add_future_identifier(function_scope, LabelDefinition, elm.identifier.location)
        self.add_future_identifier(
            args_scope + SIZE_CONSTANT, ConstDefinition, elm.identifier.location)
        self.add_future_identifier(
            rets_scope + SIZE_CONSTANT, ConstDefinition, elm.identifier.location)

        for arg_id in elm.arguments.identifiers:
            if arg_id.name == N_LOCALS_CONSTANT:
                raise PreprocessorError(
                    f"The name '{N_LOCALS_CONSTANT}' is reserved and cannot be used as an "
                    'argument name.',
                    location=arg_id.location)
            self.add_future_identifier(args_scope + arg_id.name, MemberDefinition, arg_id.location)
            # Within a function, arguments are also accessible directly.
            self.add_future_identifier(
                function_scope + arg_id.name, ReferenceDefinition, arg_id.location)
        if elm.returns is not None:
            for ret_id in elm.returns.identifiers:
                self.add_future_identifier(
                    rets_scope + ret_id.name, MemberDefinition, ret_id.location)

        # Add SIZEOF_LOCALS for current block at identifier definition location if available.
        self.add_future_identifier(
            function_scope + N_LOCALS_CONSTANT, ConstDefinition, elm.identifier.location)
        super().visit_CodeElementFunction(elm)

    def visit_CodeElementUnpackBinding(self, elm: CodeElementUnpackBinding):
        """
        Registers all the unpacked identifiers.
        """
        for identifier in elm.unpacking_list.identifiers:
            self.add_future_identifier(
                self.current_scope +
                identifier.name,
                ReferenceDefinition,
                identifier.location)

    def visit_CodeElementIf(self, obj: CodeElementIf):
        label_neq_name = self.anon_label_gen.get()
        label_end_name = self.anon_label_gen.get()
        self.add_future_identifier(
            name=self.current_scope + label_neq_name, identifier_type=LabelDefinition,
            location=obj.location)
        self.add_future_identifier(
            name=self.current_scope + label_end_name, identifier_type=LabelDefinition,
            location=obj.location)
        self.visit(obj.main_code_block)
        if obj.else_code_block is not None:
            self.visit(obj.else_code_block)

    def visit_CodeBlock(self, code_block: CodeBlock):
        """
        Collects all identifiers in a code block.
        """
        for elm in code_block.code_elements:
            self.visit(elm.code_elm)

    def visit_CodeElementImport(self, elm: CodeElementImport):
        for import_item in elm.import_items:
            alias_dst = ScopedName.from_string(elm.path.name) + import_item.orig_identifier.name
            local_identifier = import_item.identifier

            # Ensure destination is a valid identifier.
            if self.identifiers.get_by_full_name(alias_dst) is None:
                raise PreprocessorError(
                    f"Scope '{elm.path.name}' does not include identifier "
                    f"'{import_item.orig_identifier.name}'.",
                    location=import_item.orig_identifier.location)

            # Add alias to identifiers.
            self.add_identifier(
                name=self.current_scope + local_identifier.name,
                identifier_definition=AliasDefinition(destination=alias_dst),
                location=import_item.identifier.location)
