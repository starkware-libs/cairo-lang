import dataclasses
from typing import List, MutableMapping

from starkware.cairo.lang.compiler.ast.code_elements import (
    CodeBlock,
    CodeElement,
    CommentedCodeElement,
)
from starkware.cairo.lang.compiler.ast.visitor import Visitor


class InjectVisitor(Visitor):
    """
    A visitor that injects code elements after other code elements, comparing by the python object
    id (id()).
    """

    def __init__(self, injections: MutableMapping[int, List[CommentedCodeElement]]):
        super().__init__()
        self.injections = injections

    def visit_CodeBlock(self, code_block: CodeBlock) -> CodeBlock:
        code_elements = code_block.code_elements
        new_code_elements = []
        for i, elm in enumerate(code_elements):
            res = self.visit(elm.code_elm)
            new_code_elements.append(
                dataclasses.replace(
                    code_elements[i],
                    code_elm=res,
                )
            )

            for injection in self.injections.pop(id(elm.code_elm), []):
                new_code_elements.append(injection)

        return dataclasses.replace(code_block, code_elements=new_code_elements)

    def _visit_default(self, obj):
        if isinstance(obj, CodeElement):
            return obj
        super()._visit_default(obj)


def inject_code_elements(
    ast: CodeBlock, injections: MutableMapping[int, List[CommentedCodeElement]]
) -> CodeBlock:
    """
    Injects code elements.
    Args:
    * injections - A mapping from (pythonic) object id of a CodeElement, to a list of
        CommentedCodeElement to insert after it.
    """
    visitor = InjectVisitor(injections=injections)
    res = visitor.visit(ast)
    assert len(visitor.injections) == 0, f"Some injections were unsuccessful: {visitor.injections}."
    return res
