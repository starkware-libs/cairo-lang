import re

import pytest

from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo
from starkware.starknet.security.secure_hints import HintsWhitelist, InsecureHintError

ALLOWED_CODE = """
func f(a: felt, b: felt):
    %{
        This is a hint.
    %}
    ap += 5
    ret
end
"""

GOOD_CODES = [
    """
func f(b: felt):
    %{
        This is a hint.
    %}
    ap += 5
    ret
end
""",
]

BAD_CODES = [
    ("""
func f(c: felt, a: felt, b: felt):
    %{
        This is a hint.
    %}
    ap += 5
    ret
end
""", """Forbidden expressions in hint "This is a hint.":
[NamedExpression(name='__main__.f.c', expr='[cast(fp + (-5), felt*)]')]"""),
    ("""
func f(a: felt, b: felt):
    %{
        This is a bad hint.
    %}
    ap += 5
    ret
end
""", 'is not whitelisted'),
    ("""
func f(b: felt, a: felt):
    %{
        This is a hint.
    %}
    ap += 5
    ret
end
""",
        """Forbidden expressions in hint "This is a hint.":
[NamedExpression(name='__main__.f.a', expr='[cast(fp + (-3), felt*)]'), \
NamedExpression(name='__main__.f.b', expr='[cast(fp + (-4), felt*)]')]"""
     ),
]


def test_secure_hints_cases():
    template_program = compile_cairo(ALLOWED_CODE, DEFAULT_PRIME)
    whitelist = HintsWhitelist.from_program(template_program)
    for good_code in GOOD_CODES:
        program = compile_cairo(good_code, DEFAULT_PRIME)
        whitelist.verify_program_hint_secure(program)
    for bad_code, message in BAD_CODES:
        program = compile_cairo(bad_code, DEFAULT_PRIME)
        with pytest.raises(InsecureHintError, match=re.escape(message)):
            whitelist.verify_program_hint_secure(program)


def test_secure_hints_serialization():
    template_program = compile_cairo(ALLOWED_CODE, DEFAULT_PRIME)
    whitelist = HintsWhitelist.from_program(template_program)
    data = HintsWhitelist.Schema().dumps(whitelist)
    whitelist = HintsWhitelist.Schema().loads(data)
    for good_code in GOOD_CODES:
        program = compile_cairo(good_code, DEFAULT_PRIME)
        whitelist.verify_program_hint_secure(program)


def test_collision():
    """
    Tests multiple hints with the same code but different reference expressions.
    """
    code = """
func f():
    let b = [ap]
    %{
        ids.b = 1
    %}
    ret
end
func g():
    let b = [ap - 10]
    %{
        ids.b = 1
    %}
    ret
end
"""
    program = compile_cairo(code, DEFAULT_PRIME)
    whitelist = HintsWhitelist.from_program(program)
    assert len(whitelist.allowed_reference_expressions_for_hint) == 1
    whitelist.verify_program_hint_secure(program)
