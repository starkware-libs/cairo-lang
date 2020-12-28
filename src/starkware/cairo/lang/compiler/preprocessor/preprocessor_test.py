import pytest

from starkware.cairo.lang.compiler.ast.code_elements import CodeElementFunction
from starkware.cairo.lang.compiler.ast.module import CairoModule
from starkware.cairo.lang.compiler.error_handling import LocationError
from starkware.cairo.lang.compiler.identifier_definition import (
    ConstDefinition, LabelDefinition, ReferenceDefinition)
from starkware.cairo.lang.compiler.identifier_manager import IdentifierError
from starkware.cairo.lang.compiler.instruction_builder import InstructionBuilderError
from starkware.cairo.lang.compiler.parser import parse_type
from starkware.cairo.lang.compiler.preprocessor.preprocessor import preprocess_codes, preprocess_str
from starkware.cairo.lang.compiler.preprocessor.preprocessor_test_utils import (
    PRIME, verify_exception)
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.test_utils import read_file_from_dict
from starkware.cairo.lang.compiler.type_system_visitor import (
    mark_type_resolved, simplify_type_system)


def test_compiler():
    program = preprocess_str(code="""

const x = 5
const y = 2 * x
[ap] = [[fp + 2 * 3] + ((7 - 1 + y))]; ap++
ap += 4 + %[ 2**10 %]

# An empty line with a comment.
[ap] = [fp] # This is a comment.
let z = ap - 3
[ap] = [ap - x]
jmp rel 2 - 3
ret
label:
jmp label if [fp + 3 + 1] != 0
""", prime=PRIME)
    assert program.format() == """\
[ap] = [[fp + 6] + 16]; ap++
ap += 1028
[ap] = [fp]
[ap] = [ap + (-5)]
jmp rel -1
ret
jmp rel 0 if [fp + 4] != 0
"""


def test_scope_const():
    code = """\
const x = 5
[ap] = x; ap++
func f():
    const x = 1234
    [ap + 1] = x; ap++
    [ap + 2] = f.x; ap++
    ret
end
[ap + 3] = x; ap++
[ap + 4] = f.x; ap++
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
[ap] = 5; ap++
[ap + 1] = 1234; ap++
[ap + 2] = 1234; ap++
ret
[ap + 3] = 5; ap++
[ap + 4] = 1234; ap++
"""


def test_referenced_before_definition_failure():
    verify_exception("""
const x = 5
func f():
    [ap + 1] = x; ap++
    const x = 1234
end
""", """
file:?:?: Identifier 'x' referenced before definition.
    [ap + 1] = x; ap++
               ^
""")
    verify_exception("""
foo.x = 6
func foo():
    const x = 6
end
""", """
file:?:?: Identifier 'foo.x' referenced before definition.
foo.x = 6
^***^
""")


def test_assign_future_label():
    code = """\
[ap] = future_label2 - future_label1; ap++
[ap] = future_label1; ap++
future_label1:
[ap] = future_label2; ap++
future_label2:
[ap] = 8; ap++
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
[ap] = 2; ap++
[ap] = 4; ap++
[ap] = 6; ap++
[ap] = 8; ap++
"""


def test_temporary_variable():
    code = """\
struct T:
    member t = 100
end
tempvar x = [ap - 1] + [fp - 3]
ap += 3
tempvar y : T* = cast(x, T*)
ap += 4
[fp] = y.t
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
[ap] = [ap + (-1)] + [fp + (-3)]; ap++
ap += 3
[ap] = [ap + (-4)]; ap++
ap += 4
[fp] = [[ap + (-5)] + 100]
"""


def test_temporary_variable_failures():
    verify_exception("""
struct T:
    member t = 100
end
tempvar x : T = 0
""", """
file:?:?: tempvar type annotation must be 'felt' or a pointer.
tempvar x : T = 0
            ^
""")


def test_tempvar_modifier_failures():
    verify_exception("""
func main():
    tempvar local x = 5
end
""", """
file:?:?: Unexpected modifier 'local'.
    tempvar local x = 5
            ^***^
""")

    verify_exception("""
tempvar x = [ap - 1] + [fp - 3]
[x] = [[ap]]
""", """
file:?:?: While expanding the reference 'x' in:
[x] = [[ap]]
 ^
file:?:?: Expected a register. Found: [ap + (-1)].
tempvar x = [ap - 1] + [fp - 3]
        ^
Preprocessed instruction:
[[ap + (-1)]] = [[ap]]
""", exc_type=InstructionBuilderError)


def test_static_assert():
    code = """\
static_assert 3 + fp + 10 == 0 + fp + 13
let x = ap
ap += 3
static_assert x + 7 == ap + 4
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
ap += 3
"""


def test_static_assert_failures():
    verify_exception("""
static_assert 3 + fp + 10 == 0 + fp + 14
""", """
file:?:?: Static assert failed: fp + 13 != fp + 14.
static_assert 3 + fp + 10 == 0 + fp + 14
^**************************************^
""")
    verify_exception("""
let x = ap
ap += 3
static_assert x + 7 == 0
""", """
file:?:?: Static assert failed: ap + 4 != 0.
static_assert x + 7 == 0
^**********************^
""")


@pytest.mark.parametrize('last_statement', [
    'jmp body if [ap] != 0',
    'ap += 0',
    '[ap] = [ap]',
    '[ap] = [ap]; ap++',
])
def test_func_failures(last_statement):
    verify_exception(f"""
func f(x):
    body:
    ret
    {last_statement}
end
""", """
file:?:?: Function must end with a return instruction or a jump.
func f(x):
     ^
""")


def test_func_modifier_failures():
    verify_exception(f"""
func f(local x):
    ret
end
""", """
file:?:?: Unexpected modifier 'local'.
func f(local x):
       ^***^
""")

    verify_exception(f"""
func f(x) -> (local y):
    ret
end
""", """
file:?:?: Unexpected modifier 'local'.
func f(x) -> (local y):
              ^***^
""")


def test_return():
    code = """\
func f() -> (a, b, c):
    return (1, [fp], c=[fp + 1] + 2)
    return (..., c=3)
    return (...)
end
func g():
  return ()
end
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
[ap] = 1; ap++
[ap] = [fp]; ap++
[ap] = [fp + 1] + 2; ap++
ret
[ap] = 3; ap++
ret
ret
ret
"""


def test_return_failures():
    # Named after positional.
    verify_exception("""
func f() -> (a, b, c):
    return (..., b=1, [fp] + 1)
end
""", """
file:?:?: Positional arguments must not appear after named arguments.
    return (..., b=1, [fp] + 1)
                      ^******^
""")
    # Using ellipsis in a void function.
    verify_exception("""
func f():
    return (...)
end
""", """
file:?:?: Ellipsis ("...") is not supported for functions with no return values. \
Use 'return()' instead.
    return (...)
    ^**********^
""")
    # Wrong num: greater by one, with ellipsis, hence removing the ellipsis may help.
    verify_exception("""
func f() -> (a, b):
    return (..., 1, [fp] + 1)
end
""", """
file:?:?: Too many expressions. Expected at most 1, got 2. Ellipsis ("...") should be removed.
    return (..., 1, [fp] + 1)
    ^***********************^
""")
    # Wrong num: greater by more than one, with ellipsis, thus removing the ellipsis is not helpful.
    verify_exception("""
func f() -> (a):
    return (..., 1, [fp] + 1)
end
""", """
file:?:?: Too many expressions. Expected none, got 2.
    return (..., 1, [fp] + 1)
    ^***********************^
""")
    # Wrong num, without ellipsis.
    verify_exception("""
func f() -> (a, b, c, d):
    return (1, [fp] + 1)
end
""", """
file:?:?: Expected exactly 4 expressions, got 2.
    return (1, [fp] + 1)
    ^******************^
""")
    # Wrong num, without ellipsis.
    verify_exception("""
func f() -> (a, b):
    return ()
end
""", """
file:?:?: Expected exactly 2 expressions, got 0.
    return ()
    ^*******^
""")
    # Unknown name.
    verify_exception("""
func f() -> (a, b, c):
    return (..., d=1, [fp] + 1)
end
""", """
file:?:?: Expected named arg 'b' found 'd'.
    return (..., d=1, [fp] + 1)
                 ^
""")
    # Not in func.
    verify_exception("""
return (a=1, [fp] + 1)
""", """
file:?:?: Unknown identifier 'Return'.
return (a=1, [fp] + 1)
^********************^
""")


def test_ellipsis_failures():
    # Ellipsis in a wrong place.
    verify_exception("""
func f() -> (a, b, c):
    return (1, ...)
end
""", """
file:?:?: Ellipsis ("...") can only be used at the beginning of the list.
    return (1, ...)
               ^*^
""")
    # Wrong place, with ellipsis.
    verify_exception("""
func f() -> (a, b, c):
    return (..., a=1, c=[fp] + 1)
end
""", """
file:?:?: Expected named arg 'b' found 'a'.
    return (..., a=1, c=[fp] + 1)
                 ^
""")
    # Missing arg, with ellipsis.
    verify_exception("""
func f() -> (a, b, c):
    return (..., a=1, b=[fp] + 1)
end
""", """
file:?:?: Expected named arg 'b' found 'a'.
    return (..., a=1, b=[fp] + 1)
                 ^
""")
    # Wrong place, without ellipsis.
    verify_exception("""
func f() -> (a, b, c):
    return (a=1, c=[fp] + 1, b=0)
end
""", """
file:?:?: Expected named arg 'b' found 'c'.
    return (a=1, c=[fp] + 1, b=0)
                 ^
""")
    # Compound expressions with ellipsis.
    verify_exception("""
func f(x, y) -> (a, b, c, d, e):
    return (..., c=x + y, d=(x + y) * 2, e=x * y)
end
""", """
file:?:?: Compound expressions cannot be used with an ellipsis ("...").
    return (..., c=x + y, d=(x + y) * 2, e=x * y)
                            ^*********^
""")


def test_function_call():
    code = """\
func foo(a, b) -> (c):
    return (1)
end
foo(2, 3)
foo(2, b=3)
let res = foo(..., b=3)
res.c = 1
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
[ap] = 1; ap++
ret
[ap] = 2; ap++
[ap] = 3; ap++
call rel -7
[ap] = 2; ap++
[ap] = 3; ap++
call rel -13
[ap] = 3; ap++
call rel -17
[ap + (-1)] = 1
"""


def test_func_args():
    code = """\
struct T:
    member s = 0
    member t = 1
    const SIZE = 2
end
func f(x, y : T, z : T*):
    x = 1; ap++
    y.s = 2; ap++
    z.t = y.t; ap++
    ret
end
"""
    program = preprocess_str(code=code, prime=PRIME)
    reference_x = program.instructions[-1].flow_tracking_data.resolve_reference(
        reference_manager=program.reference_manager, name=ScopedName.from_string('f.x'))
    assert reference_x.value.format() == 'cast([fp + (-6)], felt)'
    reference_y = program.instructions[-1].flow_tracking_data.resolve_reference(
        reference_manager=program.reference_manager, name=ScopedName.from_string('f.y'))
    assert reference_y.value.format() == 'cast([fp + (-5)], T)'
    reference_z = program.instructions[-1].flow_tracking_data.resolve_reference(
        reference_manager=program.reference_manager, name=ScopedName.from_string('f.z'))
    assert reference_z.value.format() == 'cast([fp + (-3)], T*)'
    assert program.format() == """\
[fp + (-6)] = 1; ap++
[fp + (-5)] = 2; ap++
[[fp + (-3)] + 1] = [fp + (-4)]; ap++
ret
"""


def test_func_args_failures():
    verify_exception("""
func f(x):
    [ap] = [x] + 1
end
""", """
file:?:?: While expanding the reference 'x' in:
    [ap] = [x] + 1
            ^
file:?:?: Expected a register. Found: [fp + (-3)].
func f(x):
       ^
Preprocessed instruction:
[ap] = [[fp + (-3)]] + 1
""", exc_type=InstructionBuilderError)
    verify_exception("""
func f(x):
    g(x=x)
end
func g(x):
    ret
end
""", """
file:?:?: The called function must be defined before the call site.
    g(x=x)
    ^****^
""")


def test_func_args_scope():
    code = """\
const x = 1234
[ap] = x; ap++
func f(x, y, z):
    x = 1; ap++
    y = 2; ap++
    z = 3; ap++
    ret
end
[ap + 4] = x; ap++
[ap + 5] = f.Args.z; ap++
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
[ap] = 1234; ap++
[fp + (-5)] = 1; ap++
[fp + (-4)] = 2; ap++
[fp + (-3)] = 3; ap++
ret
[ap + 4] = 1234; ap++
[ap + 5] = 2; ap++
"""


def test_func_args_and_rets_scope():
    code = """\
const x = 1234
[ap] = x; ap++
func f(x, y, z) -> (a, b, x):
    x = 1; ap++
    y = 2; ap++
    [ap] = Return.b; ap++
    ret
end
[ap + 4] = x; ap++
[ap + 5] = f.Args.x; ap++
[ap + 6] = f.Return.x; ap++
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
[ap] = 1234; ap++
[fp + (-5)] = 1; ap++
[fp + (-4)] = 2; ap++
[ap] = 1; ap++
ret
[ap + 4] = 1234; ap++
[ap + 5] = 0; ap++
[ap + 6] = 2; ap++
"""


def test_func_named_args():
    code = """\
func f(x, y, z):
    ret
end

let f_args = cast(ap, f.Args*)
f_args.z = 2; ap++
f_args.x = 0; ap++
f_args.y = 1; ap++
static_assert f_args + f.Args.SIZE == ap
call f
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
ret
[ap + 2] = 2; ap++
[ap + (-1)] = 0; ap++
[ap + (-1)] = 1; ap++
call rel -7
"""


def test_func_named_args_failures():
    verify_exception("""
func f(x, y, z):
    ret
end

let f_args = cast(ap, f.Args*)
f_args.z = 2; ap++
f_args.x = 0; ap++
static_assert f_args + f.Args.SIZE == ap
call f
""", """
file:?:?: Static assert failed: ap + 1 != ap.
static_assert f_args + f.Args.SIZE == ap
^**************************************^
""")


def test_function_call_by_value_args():
    code = """\
struct T:
    member s = 0
    member t = 1
    const SIZE = 2
end
func f(x, y : T, z : T):
    let t : T = cast([ap], T)
    let res = f(x=2, y=z, z=t)
    return()
end
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
[ap] = 2; ap++
[ap] = [fp + (-4)]; ap++
[ap] = [fp + (-3)]; ap++
[ap] = [ap + (-3)]; ap++
[ap] = [ap + (-3)]; ap++
call rel -6
ret
"""


@pytest.mark.parametrize('test_line, expected_type, actual_type, arrow', [
    ('f(1, y=13)', 'T', 'felt', '^^'),
    ('f(1, y=&y)', 'T', 'T*', '^^'),
    ('f(1, y=t)', 'T', 'S', '^'),
])
def test_func_by_value_args_failures(test_line, expected_type, actual_type, arrow):
    verify_exception(f"""
struct T:
    member s = 0
    member t = 1
    const SIZE = 2
end
struct S:
    member s = 0
    member t = 1
    const SIZE = 2
end
func f(x, y : {expected_type}):
    local t : {actual_type}
    alloc_locals
    {test_line}
    ret
end
""", f"""
file:?:?: Expected expression of type '{expected_type}', got '{actual_type}'.
    {test_line}
           {arrow}
""")


def test_func_by_value_discontinuous_struct_failures():
    verify_exception("""
struct T:
    member s = 0
    member t = 2
    const SIZE = 3
end
func f(x, y : T):
    f(1, y=y)
    ret
end
""", """
file:?:?: Discontinuous structs are not supported.
    f(1, y=y)
           ^
""")


def test_func_by_value_nested_struct_failures():
    verify_exception("""
struct S:
    const SIZE = 0
end

struct T:
    member s = 0
    member t : S = 1
    const SIZE = 2
end
func f(x, y : T):
    f(1, y=y)
    ret
end
""", """
file:?:?: Nested structs are not supported.
    f(1, y=y)
           ^
""")


def test_func_by_value_return():
    code = """\
struct T:
    member s = 0
    member t = 1
    const SIZE = 2
end
func f(s : T) -> (x : T, y : T):
    let t : T = cast([ap - 100], T)
    return(x=s, y=t)
end
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
[ap] = [fp + (-4)]; ap++
[ap] = [fp + (-3)]; ap++
[ap] = [ap + (-102)]; ap++
[ap] = [ap + (-102)]; ap++
ret
"""


def test_scope_label():
    code = """\
x:
jmp x
jmp f
call f
func f():
    jmp x
    x:
    jmp x
    jmp f.x
end
jmp x
jmp f.x
jmp f
call f
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
jmp rel 0
jmp rel 4
call rel 2
jmp rel 2
jmp rel 0
jmp rel -2
jmp rel -12
jmp rel -6
jmp rel -10
call rel -12
"""


def test_import():
    files = {
        '.': """
from a import f as g
call g
""",
        'a': """
func f():
  jmp f
end
"""
    }
    program = preprocess_codes(
        codes=[(files['.'], '.')], prime=PRIME, read_module=read_file_from_dict(files))

    assert program.format() == """\
jmp rel 0
call rel -2
"""


def test_import_identifiers():
    # Define files used in this test.
    files = {
        '.': """
from a.b.c import alpha as x
from a.b.c import beta
from a.b.c import xi
""",
        'a.b.c': """
from tau import xi
const alpha = 0
const beta = 1
const gamma = 2
""",
        'tau': """
const xi = 42
"""
    }

    # Prepare auxiliary functions for tests.
    scope = ScopedName.from_string

    def get_full_name(name, curr_scope=''):
        try:
            return program.identifiers.search(
                accessible_scopes=[scope(curr_scope)], name=scope(name)).get_canonical_name()
        except IdentifierError:
            return None

    # Preprocess program.
    program = preprocess_codes(
        codes=[(files['.'], '.')], prime=PRIME, read_module=read_file_from_dict(files),
        main_scope=scope('__main__'))

    # Verify identifiers are resolved correctly.
    assert get_full_name('x', '__main__') == scope('a.b.c.alpha')
    assert get_full_name('beta', '__main__') == scope('a.b.c.beta')
    assert get_full_name('xi', '__main__') == scope('tau.xi')

    assert get_full_name('alpha', 'a.b.c') == scope('a.b.c.alpha')
    assert get_full_name('beta', 'a.b.c') == scope('a.b.c.beta')
    assert get_full_name('gamma', 'a.b.c') == scope('a.b.c.gamma')
    assert get_full_name('xi', 'a.b.c') == scope('tau.xi')

    assert get_full_name('xi', 'tau') == scope('tau.xi')

    # Verify inaccessible identifiers.
    assert get_full_name('alpha', '__main__') is None
    assert get_full_name('gamma', '__main__') is None
    assert get_full_name('a.b.c.alpha', '__main__') is None
    assert get_full_name('tau.xi', '__main__') is None


def test_import_errors():
    # Inaccessible import.
    verify_exception("""
from foo import bar
""", """
file:?:?: Could not load module 'foo'.
Error: 'foo'
from foo import bar
     ^*^
""", files={}, exc_type=LocationError)

    # Ignoring aliasing.
    verify_exception("""
from foo import bar as notbar
[ap] = bar
""", """
file:?:?: Unknown identifier 'bar'.
[ap] = bar
       ^*^
""", files={'foo': 'const bar = 3'})

    # Identifier redefinition.
    verify_exception("""
const bar = 0
from foo import bar
""", """
file:?:?: Redefinition of 'bar'.
from foo import bar
                ^*^
""", files={'foo': 'const bar=0'})

    verify_exception("""
const lambda = 0
from foo import bar as lambda
""", """
file:?:?: Redefinition of 'lambda'.
from foo import bar as lambda
                       ^****^
""", files={'foo': 'const bar=0'})

    verify_exception('from foo import bar', """ \
file:?:?: Scope 'foo' does not include identifier 'bar'.
from foo import bar
                ^*^
""", files={'foo': ''})


def test_error_scope_redefinition():
    verify_exception("""
from a import b
from a.b import c
""", """
Scope 'a.b' collides with a different identifier of type 'const'.
""", files={'a': 'const b = 0', 'a.b': 'const c = 1'})


def test_scope_failures():
    verify_exception("""
func f():
const x = 5
ret
end
func g():
[ap] = x; ap++
ret
end
""", """
file:?:?: Unknown identifier 'x'.
[ap] = x; ap++
       ^
""")
    verify_exception("""
func f():
label:
ret
end
func g():
call label
ret
end
""", """
file:?:?: Unknown identifier 'label'.
call label
     ^***^
""")


def test_const_failures():
    verify_exception("""
const x = y
""", """
file:?:?: Unknown identifier 'y'.
const x = y
          ^
""")
    verify_exception("""
const x = 0
[ap] = x.y.z
""", """
file:?:?: Unexpected '.' after 'x' which is const.
[ap] = x.y.z
       ^***^
""")

    verify_exception("""
const x = [ap] + 5
""", """
file:?:?: Expected a constant expression.
const x = [ap] + 5
          ^******^
""")


def test_labels():
    scope = ScopedName.from_string('my.cool.scope')
    program = preprocess_str("""
const x = 7
a0:
[ap] = x; ap++  # Size: 2.
[ap] = [fp] + 123  # Size: 2.

a1:
[ap] = [fp]  # Size: 1.
jmp rel [fp]  # Size: 1.
a2:
jmp rel x  # Size: 2.
jmp a3  # Size: 2.
jmp a3 if [ap] != 0  # Size: 2.
call a3  # Size: 2.
a3:
""", prime=PRIME, main_scope=scope)
    program_labels = {
        name: identifier_definition.pc
        for name, identifier_definition in program.identifiers.get_scope(scope).identifiers.items()
        if isinstance(identifier_definition, LabelDefinition)}
    assert program_labels == {'a0': 0, 'a1': 4, 'a2': 6, 'a3': 14}


def test_process_file_scope():
    # Verify the good scenario.
    valid_scope = ScopedName.from_string('some.valid.scope')
    program = preprocess_str('const x = 4', prime=PRIME, main_scope=valid_scope)

    module = CairoModule(cairo_file=program, module_name=valid_scope)
    assert program.identifiers.as_dict() == {
        valid_scope + 'x': ConstDefinition(4)
    }


def test_label_resolution():
    program = preprocess_str(code="""
[ap] = 7; ap++  # Size: 2.

loop:
[ap] = [ap - 1] + 1  # Size: 2.
jmp future_label  # Size: 2.
jmp future_label if [ap] != 0  # Size: 2.
call future_label  # Size: 2.
[fp] = [fp]  # Size: 1.
future_label:
jmp loop   # Size: 2.
jmp loop if [ap] != 0  # Size: 2.
call loop  # Size 2.
""", prime=PRIME)
    assert program.format() == """\
[ap] = 7; ap++
[ap] = [ap + (-1)] + 1
jmp rel 7
jmp rel 5 if [ap] != 0
call rel 3
[fp] = [fp]
jmp rel -9
jmp rel -11 if [ap] != 0
call rel -13
"""


def test_labels_failures():
    verify_exception("""
jmp x.y.z
""", """
file:?:?: Unknown identifier 'x'.
jmp x.y.z
    ^***^
""")
    verify_exception("""
const x = 0
jmp x
""", """
file:?:?: Expected a label name. Identifier 'x' is of type const.
jmp x
    ^
""")


def test_redefinition_failures():
    verify_exception("""
name:
const name = 0
""", """
file:?:?: Redefinition of 'name'.
const name = 0
      ^**^
""")
    verify_exception("""
const name = 0
let name = ap
""", """
file:?:?: Redefinition of 'name'.
let name = ap
    ^**^
""")
    verify_exception("""
let name = ap
name:
""", """
file:?:?: Redefinition of 'name'.
name:
^**^
""")
    verify_exception("""
func f(name, x, name):
    [ap + name] = 1
    [ap + x] = 2
end
""", """
file:?:?: Redefinition of 'f.Args.name'.
func f(name, x, name):
                ^**^
""")
    verify_exception("""
func f() -> (name, x, name):
    [ap + name] = 1
    [ap + x] = 2
end
""", """
file:?:?: Redefinition of 'f.Return.name'.
func f() -> (name, x, name):
                      ^**^
""")


def test_directives():
    program = preprocess_str(code="""\
# This is a comment.


%builtins ab cd ef

[fp] = [fp]
""", prime=PRIME)
    assert program.builtins == ['ab', 'cd', 'ef']
    assert program.format() == """\
%builtins ab cd ef

[fp] = [fp]
"""


def test_directives_failures():
    verify_exception("""
[fp] = [fp]
%builtins ab cd ef
""", """
file:?:?: Directives must appear at the top of the file.
%builtins ab cd ef
^****************^
""")


def test_conditionals():
    program = preprocess_str(code="""
let x = 2
if [ap] * 2 == [fp] + 3:
    let x = 3
    [ap] = x; ap++
else:
    let x = 4
    [ap] = x; ap++
end
""", prime=PRIME)
    assert program.format() == """\
[ap] = [ap] * 2; ap++
[ap] = [fp] + 3; ap++
[ap] = [ap + (-2)] - [ap + (-1)]; ap++
jmp rel 6 if [ap + (-1)] != 0
[ap] = 3; ap++
jmp rel 4
[ap] = 4; ap++
"""
    program = preprocess_str(code="""
if [ap] == [fp]:
    ret
else:
    [ap] = [ap]
end
[fp] = [fp]
""", prime=PRIME)
    assert program.format() == """\
[ap] = [ap] - [fp]; ap++
jmp rel 3 if [ap + (-1)] != 0
ret
[ap] = [ap]
[fp] = [fp]
"""
    program = preprocess_str(code="""
if [ap] == 0:
    ret
end
[fp] = [fp]
""", prime=PRIME)
    assert program.format() == """\
jmp rel 3 if [ap] != 0
ret
[fp] = [fp]
"""
    # No jump if there is no "Non-equal" block.
    program = preprocess_str(code="""
if [ap] == 0:
    [fp + 1] = [fp + 1]
end
[fp] = [fp]
""", prime=PRIME)
    assert program.format() == """\
jmp rel 3 if [ap] != 0
[fp + 1] = [fp + 1]
[fp] = [fp]
"""
    program = preprocess_str(code="""
if [ap] != 0:
    ret
end
[fp] = [fp]
""", prime=PRIME)
    assert program.format() == """\
jmp rel 4 if [ap] != 0
jmp rel 3
ret
[fp] = [fp]
"""
    # With locals.
    program = preprocess_str(code="""
func a():
    alloc_locals
    local a
    if [ap] != 0:
        local b = 7
        a = 5
    else:
        # This is a different local named b also.
        local b = 6
        # This is the same local defined above.
        a = 3
    end
    [fp] = [fp]
    ret
end
""", prime=PRIME)
    assert program.format() == """\
ap += 3
jmp rel 8 if [ap] != 0
[fp + 2] = 6
[fp] = 3
jmp rel 6
[fp + 1] = 7
[fp] = 5
[fp] = [fp]
ret
"""


def test_hints():
    code = """\
%{ hint0 %}
[fp] = [fp]
%{
    hint1
    hint2
%}
[fp] = [fp]
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == code


def test_hints_unindent():
    before = """\
  %{
      hint1
      hint2
%}
[fp] = [fp]
func f():
  %{
       if a:
           b
%}
[fp] = [fp]
ret
end
"""
    after = """\
%{
    hint1
    hint2
%}
[fp] = [fp]
%{
    if a:
        b
%}
[fp] = [fp]
ret
"""
    program = preprocess_str(code=before, prime=PRIME)
    assert program.format() == after


def test_hints_failures():
    verify_exception("""
%{
hint
%}
""", """
file:?:?: Found a hint at the end of a code block. Hints must be followed by an instruction.
%{
^^
""")
    verify_exception("""
func f():
%{
hint
%}
end
[ap] = 1
""", """
file:?:?: Found a hint at the end of a code block. Hints must be followed by an instruction.
%{
^^
""")
    verify_exception("""
%{
hint1
%}
%{
hint2
%}
""", """
file:?:?: Only one hint is allowed per instruction.
%{
^^
""")
    verify_exception("""
[fp] = [fp]
%{
hint
%}
label:
[fp] = [fp]
""", """
file:?:?: Hints before labels are not allowed.
%{
^^
""")
    verify_exception("""
[fp] = [fp]
%{
hint
%}
const x = 5
[fp] = [fp]
""", """
file:?:?: Hints before constant definitions are not allowed.
%{
^^
""")


def test_builtins_failures():
    verify_exception("""
%builtins a
%builtins b
""", """
file:?:?: Redefinition of builtins directive.
%builtins b
^*********^
""")


def test_references():
    program = preprocess_str(code="""
call label1
label1:
ret

let x = ap + 1
label2:
[x] = 1; ap++
[x + 3] = 2; ap++
[x - 2] = 3; ap++
[x - 2] = 3; ap++
jmp label1 if [x] != 0; ap++
jmp label3 if [x] != 0
[x - 2] = 4
[x - 4] = 5
[x - 6] = 6; ap++
[ap] = [ap]; ap++
ap += 4
[x] = 7

call label3
label3:
ret

let y = ap
[y] = 0; ap++
[y] = 0; ap++
""", prime=PRIME)
    assert program.format() == """\
call rel 2
ret
[ap + 1] = 1; ap++
[ap + 3] = 2; ap++
[ap + (-3)] = 3; ap++
[ap + (-4)] = 3; ap++
jmp rel -9 if [ap + (-3)] != 0; ap++
jmp rel 15 if [ap + (-4)] != 0
[ap + (-6)] = 4
[ap + (-8)] = 5
[ap + (-10)] = 6; ap++
[ap] = [ap]; ap++
ap += 4
[ap + (-10)] = 7
call rel 2
ret
[ap] = 0; ap++
[ap + (-1)] = 0; ap++
"""


def test_reference_type_deduction():
    program = preprocess_str(code="""
struct T:
    const SIZE = 0
end

func foo():
    let a = cast(0, T***)
    tempvar b = [a]
    tempvar c : felt* = [a]
    let d = [b]
    let e : felt* = [b]
    return ()
end
""", prime=PRIME)

    def get_reference_type(name):
        identifier_definition = program.identifiers.get_by_full_name(ScopedName.from_string(name))
        assert isinstance(identifier_definition, ReferenceDefinition)
        assert len(identifier_definition.references) == 1
        _, expr_type = simplify_type_system(identifier_definition.references[0].value)
        return expr_type

    assert get_reference_type('foo.a').format() == 'T***'
    assert get_reference_type('foo.b').format() == 'T**'
    assert get_reference_type('foo.c').format() == 'felt*'
    assert get_reference_type('foo.d').format() == 'T*'
    assert get_reference_type('foo.e').format() == 'felt*'


def test_rebind_reference():
    program = preprocess_str(code="""
struct T:
    member t = 100
end
struct S:
    member s = 1000
end
let x : T* = cast(ap + 1, T*)
let y = &x.t
[cast(x, felt)] = x.t
let x : S* = cast(fp - 3, S*)
[cast(x, felt)] = x.s
[y] = [y]
""", prime=PRIME)
    assert program.format() == """\
[ap + 1] = [ap + 101]
[fp + (-3)] = [fp + 997]
[ap + 101] = [ap + 101]
"""


def test_reference_over_calls():
    program = preprocess_str(code="""
func f():
    ap += 3
    jmp label1 if [ap] != 0; ap++
    [ap] = [ap]; ap++
    ret
    label1:
    ap += 1
    ret
end

let x = ap + 1
[x] = 0
call f
[x] = 0
""", prime=PRIME)
    assert program.format() == """\
ap += 3
jmp rel 4 if [ap] != 0; ap++
[ap] = [ap]; ap++
ret
ap += 1
ret
[ap + 1] = 0
call rel -11
[ap + (-6)] = 0
"""


def test_reference_over_calls_failures():
    verify_exception(f"""
func f():
    ap += 3
    jmp label1 if [ap] != 0
    [ap] = [ap]; ap++
    label1:
    ret
end

let x = ap + 1
call f
[x] = 0
""", """
file:?:?: Reference 'x' was revoked.
[x] = 0
 ^
""")

    verify_exception(f"""
func f():
    ap += 3
    jmp label1 if [ap] != 0
    [ap] = [ap]; ap++
    ret
    label1:
    ret
end

let x = ap + 1
call f
[x] = 0
""", """
file:?:?: Reference 'x' was revoked.
[x] = 0
 ^
""")


@pytest.mark.parametrize('revoking_instruction', [
    'ap += [fp]',
    'call label',
    'call rel 0',
    'ret',
    'jmp label',
    'jmp rel 0',
    'jmp abs 0',
])
def test_references_revoked(revoking_instruction):
    verify_exception(f"""
label:
let x = ap
{revoking_instruction}
[x] = 0
""", """
file:?:?: Reference 'x' was revoked.
[x] = 0
 ^
""")


def test_references_failures():
    verify_exception(f"""
let ref = [fp]
let ref2 = ref
[ref2] = [[fp]]
""", """
file:?:?: While expanding the reference 'ref2' in:
[ref2] = [[fp]]
 ^**^
file:?:?: While expanding the reference 'ref' in:
let ref2 = ref
           ^*^
file:?:?: Expected a register. Found: [fp].
let ref = [fp]
          ^**^
Preprocessed instruction:
[[fp]] = [[fp]]
""", exc_type=InstructionBuilderError)


@pytest.mark.parametrize('valid, has0, has1, has2', [
    (False, True, True, True),
    (False, False, True, True),
    (False, True, False, True),
    (False, True, True, False),
    (False, False, True, False),
    (False, False, False, True),
    (True, True, False, False),
])
def test_reference_flow_revokes(valid, has0, has1, has2):
    def0 = 'let ref = [fp]' if has0 else ''
    def1 = 'let ref = [fp + 1]' if has1 else ''
    def2 = 'let ref = [fp + 2]' if has2 else ''
    code = f"""
{def0}
jmp b if [ap] != 0
a:
{def1}
jmp c
b:
{def2}
c:
[ref] = [fp + 3]
"""
    if valid:
        preprocess_str(code, prime=PRIME)
    else:
        verify_exception(code, """
file:?:?: Reference 'ref' was revoked.
[ref] = [fp + 3]
 ^*^
""")


def test_reference_flow_converge():
    program = preprocess_str("""
if [ap] != 0:
    tempvar a = 1
else:
    tempvar a = 2
end

assert a = a
""", prime=PRIME)
    assert program.format() == """\
jmp rel 6 if [ap] != 0
[ap] = 2; ap++
jmp rel 4
[ap] = 1; ap++
[ap + (-1)] = [ap + (-1)]
"""


def test_typed_references():
    program = preprocess_str(code="""
func main():
    struct T:
        member b : T* = 3
    end

    struct Struct:
        member a : T* = 2
    end

    let x : Struct* = cast(ap + 10, Struct*)
    let y : Struct = [x]

    [fp] = x.a
    assert [fp] = x.a.b
    assert [fp] = x.a.b.b

    [fp] = y.a + 1
    ret
end
""", prime=PRIME)
    scope = ScopedName.from_string

    assert isinstance(program.identifiers.get_by_full_name(scope('main.x')), ReferenceDefinition)
    expected_type_x = mark_type_resolved(parse_type('main.Struct*'))
    reference = program.instructions[-1].flow_tracking_data.resolve_reference(
        reference_manager=program.reference_manager, name=scope('main.x'))
    assert simplify_type_system(reference.value)[1] == \
        expected_type_x

    assert isinstance(program.identifiers.get_by_full_name(scope('main.y')), ReferenceDefinition)
    expected_type_y = mark_type_resolved(parse_type('main.Struct'))
    reference = program.instructions[-1].flow_tracking_data.resolve_reference(
        reference_manager=program.reference_manager, name=scope('main.y'))
    assert simplify_type_system(reference.value)[1] == \
        expected_type_y

    assert reference.value.format() == \
        'cast([ap + 10], main.Struct)'
    assert program.format() == """\
[fp] = [ap + 12]
[fp] = [[ap + 12] + 3]
[ap] = [[ap + 12] + 3]; ap++
[fp] = [[ap + (-1)] + 3]
[fp] = [ap + 11] + 1
ret
"""


def test_typed_references_failures():
    verify_exception(f"""
struct T:
    const z = 0
end

let x : T* = cast(ap, T*)
x.z = x.z
""", """
file:?:?: Expected reference offset 'T.z' to be a member, found const.
x.z = x.z
^*^
""")
    verify_exception(f"""
let x = fp
x.a = x.a
""", """
file:?:?: Member access requires a type of the form Struct*.
x.a = x.a
^*^
""")
    verify_exception(f"""
struct T:
    member z = 0
end

let x : T = ap
x.z = x.z
""", """
file:?:?: Cannot assign an expression of type 'felt' to a reference of type 'T'.
let x : T = ap
        ^
""")
    verify_exception(f"""
struct T:
    member z = 0
end

let x : T* = cast([ap], T)
""", """
file:?:?: Cannot assign an expression of type 'T' to a reference of type 'T*'.
let x : T* = cast([ap], T)
        ^^
""")


def test_return_value_reference():
    program = preprocess_str(code="""
func foo() -> (val, x, y):
    ret
end

func main():
    let x = call foo
    [ap] = 0; ap++
    x.val = 9

    let y : main.Return = call foo

    let z = call abs 0
    ret
end
""", prime=PRIME)
    scope = ScopedName.from_string

    assert isinstance(program.identifiers.get_by_full_name(scope('main.x')), ReferenceDefinition)
    expected_type = mark_type_resolved(parse_type(f'foo.{CodeElementFunction.RETURN_SCOPE}'))
    reference = program.instructions[-1].flow_tracking_data.resolve_reference(
        reference_manager=program.reference_manager, name=scope('main.x'))
    assert simplify_type_system(reference.value)[1] == expected_type

    assert isinstance(program.identifiers.get_by_full_name(scope('main.y')), ReferenceDefinition)
    expected_type = mark_type_resolved(parse_type(f'main.{CodeElementFunction.RETURN_SCOPE}'))
    reference = program.instructions[-1].flow_tracking_data.resolve_reference(
        reference_manager=program.reference_manager, name=scope('main.y'))
    assert simplify_type_system(reference.value)[1] == expected_type

    assert isinstance(program.identifiers.get_by_full_name(scope('main.z')), ReferenceDefinition)
    expected_type = parse_type('felt')
    reference = program.instructions[-1].flow_tracking_data.resolve_reference(
        reference_manager=program.reference_manager, name=scope('main.z'))
    assert simplify_type_system(reference.value)[1] == expected_type

    assert program.format() == """\
ret
call rel -1
[ap] = 0; ap++
[ap + (-4)] = 9
call rel -7
call abs 0
ret
"""


def test_return_value_reference_failures():
    verify_exception(f"""
let x = call foo
""", """
file:?:?: Unknown identifier 'foo'.
let x = call foo
             ^*^
""")
    verify_exception(f"""
func foo():
  ret
end
let x = call foo
[x.a] = 0
""", """
file:?:?: Member 'foo.Return.a' was not found.
[x.a] = 0
 ^*^
""")
    verify_exception(f"""
func foo():
    ret
end
let x : unknown_type* = call foo
""", """
file:?:?: Unknown identifier 'unknown_type'.
let x : unknown_type* = call foo
        ^**********^
""")
    verify_exception(f"""
struct T:
  const s = 1000
end
let x : T* = cast(ap, T*)
[ap] = x.a
""", """
file:?:?: Member 'T.a' was not found.
[ap] = x.a
       ^*^
""")


def test_unpacking():
    code = """\
struct T:
    member a = 0
    member b = 1
    const SIZE = 2
end
func f() -> (a, b, c, d , e : T):
    return (...)
end
func g():
    alloc_locals
    let (a, local b, local c, d : T*, e) = f()
    a = d.b
    a = b + c; ap++
    a = b + c
    # The type of e is deduced from the return type of f().
    a = e.b
    ret
end
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
ret
ap += 2
call rel -3
[fp] = [ap + (-5)]
[fp + 1] = [ap + (-4)]
[ap + (-6)] = [[ap + (-3)] + 1]
[ap + (-6)] = [fp] + [fp + 1]; ap++
[ap + (-7)] = [fp] + [fp + 1]
[ap + (-7)] = [ap + (-2)]
ret
"""


def test_unpacking_failures():
    verify_exception(f"""
func foo() -> (a):
  ret
end
let (a, b) = foo()
""", """
file:?:?: Expected 1 unpacking identifier, found 2.
let (a, b) = foo()
     ^**^
""")

    verify_exception(f"""
let (a, b) = 1 + 3
""", """
file:?:?: Cannot unpack 1 + 3.
let (a, b) = 1 + 3
             ^***^
""")

    verify_exception(f"""
struct T:
    member a = 0
    member b = 1
    const SIZE = 2
end
func foo() -> (a, b : T):
  ret
end
let (a, b, c) = foo()
""", """
file:?:?: Expected 2 unpacking identifiers, found 3.
let (a, b, c) = foo()
     ^*****^
""")

    verify_exception(f"""
struct T:
    member a = 0
    member b = 1
    const SIZE = 2
end
func foo() -> (a, b):
  ret
end
let (a, b : T) = foo()
""", """
file:?:?: Expected expression of type 'felt', got 'T'.
let (a, b : T) = foo()
        ^***^
""")

    verify_exception(f"""
struct T:
    member a = 0
    member b = 1
    const SIZE = 2
end
func foo() -> (a, b : T):
  ret
end
func test():
    alloc_locals
    let (a, local b : T) = foo()
    ret
end
""", """
file:?:?: Expected a 'felt' or a pointer type. Got: 'T'.
    let (a, local b : T) = foo()
                  ^
""")

    verify_exception(f"""
func foo() -> (a):
  ret
end
let (a) = foo()
[a] = [a]
""", """
file:?:?: While expanding the reference 'a' in:
[a] = [a]
 ^
file:?:?: Expected a register. Found: [ap + (-1)].
let (a) = foo()
     ^
Preprocessed instruction:
[[ap + (-1)]] = [[ap + (-1)]]
""", exc_type=InstructionBuilderError)


def test_unpacking_modifier_failure():
    verify_exception("""
func foo() -> (a, b):
  ret
end
let (a, local b) = foo()
""", """
file:?:?: Unexpected modifier 'local'.
let (a, local b) = foo()
        ^***^
""")


def test_member_def_failure():
    verify_exception("""
struct T:
    member t = ap + 5
end
""", """
file:?:?: Expected a constant expression.
    member t = ap + 5
               ^****^
""")


def test_member_def_modifier_failure():
    verify_exception("""
struct T:
    member local t = 17
end
""", """
file:?:?: Unexpected modifier 'local'.
    member local t = 17
           ^***^
""")
