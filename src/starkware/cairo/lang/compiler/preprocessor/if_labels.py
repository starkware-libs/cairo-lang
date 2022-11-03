from starkware.cairo.lang.compiler.ast.code_elements import CodeElement, CodeElementIf
from starkware.cairo.lang.compiler.ast.node import AstNode
from starkware.cairo.lang.compiler.ast.visitor import Visitor
from starkware.cairo.lang.compiler.unique_name_provider import UniqueNameKind, UniqueNameProvider


class IfLabelAssigner(Visitor):
    """
    Adds unique labels to CodeElementIf elements.
    """

    def __init__(self, unique_names: UniqueNameProvider):
        super().__init__()
        self.unique_names = unique_names

    def _visit_default(self, elm: AstNode):
        assert elm is None or isinstance(elm, CodeElement)
        return elm

    def visit_CodeElementIf(self, elm: CodeElementIf):
        assert elm.label_neq is None
        assert elm.label_end is None
        label_neq = self.unique_names.next(UniqueNameKind.Label)
        label_end = self.unique_names.next(UniqueNameKind.Label)
        return CodeElementIf(
            condition=elm.condition,
            main_code_block=self.visit(elm.main_code_block),
            else_code_block=self.visit(elm.else_code_block),
            label_neq=label_neq,
            label_end=label_end,
            location=elm.location,
        )
