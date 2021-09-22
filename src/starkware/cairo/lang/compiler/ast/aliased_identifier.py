import dataclasses
from typing import Optional, Sequence

from starkware.cairo.lang.compiler.ast.expr import ExprIdentifier
from starkware.cairo.lang.compiler.ast.formatting_utils import LocationField
from starkware.cairo.lang.compiler.ast.node import AstNode
from starkware.cairo.lang.compiler.error_handling import Location


@dataclasses.dataclass
class AliasedIdentifier(AstNode):
    orig_identifier: ExprIdentifier
    local_name: Optional[ExprIdentifier]
    location: Optional[Location] = LocationField

    def format(self):
        return f"{self.orig_identifier.format()}" + (
            f" as {self.local_name.format()}" if self.local_name else ""
        )

    @property
    def identifier(self):
        return self.local_name if self.local_name is not None else self.orig_identifier

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.orig_identifier, self.local_name]
