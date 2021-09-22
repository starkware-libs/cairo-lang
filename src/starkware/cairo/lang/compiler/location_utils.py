from typing import Optional

from starkware.cairo.lang.compiler.ast.expr import Expression
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.expression_transformer import ExpressionTransformer


def add_parent_location(
    expr: Expression, new_parent_location: Optional[Location], message: str
) -> Expression:
    if new_parent_location is None:
        return expr

    class AddParentLocationTransformer(ExpressionTransformer):
        def location_modifier(self, location: Optional[Location]) -> Optional[Location]:
            if location is None:
                return new_parent_location
            return location.with_parent_location(
                new_parent_location=new_parent_location, message=message  # type: ignore
            )

    return AddParentLocationTransformer().visit(expr)
