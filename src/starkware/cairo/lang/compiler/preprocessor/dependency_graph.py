from typing import Dict, List

from starkware.cairo.lang.compiler.ast.code_elements import CodeElementImport
from starkware.cairo.lang.compiler.ast.expr import ExprIdentifier
from starkware.cairo.lang.compiler.ast.visitor import Visitor
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.scoped_name import ScopedName


class DependencyGraphVisitor(Visitor):
    """
    Tracks the dependencies between scope and identifier (that is, what identifiers are used in each
    scope).
    """

    def __init__(self, identifiers: IdentifierManager):
        super().__init__()
        self.identifiers = identifiers
        # A dictionary from a scope name to the list of identifiers it uses.
        self.visited_identifiers: Dict[ScopedName, List[ScopedName]] = {}

    def _visit_default(self, obj):
        for child in obj.get_children():
            if child is not None:
                self.visit(child)

    def add_identifier(self, name: ScopedName, is_resolved: bool = False):
        if is_resolved:
            canonical_name = name
        else:
            canonical_name = self.identifiers.search(
                accessible_scopes=self.accessible_scopes, name=name).canonical_name

        self.visited_identifiers.setdefault(self.current_scope, []).append(
            canonical_name)

    def visit_ExprIdentifier(self, expr: ExprIdentifier):
        self.add_identifier(ScopedName.from_string(expr.name))

    def visit_CodeElementImport(self, code_elm: CodeElementImport):
        for import_item in code_elm.import_items:
            self.add_identifier(
                ScopedName.from_string(code_elm.path.name) +
                ScopedName.from_string(import_item.orig_identifier.name),
                is_resolved=True)
