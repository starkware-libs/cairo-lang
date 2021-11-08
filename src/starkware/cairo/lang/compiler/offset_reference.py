import dataclasses
from typing import ClassVar, Type

import marshmallow

from starkware.cairo.lang.compiler.ast.expr import ExprDot, Expression, ExprIdentifier
from starkware.cairo.lang.compiler.identifier_definition import (
    IdentifierDefinition,
    ReferenceDefinition,
)
from starkware.cairo.lang.compiler.preprocessor.flow import FlowTrackingData, ReferenceManager
from starkware.cairo.lang.compiler.scoped_name import ScopedName


@dataclasses.dataclass
class OffsetReferenceDefinition(IdentifierDefinition):
    """
    Represents an expression of the form "x.y.z" where "x" is a typed reference.
    For example, if 'x' is a typed reference with type 'T*', then 'x.y' is translated to
    '[x + T.y]'.
    If 'x.y' is of type 'S*' then 'x.y.z' is translated to '[[x + T.y] + S.z]'.
    In the example, 'x' is the parent reference and 'y.z' is the member path.
    When eval() is called, both 'x' and 'T.y' are evaluated and '[x + T.y]' is returned.
    """

    TYPE: ClassVar[str] = "offset-reference"
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema

    parent: ReferenceDefinition
    member_path: ScopedName

    def eval(
        self, reference_manager: ReferenceManager, flow_tracking_data: FlowTrackingData
    ) -> Expression:
        expr = flow_tracking_data.evaluate_reference(
            reference_manager=reference_manager, name=self.parent.full_name
        )

        for member_name in self.member_path.path:
            expr = ExprDot(expr=expr, member=ExprIdentifier(name=member_name))

        return expr
