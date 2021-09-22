import dataclasses
from typing import Optional, Sequence

from starkware.cairo.lang.compiler.ast.cairo_types import CairoType, TypeFelt
from starkware.cairo.lang.compiler.ast.expr import ExprIdentifier
from starkware.cairo.lang.compiler.ast.formatting_utils import LocationField
from starkware.cairo.lang.compiler.ast.node import AstNode
from starkware.cairo.lang.compiler.error_handling import Location


@dataclasses.dataclass
class Modifier(AstNode):
    name: str
    location: Optional[Location] = LocationField

    def format(self):
        return self.name

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return []


@dataclasses.dataclass
class TypedIdentifier(AstNode):
    """
    Represents an identifier with an optional type: "identifier [: type]".
    """

    identifier: ExprIdentifier
    expr_type: Optional[CairoType]
    location: Optional[Location] = LocationField
    modifier: Optional[Modifier] = None

    def format(self):
        modifier_str = "" if self.modifier is None else self.modifier.format() + " "
        type_str = "" if self.expr_type is None else f" : {self.expr_type.format()}"
        return modifier_str + self.identifier.format() + type_str

    def override_type(self, expr_type):
        return dataclasses.replace(self, expr_type=expr_type)

    def strip_modifier(self):
        return dataclasses.replace(self, modifier=None)

    @property
    def name(self) -> str:
        return self.identifier.name

    def get_type(self) -> CairoType:
        """
        Returns the type of the identifier. If not specified, the default type is felt (TypeFelt).
        """
        return TypeFelt(location=self.location) if self.expr_type is None else self.expr_type

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.identifier, self.expr_type, self.modifier]
