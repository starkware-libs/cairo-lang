import functools
import os
import sys
from typing import Iterable, List, Optional, Set

import lark

from starkware.cairo.lang.compiler.ast.cairo_types import TypeTuple
from starkware.cairo.lang.compiler.ast.code_elements import (
    CodeElement,
    CodeElementFunction,
    CodeElementImport,
    CodeElementLocalVariable,
    CodeElementReturn,
    CodeElementReturnValueReference,
    CodeElementScoped,
    CodeElementTailCall,
    CodeElementUnpackBinding,
    CommentedCodeElement,
)
from starkware.cairo.lang.compiler.ast.expr import (
    ArgList,
    ExprAssignment,
    ExprCast,
    ExprDeref,
    ExprParentheses,
    ExprSubscript,
    ExprTuple,
)
from starkware.cairo.lang.compiler.ast.expr_func_call import ExprFuncCall
from starkware.cairo.lang.compiler.ast.module import CairoFile
from starkware.cairo.lang.compiler.ast.notes import Notes
from starkware.cairo.lang.compiler.ast.rvalue import RvalueFuncCall
from starkware.cairo.lang.compiler.ast.visitor import Visitor
from starkware.cairo.lang.compiler.cairo_format import cairo_format_arg_parser, cairo_format_common
from starkware.cairo.lang.compiler.error_handling import InputFile
from starkware.cairo.lang.compiler.parser import get_grammar_parser, parse, parse_file
from starkware.cairo.lang.compiler.parser_transformer import ParserContext, ParserTransformer
from starkware.cairo.lang.compiler.scoped_name import ScopedName

GRAMMER_FILE = os.path.join(os.path.dirname(__file__), "migrator_grammar.ebnf")
MIGRATE_FUNCTIONS: List[str] = [
    "starkware.cairo.common.ec.is_x_on_curve",
    "starkware.cairo.common.math_cmp.is_in_range",
    "starkware.cairo.common.math_cmp.is_le_felt",
    "starkware.cairo.common.math_cmp.is_le",
    "starkware.cairo.common.math_cmp.is_nn_le",
    "starkware.cairo.common.math_cmp.is_nn",
    "starkware.cairo.common.math_cmp.is_not_zero",
    "starkware.cairo.common.math.abs_value",
    "starkware.cairo.common.math.is_quad_residue",
    "starkware.cairo.common.math.sign",
    "starkware.cairo.common.math.sqrt",
]


class MigratorParserTransformer(ParserTransformer):
    """
    Modified ParserTransformer that works with migrator_grammar.ebnf.
    """

    def __init__(self, input_file: InputFile, parser_context: Optional[ParserContext]):
        super().__init__(input_file, parser_context)

    @lark.v_args(meta=True)
    def atom_deref(self, meta, value):
        return ExprDeref(addr=value[1], notes=value[0], location=self.meta2loc(meta))

    @lark.v_args(meta=True)
    def atom_subscript(self, meta, value):
        return ExprSubscript(
            expr=value[0], offset=value[2], notes=value[1], location=self.meta2loc(meta)
        )

    @lark.v_args(meta=True)
    def atom_cast(self, meta, value):
        return ExprCast(
            expr=value[1], dest_type=value[2], notes=value[0], location=self.meta2loc(meta)
        )

    def code_element_function(self, value):
        decorators, identifier, implicit_arguments, arguments = value[:4]
        if len(value) == 6:
            # Return values present.
            returns_identifier_list = value[4]
            code_block = value[5]
            returns = TypeTuple.from_members(
                members=[
                    TypeTuple.Item(
                        name=typed_identifier.name,
                        typ=typed_identifier.get_type(),
                        location=typed_identifier.location,
                    )
                    for typed_identifier in returns_identifier_list.identifiers
                ],
                location=returns_identifier_list.location,
            )
        elif len(value) == 5:
            # Return values not present.
            returns = None
            code_block = value[4]
        else:
            raise NotImplementedError(f"Unexpected argument: value={value}")

        return CodeElementFunction(
            element_type="func",
            identifier=identifier,
            arguments=arguments,
            implicit_arguments=implicit_arguments,
            returns=returns,
            code_block=code_block,
            decorators=decorators,
        )

    @lark.v_args(meta=True)
    def commented_code_element(self, meta, value):
        comment = value[1][1:] if value[1] is not None else None
        return CommentedCodeElement(
            code_elm=value[0], comment=comment, location=self.meta2loc(meta)
        )

    @lark.v_args(meta=True)
    def code_element_return(self, meta, value):
        (expr,) = value

        if not isinstance(expr, ExprParentheses):
            return super().code_element_return(meta, value)

        # Replace the outer parentheses with an ExprTuple with has_trailing_comma=True.
        location = self.meta2loc(meta)
        expr = ExprTuple(
            members=ArgList(
                args=[ExprAssignment(identifier=None, expr=expr.val, location=expr.location)],
                notes=[Notes(), Notes()],
                has_trailing_comma=True,
                location=expr.location,
            ),
            location=location,
        )

        return CodeElementReturn(expr=expr, location=location)


class MigrateFunctionCalls(Visitor):
    """
    Migrate calls to some single-return standard library functions.
    A different instance of this visitor should be used per file.
    """

    def __init__(self, single_return_functions: Iterable[str]):
        super().__init__()
        self.local_functions_to_migrate: Set[str] = set()
        self.single_return_functions = list(single_return_functions)

    def _visit_default(self, elm: CodeElement):
        assert isinstance(elm, CodeElement)
        return elm

    def visit_CodeElementImport(self, elm: CodeElementImport):
        for item in elm.import_items:
            imported_function = f"{elm.path.name}.{item.orig_identifier.name}"
            if imported_function in self.single_return_functions:
                self.local_functions_to_migrate.add(item.identifier.name)
        return elm

    def visit_CodeElementUnpackBinding(self, elm: CodeElementUnpackBinding):
        """
        Migrates statements of the form:
            let (x) = foo();
        to:
            let x = foo();
        """

        if not isinstance(elm.rvalue, RvalueFuncCall):
            return elm
        if elm.rvalue.func_ident.name not in self.local_functions_to_migrate:
            return elm
        if len(elm.unpacking_list.identifiers) != 1:
            return elm

        # Don't convert if there are comments inside the unpacking.
        if any(len(note.comments) > 0 for note in elm.unpacking_list.notes):
            return elm

        identifier = elm.unpacking_list.identifiers[0]
        location = elm.unpacking_list.location

        if identifier.modifier is not None:
            if identifier.modifier.name != "local":
                return elm
            return CodeElementLocalVariable(
                typed_identifier=identifier.strip_modifier(),
                expr=ExprFuncCall(rvalue=elm.rvalue, location=location),
                location=location,
            )

        return CodeElementReturnValueReference(
            typed_identifier=identifier,
            func_call=elm.rvalue,
        )

    def visit_CodeElementTailCall(self, elm: CodeElementTailCall):
        """
        Migrates statements of the form:
            return foo();
        to:
            return (foo(),);
        """
        if elm.func_call.func_ident.name not in self.local_functions_to_migrate:
            return elm

        location = elm.location
        return CodeElementReturn(
            expr=ExprTuple(
                members=ArgList(
                    args=[
                        ExprAssignment(
                            identifier=None,
                            expr=ExprFuncCall(rvalue=elm.func_call, location=location),
                            location=location,
                        )
                    ],
                    notes=[Notes(), Notes()],
                    has_trailing_comma=True,
                    location=location,
                ),
                location=location,
            ),
            location=location,
        )


@functools.lru_cache(None)
def get_old_grammar() -> lark.Lark:
    return get_grammar_parser(grammar=open(GRAMMER_FILE, "r").read())


def parse_and_migrate(
    code: str, filename: str, migrate_syntax: bool, single_return_functions: Optional[Iterable[str]]
):
    if migrate_syntax:
        ast = parse(
            filename=filename,
            code=code,
            code_type="cairo_file",
            expected_type=CairoFile,
            parser_transformer_class=MigratorParserTransformer,
            grammar_parser=get_old_grammar(),
        )
    else:
        ast = parse_file(code=code, filename=filename)

    if single_return_functions is not None:
        scoped_ast = CodeElementScoped(scope=ScopedName.from_string(""), code_elements=[ast])
        scoped_ast = MigrateFunctionCalls(single_return_functions=single_return_functions).visit(
            scoped_ast
        )
        assert isinstance(scoped_ast, CodeElementScoped) and len(scoped_ast.code_elements) == 1
        ast = scoped_ast.code_elements[0]

    return ast


def main():
    validate_parser = lambda code, filename: parse_file(code=code, filename=filename)

    arg_parser = cairo_format_arg_parser(
        description="A tool to migrate Cairo code from versions before 0.10.0.",
    )

    arg_parser.add_argument(
        "--migrate_syntax",
        dest="migrate_syntax",
        action="store_true",
        default=True,
        help="Convert the syntax from Cairo versions before 0.10.0.",
    )
    arg_parser.add_argument(
        "--no_migrate_syntax",
        dest="migrate_syntax",
        action="store_false",
        help=(
            "Don't convert the syntax. This flag should only be used if the syntax was "
            "already migrated."
        ),
    )

    arg_parser.add_argument(
        "--single_return_functions",
        dest="single_return_functions",
        action="store_true",
        default=True,
        help=(
            "In version 0.10.0 some standard library functions, such as abs(), "
            "have changed to return 'felt' instead of '(res: felt)'. "
            "This requires syntax changes in the calling functions. "
            "For example, 'let (x) = abs(-5)' should change to 'let x = abs(-5)'."
        ),
    )
    arg_parser.add_argument(
        "--no_single_return_functions",
        dest="single_return_functions",
        action="store_false",
        help=(
            "Don't migrate calls to some single-return functions, such as abs(). "
            "See '--single_return_functions'."
        ),
    )

    args = arg_parser.parse_args()

    return cairo_format_common(
        args=args,
        cairo_parser=functools.partial(
            parse_and_migrate,
            migrate_syntax=args.migrate_syntax,
            single_return_functions=MIGRATE_FUNCTIONS if args.single_return_functions else None,
        ),
        validate_parser=validate_parser,
    )


if __name__ == "__main__":
    sys.exit(main())
