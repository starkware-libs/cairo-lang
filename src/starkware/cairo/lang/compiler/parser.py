import os
from functools import lru_cache
from typing import List, Optional

import lark
from lark.exceptions import (
    LarkError, UnexpectedCharacters, UnexpectedEOF, UnexpectedToken, VisitError)

from starkware.cairo.lang.compiler.ast.cairo_types import CairoType
from starkware.cairo.lang.compiler.ast.code_elements import CodeElement
from starkware.cairo.lang.compiler.ast.expr import Expression
from starkware.cairo.lang.compiler.ast.instructions import InstructionAst
from starkware.cairo.lang.compiler.ast.module import CairoFile
from starkware.cairo.lang.compiler.error_handling import InputFile, Location, LocationError
from starkware.cairo.lang.compiler.parser_transformer import ParserError, ParserTransformer

grammar_file = os.path.join(os.path.dirname(__file__), 'cairo.ebnf')
gram_parser = lark.Lark(
    open(grammar_file, 'r').read(),
    start=['cairo_file', 'repl'],
    lexer='standard',
    propagate_positions=True)


def wrap_lark_error(err: LarkError, input_file: InputFile) -> Exception:
    if input_file.content is None:
        return err
    lines = input_file.content.splitlines()
    assert len(lines) > 0, 'Syntax errors are unexpected in code with no lines.'

    err_str = str(err)

    if isinstance(err, UnexpectedToken):
        expected = set(err.expected)
        if {'FP', 'AP'} <= expected:
            expected.remove('FP')
            expected.remove('AP')
            expected.add('register')
        if {'MINUS', 'INT'} <= expected:
            expected.remove('MINUS')
        if {'CAST', 'LPAR', 'LSQB', 'IDENTIFIER', 'INT', 'AMPERSAND', 'register'} <= expected:
            expected -= {
                'CAST', 'LPAR', 'LSQB', 'IDENTIFIER', 'INT', 'PYCONST', 'AMPERSAND', 'register'}
            expected.add('expression')
        if {'PLUS', 'MINUS', 'STAR', 'SLASH'} <= expected:
            expected -= {'PLUS', 'MINUS', 'STAR', 'SLASH'}
            expected.add('operator')
        if 'COMMENT' in expected:
            expected.remove('COMMENT')
        if '_NEWLINE' in expected:
            expected.remove('_NEWLINE')
        TOKENS = {
            '_DBL_EQ': '"=="',
            '_ELLIPSIS': '"..."',
            'AMPERSAND': '"&"',
            'CAST': '"cast"',
            'CALL': '"call"',
            'COLON': '":"',
            'DOT': '"."',
            'EQUAL': '"="',
            'IDENTIFIER': 'identifier',
            'INT': 'integer',
            'LPAR': '"("',
            'LSQB': '"["',
            'MINUS': '"-"',
            'PLUS': '"+"',
            'RPAR': '")"',
            'RSQB': '"]"',
            'SEMICOLON': '";"',
            'SLASH': '"/"',
            'STAR': '"*"',
        }
        expected_lst = sorted(TOKENS.get(x, x) for x in expected)
        if len(expected_lst) > 1:
            err_str = \
                f'Unexpected token {repr(err.token)}. Expected one of: {", ".join(expected_lst)}.'
        else:
            err_str = f'Unexpected token {repr(err.token)}. Expected: {", ".join(expected_lst)}.'

        line, col, width = err.line, err.column, len(err.token)
    elif isinstance(err, UnexpectedCharacters):
        line, col, width = err.line, err.column, 1
        # Make sure line and col make sense.
        if not (0 <= line - 1 < len(lines) and 0 <= col - 1 < len(lines[line - 1])):
            raise err
        err_str = f'Unexpected character "{lines[line - 1][col - 1]}".'
    elif isinstance(err, UnexpectedEOF):
        line = len(lines)
        col, width = len(lines[-1]), 1
    else:
        # Unsupported error.
        return err

    location = Location(
        start_line=line, start_col=col, end_line=line,
        end_col=min(col + width, len(lines[line - 1]) + 1), input_file=input_file)
    return ParserError(err_str, location)


def parse(filename: Optional[str], code: str, code_type: str, expected_type):
    """
    Parses the given string and returns an AST tree based on the classes in ast/*.py.
    code_type is the ebnf rule to start from (e.g., 'expr' or 'cairo_file').
    """
    input_file = InputFile(filename=filename, content=code)
    parser_transformer = ParserTransformer(input_file)

    try:
        tree = gram_parser.parse(code, start=code_type)
    except LarkError as err:
        raise wrap_lark_error(err, input_file) from None

    try:
        parsed = parser_transformer.transform(tree)
    except VisitError as err:
        if isinstance(err.orig_exc, LocationError):
            raise err.orig_exc
        else:
            raise
    assert isinstance(parsed, expected_type), \
        f'Expected parsing result to be {expected_type.__name__}. Found: {type(parsed).__name__}'

    return parsed


def lex(code: str) -> List[lark.lexer.Token]:
    """
    Runs the lexer on the given code and returns the lark-parser tokens.
    """
    return gram_parser.lex(code)


def parse_file(code: str, filename: str = '<string>') -> CairoFile:
    """
    Parses the given string and returns a CairoFile instance.
    """
    # If code does not end with '\n', add it.
    if not code.endswith('\n'):
        code += '\n'
    return parse(filename, code, 'cairo_file', CairoFile)


def parse_instruction(code: str) -> InstructionAst:
    """
    Parses the given string and returns an InstructionAst instance.
    """
    return parse(None, code, 'instruction', InstructionAst)


@lru_cache(None)
def parse_expr(code: str) -> Expression:
    """
    Parses the given string and returns an Expression instance.
    """
    return parse(None, code, 'expr', Expression)


def parse_type(code: str) -> CairoType:
    """
    Parses the given string and returns an Expression instance.
    """
    return parse(None, code, 'type', CairoType)


def parse_code_element(code: str) -> CodeElement:
    """
    Parses the given string and returns a CodeElement instance.
    """
    return parse(None, code, 'code_element', CodeElement)
