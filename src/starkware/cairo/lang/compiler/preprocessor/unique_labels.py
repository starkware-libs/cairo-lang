from starkware.cairo.lang.compiler.ast.code_elements import CodeElement, CodeElementIf
from starkware.cairo.lang.compiler.ast.node import AstNode
from starkware.cairo.lang.compiler.ast.visitor import Visitor


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


class UniqueLabelCreator(Visitor):
    """
    Adds unique labels to CodeElementIf elements.
    """

    def __init__(self):
        super().__init__()
        # Generates anonymous labels.
        self.anon_label_gen = AnonymousLabelGenerator()

    def _visit_default(self, elm: AstNode):
        assert elm is None or isinstance(elm, CodeElement)
        return elm

    def visit_CodeElementIf(self, elm: CodeElementIf):
        assert elm.label_neq is None
        assert elm.label_end is None
        label_neq = self.anon_label_gen.get()
        label_end = self.anon_label_gen.get()
        return CodeElementIf(
            condition=elm.condition,
            main_code_block=self.visit(elm.main_code_block),
            else_code_block=self.visit(elm.else_code_block),
            label_neq=label_neq,
            label_end=label_end,
            location=elm.location,
        )
