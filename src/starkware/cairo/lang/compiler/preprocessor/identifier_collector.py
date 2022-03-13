from typing import Dict, Optional, Type

from starkware.cairo.lang.compiler.ast.arguments import IdentifierList
from starkware.cairo.lang.compiler.ast.code_elements import (
    CodeBlock,
    CodeElement,
    CodeElementConst,
    CodeElementFunction,
    CodeElementIf,
    CodeElementImport,
    CodeElementLabel,
    CodeElementLocalVariable,
    CodeElementReference,
    CodeElementReturnValueReference,
    CodeElementTemporaryVariable,
    CodeElementTypeDef,
    CodeElementUnpackBinding,
    CodeElementWith,
)
from starkware.cairo.lang.compiler.ast.visitor import Visitor
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.identifier_definition import (
    AliasDefinition,
    ConstDefinition,
    FunctionDefinition,
    FutureIdentifierDefinition,
    IdentifierDefinition,
    LabelDefinition,
    NamespaceDefinition,
    ReferenceDefinition,
    StructDefinition,
    TypeDefinition,
)
from starkware.cairo.lang.compiler.identifier_manager import IdentifierError, IdentifierManager
from starkware.cairo.lang.compiler.preprocessor.local_variables import N_LOCALS_CONSTANT
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.scoped_name import ScopedName


def _get_identifier(obj):
    """
    Gets the name of the identifier defined by an object with either an 'identifier' attribute or
    a 'typed_identifier' attribute.
    """
    if hasattr(obj, "identifier"):
        return obj.identifier
    if hasattr(obj, "typed_identifier"):
        return obj.typed_identifier
    raise AttributeError(
        f"Object of type '{type(obj).__name__}' has no 'identifier' or 'typed_identifier'."
    )


class IdentifierCollector(Visitor):
    """
    Collects all the identifiers in a code element.
    Uses a partial visitor.
    """

    # A dict from code element types to the identifier type they define.
    IDENTIFIER_DEFINERS: Dict[Type[CodeElement], Type[IdentifierDefinition]] = {
        CodeElementConst: ConstDefinition,
        CodeElementLabel: LabelDefinition,
        CodeElementReference: ReferenceDefinition,
        CodeElementLocalVariable: ReferenceDefinition,
        CodeElementTemporaryVariable: ReferenceDefinition,
        CodeElementReturnValueReference: ReferenceDefinition,
        CodeElementTypeDef: TypeDefinition,
    }

    def __init__(self, identifiers: Optional[IdentifierManager] = None):
        super().__init__()
        self.identifiers = IdentifierManager() if identifiers is None else identifiers

    def add_identifier(
        self,
        name: ScopedName,
        identifier_definition: IdentifierDefinition,
        location: Optional[Location],
    ):
        """
        Adds an identifier with name 'name' and the given identifier definition at location
        'location'.
        """
        existing_definition = self.identifiers.get_by_full_name(name)
        if existing_definition is not None:
            if not isinstance(existing_definition, FutureIdentifierDefinition) or not isinstance(
                identifier_definition, FutureIdentifierDefinition
            ):
                raise PreprocessorError(f"Redefinition of '{name}'.", location=location)
            if (existing_definition.identifier_type, identifier_definition.identifier_type) != (
                ReferenceDefinition,
                ReferenceDefinition,
            ):
                # Redefinition is only allowed in reference rebinding.
                raise PreprocessorError(f"Redefinition of '{name}'.", location=location)

        self.identifiers.add_identifier(name, identifier_definition)

    def add_future_identifier(
        self, name: ScopedName, identifier_type: type, location: Optional[Location]
    ):
        """
        Adds a future identifier with name 'name' of type 'identifier_type' at location 'location'.
        """

        self.add_identifier(
            name=name,
            identifier_definition=FutureIdentifierDefinition(identifier_type=identifier_type),
            location=location,
        )

    def visit(self, obj):
        if type(obj) in self.IDENTIFIER_DEFINERS:
            definition_type = self.IDENTIFIER_DEFINERS[type(obj)]
            identifier = _get_identifier(obj)
            self.add_future_identifier(
                self.current_scope + identifier.name, definition_type, identifier.location
            )
        return super().visit(obj)

    def _visit_default(self, obj):
        assert isinstance(
            obj, (CodeBlock, CodeElement)
        ), f"Received unexpected object of type {type(obj).__name__}."

    def visit_CodeElementFunction(self, elm: CodeElementFunction):
        """
        Registers the function's identifier, arguments and return values, and then recursively
        visits the code block contained in the function.
        """
        function_scope = self.current_scope + elm.name
        if elm.element_type == "struct":
            self.add_future_identifier(function_scope, StructDefinition, elm.identifier.location)
            return

        args_scope = function_scope + CodeElementFunction.ARGUMENT_SCOPE
        implicit_args_scope = function_scope + CodeElementFunction.IMPLICIT_ARGUMENT_SCOPE
        rets_scope = function_scope + CodeElementFunction.RETURN_SCOPE

        def handle_struct_def(identifier_list: Optional[IdentifierList], struct_name: ScopedName):
            location = elm.identifier.location
            if identifier_list is not None:
                location = identifier_list.location

            self.add_future_identifier(
                name=struct_name, identifier_type=StructDefinition, location=location
            )

        def handle_function_arguments(
            identifier_list: Optional[IdentifierList], struct_name: ScopedName
        ):
            handle_struct_def(identifier_list=identifier_list, struct_name=struct_name)
            if identifier_list is None:
                return

            for arg_id in identifier_list.identifiers:
                if arg_id.name == N_LOCALS_CONSTANT:
                    raise PreprocessorError(
                        f"The name '{N_LOCALS_CONSTANT}' is reserved and cannot be used as an "
                        "argument name.",
                        location=arg_id.location,
                    )
                # Within a function, arguments are also accessible directly.
                self.add_future_identifier(
                    function_scope + arg_id.name, ReferenceDefinition, arg_id.location
                )

        assert elm.element_type in ["func", "namespace"]
        identifier_type = FunctionDefinition if elm.element_type == "func" else NamespaceDefinition
        self.add_future_identifier(function_scope, identifier_type, elm.identifier.location)

        handle_function_arguments(identifier_list=elm.arguments, struct_name=args_scope)
        handle_function_arguments(
            identifier_list=elm.implicit_arguments, struct_name=implicit_args_scope
        )

        handle_struct_def(identifier_list=elm.returns, struct_name=rets_scope)

        # Make sure there is no name collision.
        if elm.implicit_arguments is not None:
            implicit_arg_names = {arg_id.name for arg_id in elm.implicit_arguments.identifiers}
            arg_and_return_identifiers = list(elm.arguments.identifiers)
            if elm.returns is not None:
                arg_and_return_identifiers += elm.returns.identifiers

            for arg_id in arg_and_return_identifiers:
                if arg_id.name in implicit_arg_names:
                    raise PreprocessorError(
                        "Arguments and return values cannot have the same name of an implicit "
                        "argument.",
                        location=arg_id.location,
                    )

        # Add SIZEOF_LOCALS for current block at identifier definition location if available.
        self.add_future_identifier(
            function_scope + N_LOCALS_CONSTANT, ConstDefinition, elm.identifier.location
        )
        super().visit_CodeElementFunction(elm)

    def visit_CodeElementUnpackBinding(self, elm: CodeElementUnpackBinding):
        """
        Registers all the unpacked identifiers.
        """
        for identifier in elm.unpacking_list.identifiers:
            if identifier.name == "_":
                continue
            self.add_future_identifier(
                self.current_scope + identifier.name, ReferenceDefinition, identifier.location
            )

    def visit_CodeElementIf(self, obj: CodeElementIf):
        assert obj.label_neq is not None
        assert obj.label_end is not None
        self.add_future_identifier(
            name=self.current_scope + obj.label_neq,
            identifier_type=LabelDefinition,
            location=obj.location,
        )
        self.add_future_identifier(
            name=self.current_scope + obj.label_end,
            identifier_type=LabelDefinition,
            location=obj.location,
        )
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
                try:
                    self.identifiers.get_scope(alias_dst)
                except IdentifierError:
                    raise PreprocessorError(
                        f"Cannot import '{import_item.orig_identifier.name}' "
                        f"from '{elm.path.name}'.",
                        location=import_item.orig_identifier.location,
                    )

            # Add alias to identifiers.
            self.add_identifier(
                name=self.current_scope + local_identifier.name,
                identifier_definition=AliasDefinition(destination=alias_dst),
                location=import_item.identifier.location,
            )

    def visit_CodeElementWith(self, elm: CodeElementWith):
        for aliased_identifier in elm.identifiers:
            if aliased_identifier.local_name is not None:
                self.add_future_identifier(
                    name=self.current_scope + aliased_identifier.local_name.name,
                    identifier_type=ReferenceDefinition,
                    location=aliased_identifier.local_name.location,
                )
        self.visit(elm.code_block)
