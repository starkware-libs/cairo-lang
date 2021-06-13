from contextlib import contextmanager
from typing import List, Optional

from starkware.cairo.lang.compiler.ast.code_elements import (
    CodeBlock, CodeElementDirective, CodeElementFunction, CodeElementScoped, CodeElementWith,
    CommentedCodeElement, LangDirective)
from starkware.cairo.lang.compiler.ast.module import CairoFile, CairoModule
from starkware.cairo.lang.compiler.ast.node import AstNode
from starkware.cairo.lang.compiler.error_handling import LocationError
from starkware.cairo.lang.compiler.scoped_name import ScopedName


class VisitorError(LocationError):
    pass


class Visitor:
    """
    Base visitor class for visiting code elements in the Cairo AST.
    """

    def __init__(self):
        self.accessible_scopes: List[ScopedName] = []
        self.parents: List[Optional[AstNode]] = []
        self.file_lang: Optional[str] = None

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
                decorators=elm.decorators,
            )

    def visit_CairoModule(self, module: CairoModule):
        with self.scoped(module.module_name, parent=module), \
                self.with_file_lang(get_lang_from_file(module.cairo_file)):
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
        raise NotImplementedError(
            f'No handler found for type {type(obj).__name__} in {type(self).__name__}.')

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

    @contextmanager
    def with_file_lang(self, lang: Optional[str]):
        """
        Context manager for setting the file_lang member.
        """
        old_file_lang, self.file_lang = self.file_lang, lang
        try:
            yield
        finally:
            self.file_lang = old_file_lang

    @property
    def current_scope(self) -> ScopedName:
        """
        Returns the name of the current scope.
        """
        assert len(self.accessible_scopes) > 0
        return self.accessible_scopes[-1]


def get_lang_from_file(cairo_file: CairoFile) -> Optional[str]:
    """
    Returns the value of the %lang directive if it exists in the given file.
    Returns None otherwise.
    """
    lang = None
    for commented_code_element in cairo_file.code_block.code_elements:
        code_elm = commented_code_element.code_elm
        if not isinstance(code_elm, CodeElementDirective):
            continue
        directive = code_elm.directive
        if not isinstance(directive, LangDirective):
            continue
        if lang is not None:
            raise VisitorError('Found two %lang directives', location=code_elm.location)
        lang = directive.name
    return lang
