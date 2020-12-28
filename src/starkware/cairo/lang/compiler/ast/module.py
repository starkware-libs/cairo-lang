import dataclasses
from typing import Optional, Sequence

from starkware.cairo.lang.compiler.ast.code_elements import CodeBlock
from starkware.cairo.lang.compiler.ast.formatting_utils import get_max_line_length
from starkware.cairo.lang.compiler.ast.node import AstNode
from starkware.cairo.lang.compiler.scoped_name import ScopedName


@dataclasses.dataclass
class CairoFile(AstNode):
    code_block: CodeBlock

    def format(self, allowed_line_length=None):
        if allowed_line_length is None:
            allowed_line_length = get_max_line_length()
        return self.code_block.format(allowed_line_length=allowed_line_length)

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.code_block]


@dataclasses.dataclass
class CairoModule(AstNode):
    cairo_file: CairoFile
    module_name: ScopedName

    def format(self, allowed_line_length=None):
        if allowed_line_length is None:
            allowed_line_length = get_max_line_length()
        return self.cairo_file.format(allowed_line_length=allowed_line_length)

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.cairo_file]
