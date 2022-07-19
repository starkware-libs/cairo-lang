from typing import Optional

from starkware.cairo.lang.compiler.ast.bool_expr import BoolAndExpr, BoolEqExpr, BoolExpr
from starkware.cairo.lang.compiler.ast.code_elements import CodeBlock, CodeElementIf
from starkware.cairo.lang.compiler.ast.visitor import Visitor
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.preprocessor.bool_expr.errors import BoolExprLoweringError
from starkware.cairo.lang.compiler.preprocessor.pass_manager import PassManagerContext, VisitorStage


class BoolExprLoweringStage(VisitorStage):
    """
    Lowers boolean logic expressions in if conditions to nested if statements.

    This stage is relatively high level and should be placed early in the compilation pass chain.
    """

    def __init__(self):
        super().__init__(visitor_factory=BoolExprLoweringVisitor, modify_ast=True)


class BoolExprLoweringVisitor(Visitor):
    def __init__(self, context: PassManagerContext):
        super().__init__()
        self.context = context

    def _visit_default(self, elm):
        return elm

    def visit_CodeElementIf(self, elm: CodeElementIf) -> CodeElementIf:
        if isinstance(elm.condition, BoolEqExpr):
            return elm

        if elm.else_code_block is not None:
            raise BoolExprLoweringError(
                "Else blocks are not supported with boolean logic expressions yet.",
                location=elm.location,
            )

        return _lower_conjunction_chain(
            lhs=elm.condition, main_code_block=elm.main_code_block, location=elm.location
        )


def _lower_conjunction_chain(
    lhs: BoolExpr, main_code_block: CodeBlock, location: Optional[Location]
) -> CodeElementIf:
    """
    Substitutes::

        if a and b:
            main_code_block
        end

    with::

        if a:
            if b:
                main_code_block
            end
        end

    Recursively for whole `and` chains.

    Python's recursion limit guards against getting into infinite loops, which may happen if
    the compiler has a bug and makes a loop in conditions tree.
    """
    if isinstance(lhs, BoolEqExpr):
        # We have reached innermost/first equation to check.
        return CodeElementIf(
            condition=lhs,
            main_code_block=main_code_block,
            else_code_block=None,
            location=location,
        )

    assert isinstance(lhs, BoolAndExpr)

    return _lower_conjunction_chain(
        lhs=lhs.a,
        main_code_block=CodeBlock.singleton(
            CodeElementIf(
                condition=lhs.b,
                main_code_block=main_code_block,
                else_code_block=None,
                location=location,
            )
        ),
        location=location,
    )
