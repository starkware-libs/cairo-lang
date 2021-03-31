from contextlib import contextmanager
from typing import List, Optional

from starkware.cairo.lang.compiler.ast.code_elements import (
    CodeBlock, CodeElementFunction, CodeElementScoped, CodeElementWith, CommentedCodeElement)
from starkware.cairo.lang.compiler.ast.module import CairoFile, CairoModule
from starkware.cairo.lang.compiler.ast.node import AstNode
from starkware.cairo.lang.compiler.scoped_name import ScopedName


class Visitor:
    """
    Base visitor class for visiting code elements in the Cairo AST.
    """

    def __init__(self):
        self.accessible_scopes: List[ScopedName] = []
        self.parents: List[Optional[AstNode]] = []

    def visit(self, obj):
        """
        Visits an object by calling its type's 'visit_{type}'. If no corresponding visit function
        is found, calls '_visit_default'.
        """
        return getattr(self, f'visit_{type(obj).__name__}', self._visit_default)(obj)

    def visit_CodeElementFunction(self, elm: CodeElementFunction):
        if elm.element_type == 'struct':
            return elm

        new_scope = self.current_scope + elm.name
        with self.scoped(new_scope, parent=elm):
            return CodeElementFunction(
                element_type=elm.element_type,
                identifier=elm.identifier,
                arguments=elm.arguments,
                implicit_arguments=elm.implicit_arguments,
                returns=elm.returns,
                code_block=self.visit(elm.code_block),
            )

    def visit_CairoModule(self, module: CairoModule):
        with self.scoped(module.module_name, parent=module):
            return CairoModule(
                cairo_file=CairoFile(code_block=self.visit(module.cairo_file.code_block)),
                module_name=module.module_name,
            )

    def visit_CodeElementScoped(self, elm: CodeElementScoped):
        with self.scoped(elm.scope, parent=elm):
            return CodeElementScoped(
                scope=elm.scope,
                code_elements=[self.visit(element) for element in elm.code_elements],
            )

    def visit_CodeBlock(self, elm: CodeBlock):
        return CodeBlock(code_elements=[
            CommentedCodeElement(code_elm=self.visit(code_elm.code_elm), comment=code_elm.comment)
            for code_elm in elm.code_elements
        ])

    def visit_CodeElementWith(self, elm: CodeElementWith):
        return CodeElementWith(identifiers=elm.identifiers, code_block=self.visit(elm.code_block))

    def _visit_default(self, obj):
        """
        Default behavior for visitor if 'obj' type isn't handled. By default, raise exception.
        """
        raise NotImplementedError(f'No handler found for type {type(obj).__name__}.')

    @contextmanager
    def scoped(self, new_scope: ScopedName, parent: Optional[AstNode]):
        """
        Context manager for entering and leaving a scope.
        """
        self.accessible_scopes.append(new_scope)
        self.parents.append(parent)
        try:
            yield
        finally:
            self.accessible_scopes.pop()
            self.parents.pop()

    @property
    def current_scope(self) -> ScopedName:
        """
        Returns the name of the current scope.
        """
        assert len(self.accessible_scopes) > 0
        return self.accessible_scopes[-1]
