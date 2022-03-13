import os
from functools import lru_cache
from typing import List, Optional

import lark
from lark.exceptions import LarkError, UnexpectedCharacters, UnexpectedToken, VisitError

from starkware.cairo.lang.compiler.ast.cairo_types import CairoType
from starkware.cairo.lang.compiler.ast.code_elements import CodeBlock, CodeElement
from starkware.cairo.lang.compiler.ast.expr import ExprConst, Expression
from starkware.cairo.lang.compiler.ast.instructions import InstructionAst
from starkware.cairo.lang.compiler.ast.module import CairoFile
from starkware.cairo.lang.compiler.error_handling import InputFile, Location, LocationError
from starkware.cairo.lang.compiler.parser_transformer import (
    ParserContext,
    ParserError,
    ParserTransformer,
)

grammar_file = os.path.join(os.path.dirname(__file__), "cairo.ebnf")
gram_parser = lark.Lark(
    open(grammar_file, "r").read(),
    start=[
        "cairo_file",
        "code_block",
        "code_element",
        "expr",
        "instruction",
        "type",
        "typed_identifier",
    ],
    lexer="standard",
    parser="lalr",
    propagate_positions=True,
)


def wrap_lark_error(err: LarkError, input_file: InputFile) -> Exception:
    if input_file.content is None:
        return err
    lines = input_file.content.splitlines()
    assert len(lines) > 0, "Syntax errors are unexpected in code with no lines."

    err_str = str(err)

    if isinstance(err, UnexpectedToken):
        # Handle unexpected part.
        unexpected_token = err.token  # type: ignore
        if unexpected_token.type == "$END":
            unexpected_msg = f"Unexpected end of input"
        else:
            unexpected_msg = f"Unexpected token {repr(unexpected_token)}"

        # Handle expected part.
        expected = set(err.accepts)
        if {"FP", "AP"} <= expected:
            expected.remove("FP")
            expected.remove("AP")
            expected.add("register")
        if {"MINUS", "INT"} <= expected:
            expected.remove("MINUS")
        if {"CAST", "LPAR", "LSQB", "IDENTIFIER", "INT", "AMPERSAND", "register"} <= expected:
            expected -= {
                "AMPERSAND",
                "CAST",
                "HEXINT",
                "IDENTIFIER",
                "INT",
                "LPAR",
                "LSQB",
                "NONDET",
                "NEW",
                "PYCONST",
                "SHORT_STRING",
                "register",
            }
            expected.add("expression")
        if {"PLUS", "MINUS", "STAR", "SLASH", "_DBL_STAR"} <= expected:
            expected -= {"PLUS", "MINUS", "STAR", "SLASH", "_DBL_STAR"}
            expected.add("operator")
        if {"STAR", "_DBL_STAR"} <= expected and "PLUS" not in expected:
            expected.remove("_DBL_STAR")
        if "COMMENT" in expected:
            expected.remove("COMMENT")
        if "_NEWLINE" in expected:
            expected.remove("_NEWLINE")
        TOKENS = {
            "$END": "end of input",
            "_ARROW": '"->"',
            "_AT": '"@"',
            "_DBL_EQ": '"=="',
            "_DBL_PLUS": '"++"',
            "_DBL_STAR": '"**"',
            "_NEQ": '"!="',
            "ALLOC_LOCALS": '"alloc_locals"',
            "AMPERSAND": '"&"',
            "AS": '"as"',
            "ASSERT": '"assert"',
            "BUILTINS": '"%builtins"',
            "CALL": '"call"',
            "CAST": '"cast"',
            "COLON": '":"',
            "COMMA": '","',
            "CONST": '"const"',
            "DOT": '"."',
            "DW": '"dw"',
            "END": '"end"',
            "EQUAL": '"="',
            "FROM": '"from"',
            "FUNC": '"func"',
            "HEXINT": "integer",
            "HINT": "hint",
            "IDENTIFIER": "identifier",
            "IF": '"if"',
            "INT": "integer",
            "JMP": '"jmp"',
            "LANG": '"%lang"',
            "LBRACE": '"{"',
            "LET": '"let"',
            "LOCAL": '"local"',
            "LPAR": '"("',
            "LSQB": '"["',
            "MEMBER": '"member"',
            "MINUS": '"-"',
            "NAMESPACE": '"namespace"',
            "NEW": '"new"',
            "PLUS": '"+"',
            "RBRACE": '"}"',
            "RET": '"ret"',
            "RETURN": '"return"',
            "RPAR": '")"',
            "RSQB": '"]"',
            "SEMICOLON": '";"',
            "SLASH": '"/"',
            "STAR": '"*"',
            "STATIC_ASSERT": '"static_assert"',
            "STRUCT": '"struct"',
            "SHORT_STRING": "short string",
            "TEMPVAR": '"tempvar"',
            "WITH": '"with"',
            "WITH_ATTR": '"with_attr"',
        }
        expected_lst = sorted(TOKENS.get(x, x) for x in expected)
        expected_lst_suffix = "."
        if len(expected_lst) > 10:
            expected_lst = expected_lst[:10]
            expected_lst_suffix = ", ..."
        if len(expected_lst) > 1:
            err_str = (
                f"{unexpected_msg}. Expected one of: "
                f'{", ".join(expected_lst)}{expected_lst_suffix}'
            )
        else:
            err_str = f'{unexpected_msg}. Expected: {", ".join(expected_lst)}.'

        line, col, width = err.line, err.column, len(unexpected_token)
    elif isinstance(err, UnexpectedCharacters):
        line, col, width = err.line, err.column, 1
        # Make sure line and col make sense.
        if not (0 <= line - 1 < len(lines) and 0 <= col - 1 < len(lines[line - 1])):
            raise err
        err_str = f'Unexpected character "{lines[line - 1][col - 1]}".'
    else:
        # Unsupported error.
        return err

    location = Location(
        start_line=line,
        start_col=col,
        end_line=line,
        end_col=min(col + width, len(lines[line - 1]) + 1),
        input_file=input_file,
    )
    return ParserError(err_str, location=location)


def parse(
    filename: Optional[str],
    code: str,
    code_type: str,
    expected_type,
    parser_context: Optional[ParserContext] = None,
):
    """
    Parses the given string and returns an AST tree based on the classes in ast/*.py.
    code_type is the ebnf rule to start from (e.g., 'expr' or 'cairo_file').
    """
    input_file = InputFile(filename=filename, content=code)
    parser_transformer = ParserTransformer(input_file, parser_context=parser_context)

    parser = gram_parser.parse_interactive(code, start=code_type)
    parser_state = parser.parser_state
    try:
        token = None
        for token in parser.lexer_state.lex(parser_state):
            old_state_stack = list(parser_state.state_stack)
            old_value_stack = list(parser_state.value_stack)
            parser.feed_token(token)
        old_state_stack = list(parser_state.state_stack)
        old_value_stack = list(parser_state.value_stack)
        tree = parser.feed_eof(last_token=token)
    except UnexpectedToken as err:
        # Restore the old state stack.
        parser_state.state_stack = old_state_stack
        parser_state.value_stack = old_value_stack
        err.interactive_parser = parser
        raise wrap_lark_error(err, input_file) from None
    except LarkError as err:
        raise wrap_lark_error(err, input_file) from None

    try:
        parsed = parser_transformer.transform(tree)
    except VisitError as err:
        if isinstance(err.orig_exc, LocationError):
            raise err.orig_exc
        else:
            raise
    assert isinstance(
        parsed, expected_type
    ), f"Expected parsing result to be {expected_type.__name__}. Found: {type(parsed).__name__}"

    return parsed


def lex(code: str) -> List[lark.lexer.Token]:
    """
    Runs the lexer on the given code and returns the lark-parser tokens.
    """
    return list(gram_parser.lex(code))


def parse_file(
    code: str, filename: str = "<string>", parser_context: Optional[ParserContext] = None
) -> CairoFile:
    """
    Parses the given string and returns a CairoFile instance.
    """
    # If code does not end with '\n', add it.
    if not code.endswith("\n"):
        code += "\n"
    return parse(filename, code, "cairo_file", CairoFile, parser_context=parser_context)


def parse_instruction(code: str) -> InstructionAst:
    """
    Parses the given string and returns an InstructionAst instance.
    """
    return parse(None, code, "instruction", InstructionAst)


@lru_cache(None)
def parse_expr(code: str) -> Expression:
    """
    Parses the given string and returns an Expression instance.
    """
    return parse(None, code, "expr", Expression)


def parse_const(code: str) -> ExprConst:
    """
    Parses the given string and returns an ExprConst instance.
    """
    # Use parse_expr to share the lru cache.
    expr_const = parse_expr(code=code)
    assert isinstance(expr_const, ExprConst)
    return expr_const


def parse_type(code: str) -> CairoType:
    """
    Parses the given string and returns an Expression instance.
    """
    return parse(None, code, "type", CairoType)


def parse_code_element(code: str, parser_context: Optional[ParserContext] = None) -> CodeElement:
    """
    Parses the given string and returns a CodeElement instance.
    """
    return parse(None, code, "code_element", CodeElement, parser_context=parser_context)


def parse_block(code: str) -> CodeBlock:
    return parse(
        filename=None,
        code=code,
        code_type="code_block",
        expected_type=CodeBlock,
    )
