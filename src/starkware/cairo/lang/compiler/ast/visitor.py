from contextlib import contextmanager
from typing import List

from starkware.cairo.lang.compiler.ast.code_elements import CodeElementFunction, CodeElementScoped
from starkware.cairo.lang.compiler.ast.module import CairoModule
from starkware.cairo.lang.compiler.scoped_name import ScopedName


class Visitor:
    """
    Base visitor class for visiting code elements in the Cairo AST.
    """

    def __init__(self):
        self.accessible_scopes: List[ScopedName] = []

    def visit(self, obj):
        """
        Visits an object by calling its type's 'visit_{type}'. If no corresponding visit function
        is found, calls '_visit_default'.
        """
        return getattr(self, f'visit_{type(obj).__name__}', self._visit_default)(obj)

    def visit_CodeElementFunction(self, elm: CodeElementFunction):
        new_scope = self.current_scope + elm.name
        with self.scoped(new_scope):
            self.visit(elm.code_block)

    def visit_CairoModule(self, module: CairoModule):
        with self.scoped(module.module_name):
            self.visit(module.cairo_file.code_block)

    def visit_CodeElementScoped(self, elm: CodeElementScoped):
        with self.scoped(elm.scope):
            for element in elm.code_elements:
                self.visit(element)

    def _visit_default(self, obj):
        """
        Default behavior for visitor if 'obj' type isn't handled. By default, raise exception.
        """
        raise NotImplementedError(f'No handler found for type {type(obj).__name__}.')

    @contextmanager
    def scoped(self, new_scope: ScopedName):
        """
        Context manager for entering and leaving a scope.
        """
        self.accessible_scopes.append(new_scope)
        try:
            yield
        finally:
            self.accessible_scopes.pop()

    @property
    def current_scope(self) -> ScopedName:
        """
        Returns the name of the current scope.
        """
        assert len(self.accessible_scopes) > 0
        return self.accessible_scopes[-1]
