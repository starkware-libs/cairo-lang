import dataclasses
from typing import Optional, Sequence

from starkware.cairo.lang.compiler.ast.expr import Expression
from starkware.cairo.lang.compiler.ast.formatting_utils import LocationField
from starkware.cairo.lang.compiler.ast.node import AstNode
from starkware.cairo.lang.compiler.error_handling import Location


@dataclasses.dataclass
class BoolExpr(AstNode):
    a: Expression
    b: Expression
    eq: bool
    location: Optional[Location] = LocationField

    def get_particles(self):
        relation = '==' if self.eq else '!='
        return [f'{self.a.format()} {relation} ', self.b.format()]

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.a, self.b]
