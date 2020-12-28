import re

import pytest

from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt, TypePointer, TypeStruct
from starkware.cairo.lang.compiler.parser import parse_expr
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.type_system_visitor import CairoTypeError, simplify_type_system

scope = ScopedName.from_string


def test_type_visitor():
    t = TypeStruct(scope=scope('T'), is_fully_resolved=False)
    t_star = TypePointer(pointee=t)
    t_star2 = TypePointer(pointee=t_star)
    assert simplify_type_system(parse_expr('fp + 3 + [ap]')) == (
        parse_expr('fp + 3 + [ap]'), TypeFelt())
    assert simplify_type_system(parse_expr('cast(fp + 3 + [ap], T*)')) == (
        parse_expr('fp + 3 + [ap]'), t_star)
    # Two casts.
    assert simplify_type_system(parse_expr('cast(cast(fp, T*), felt)')) == (
        parse_expr('fp'), TypeFelt())
    # Cast from T to T.
    assert simplify_type_system(parse_expr('cast([cast(fp, T*)], T)')) == (
        parse_expr('[fp]'), t)
    # Dereference.
    assert simplify_type_system(parse_expr('[cast(fp, T**)]')) == (
        parse_expr('[fp]'), t_star)
    assert simplify_type_system(parse_expr('[[cast(fp, T**)]]')) == (
        parse_expr('[[fp]]'), t)
    # Address of.
    assert simplify_type_system(parse_expr('&([[cast(fp, T**)]])')) == (
        parse_expr('[fp]'), t_star)
    assert simplify_type_system(parse_expr('&&[[cast(fp, T**)]]')) == (
        parse_expr('fp'), t_star2)


def test_type_visitor_failures():
    verify_exception('[cast(fp, T*)] + 3', """
file:?:?: Operator '+' is not implemented for types 'T' and 'felt'.
[cast(fp, T*)] + 3
^****************^
""")
    verify_exception('[[cast(fp, T*)]]', """
file:?:?: Cannot dereference type 'T'.
[[cast(fp, T*)]]
^**************^
""")
    verify_exception('[cast(fp, T)]', """
file:?:?: Cannot cast to 'T' since the expression has no address.
[cast(fp, T)]
      ^^
""")
    verify_exception('&(cast(fp, T*) + 3)', """
file:?:?: Expression has no address.
&(cast(fp, T*) + 3)
  ^**************^
""")


def test_type_visitor_pointer_arithmetic():
    t = TypeStruct(scope=scope('T'), is_fully_resolved=False)
    t_star = TypePointer(pointee=t)
    assert simplify_type_system(parse_expr('cast(fp, T*) + 3')) == (
        parse_expr('fp + 3'), t_star)
    assert simplify_type_system(parse_expr('cast(fp, T*) - 3')) == (
        parse_expr('fp - 3'), t_star)
    assert simplify_type_system(parse_expr('cast(fp, T*) - cast(3, T*)')) == (
        parse_expr('fp - 3'), TypeFelt())


def test_type_visitor_pointer_arithmetic_failures():
    verify_exception('cast(fp, T*) + cast(fp, T*)', """
file:?:?: Operator '+' is not implemented for types 'T*' and 'T*'.
cast(fp, T*) + cast(fp, T*)
^*************************^
""")
    verify_exception('cast(fp, T*) - cast(fp, S*)', """
file:?:?: Operator '-' is not implemented for types 'T*' and 'S*'.
cast(fp, T*) - cast(fp, S*)
^*************************^
""")
    verify_exception('fp - cast(fp, T*)', """
file:?:?: Operator '-' is not implemented for types 'felt' and 'T*'.
fp - cast(fp, T*)
^***************^
""")


def verify_exception(expr_str: str, error: str):
    """
    Verifies that calling simplify_type_system() on the code results in the given error.
    """
    with pytest.raises(CairoTypeError) as e:
        simplify_type_system(parse_expr(expr_str))
    # Remove line and column information from the error using a regular expression.
    assert re.sub(':[0-9]+:[0-9]+: ', 'file:?:?: ', str(e.value)) == error.strip()
