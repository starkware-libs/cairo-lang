import pytest

from starkware.cairo.lang.compiler.ast.code_elements import CodeElementFunction
from starkware.cairo.lang.compiler.ast.module import CairoModule
from starkware.cairo.lang.compiler.error_handling import LocationError
from starkware.cairo.lang.compiler.identifier_definition import (
    ConstDefinition, LabelDefinition, ReferenceDefinition)
from starkware.cairo.lang.compiler.identifier_manager import IdentifierError
from starkware.cairo.lang.compiler.instruction_builder import InstructionBuilderError
from starkware.cairo.lang.compiler.parser import parse_type
from starkware.cairo.lang.compiler.preprocessor.default_pass_manager import default_pass_manager
from starkware.cairo.lang.compiler.preprocessor.preprocess_codes import preprocess_codes
from starkware.cairo.lang.compiler.preprocessor.preprocessor_test_utils import (
    PRIME, TEST_SCOPE, preprocess_str, strip_comments_and_linebreaks, verify_exception)
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.test_utils import read_file_from_dict
from starkware.cairo.lang.compiler.type_casts import CairoTypeError
from starkware.cairo.lang.compiler.type_system import mark_type_resolved
from starkware.cairo.lang.compiler.type_system_visitor import simplify_type_system


def test_compiler():
    program = preprocess_str(code="""

const x = 5
const y = 2 * x
[ap] = [[fp + 2 * 0x3] + ((7 - 1 + y))]; ap++
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


def test_pow_failure():
    verify_exception("""\
func foo(x : felt):
    tempvar y = x ** 2
end
""", """
file:?:?: Operator '**' is only supported for constant values.
    tempvar y = x ** 2
                ^****^
""")
    verify_exception("""\
const X = 2
const Y = 2 ** (2 * 3)
const Z = 2 ** (X * 3)
""", """
file:?:?: Identifier 'X' is not allowed in this context.
const Z = 2 ** (X * 3)
                ^
""", exc_type=CairoTypeError)


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
    member pad0 : felt
    member t : felt
end
tempvar x = [ap - 1] + [fp - 3]
ap += 3
tempvar y : T* = cast(x, T*)
ap += 4
[fp] = y.t
ap += 5
tempvar z : (felt, felt) = (1, 2)
# Check the expression pushing optimization.
tempvar z : (felt, felt) = ([ap - 1], 3)
tempvar q : T
assert q.t = 0
tempvar w
tempvar h = nondet %{ 5**i %}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
[ap] = [ap + (-1)] + [fp + (-3)]; ap++
ap += 3
[ap] = [ap + (-4)]; ap++
ap += 4
[fp] = [[ap + (-5)] + 1]
ap += 5
[ap] = 1; ap++
[ap] = 2; ap++
[ap] = 3; ap++
ap += 2
[ap + (-1)] = 0
ap += 1
%{ memory[ap] = int(5**i) %}
ap += 1
"""


def test_temporary_variable_failures():
    verify_exception("""
tempvar x : felt = cast([ap], felt*)
""", """
file:?:?: Cannot assign an expression of type 'felt*' to a temporary variable of type 'felt'.
tempvar x : felt = cast([ap], felt*)
            ^**^
""")
    verify_exception("""
tempvar _ = 0
""", """
file:?:?: Reference name cannot be '_'.
tempvar _ = 0
        ^
""")
    verify_exception("""
struct T:
    member x : felt
    member y : felt
end
tempvar a : T = nondet %{ 1 %}
""", """
file:?:?: Hint tempvars must be of type felt.
tempvar a : T = nondet %{ 1 %}
                ^************^
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

    tempvar z = 5
    tempvar x = 1
    tempvar y = 2
    return (x, y, z)

    tempvar x = 1
    tempvar y = 2
    return (x, y, x + x + y)
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
[ap] = 5; ap++
[ap] = 1; ap++
[ap] = 2; ap++
[ap] = [ap + (-3)]; ap++
ret
[ap] = 1; ap++
[ap] = 2; ap++
[ap] = [ap + (-2)] + [ap + (-2)]; ap++
[ap] = [ap + (-3)]; ap++
[ap] = [ap + (-3)]; ap++
[ap] = [ap + (-3)] + [ap + (-4)]; ap++
ret
ret
"""


def test_return_failures():
    # Named after positional.
    verify_exception("""
func f() -> (a, b, c):
    return (a=1, b=1, [fp] + 1)
end
""", """
file:?:?: Positional arguments must not appear after named arguments.
    return (a=1, b=1, [fp] + 1)
                      ^******^
""")
    # Wrong num.
    verify_exception("""
func f() -> (a, b, c, d):
    return (1, [fp] + 1)
end
""", """
file:?:?: Expected exactly 4 expressions, got 2.
    return (1, [fp] + 1)
    ^******************^
""")
    # Wrong num.
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
    return (a=1, d=1, [fp] + 1)
end
""", """
file:?:?: Expected named arg 'b' found 'd'.
    return (a=1, d=1, [fp] + 1)
                 ^
""")
    # Not in func.
    verify_exception("""
return (a=1, [fp] + 1)
""", """
file:?:?: return cannot be used outside of a function.
return (a=1, [fp] + 1)
^********************^
""")


def test_tail_call():
    code = """\
func f(a) -> (a):
    return f(a)
end
func g(a, b) -> (a):
    return f(a)
end
"""
    program = preprocess_str(
        code=code, prime=PRIME, main_scope=ScopedName.from_string('test_scope'))
    assert program.format() == """\
[ap] = [fp + (-3)]; ap++
call rel -1
ret
[ap] = [fp + (-4)]; ap++
call rel -5
ret
"""


def test_tail_call_failure():
    verify_exception("""
func g() -> (a):
    return (a=0)
end
return g()
""", """
file:?:?: return cannot be used outside of a function.
return g()
^********^
""")

    verify_exception("""
func g() -> (a):
    return (a=0)
end
func f(x, y) -> (a, b, c, d, e):
    return g()
end
""", """
file:?:?: Cannot convert the return type of g to the return type of f.
    return g()
           ^*^
""")

    verify_exception("""
func g{x}() -> (a):
    return (a=0)
end
func f(x, y) -> (a):
    with x:
        return g()
    end
end
""", """
file:?:?: Cannot convert the implicit arguments of g to the implicit arguments of f.
        return g()
               ^*^
""")

    verify_exception("""
func f(x, y) -> (a, b, c, d, e):
    return g()
end
""", """
file:?:?: Unknown identifier 'g'.
    return g()
           ^
""")

    verify_exception("""
func g(x, y) -> (a : felt):
    return (a=5)
end
func f(x, y) -> (a : felt*):
    return g(x, y)
end
""", """
file:?:?: Cannot convert the return type of g to the return type of f.
    return g(x, y)
           ^*****^
""")


def test_function_call():
    code = """\
func foo(a, b) -> (c):
    bar(a=a)
    return (1)
end
func bar(a):
    return ()
end
foo(2, 3)
foo(2, b=3)
let res = foo(a=2, b=3)
res.c = 1
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
[ap] = [fp + (-4)]; ap++
call rel 5
[ap] = 1; ap++
ret
ret
[ap] = 2; ap++
[ap] = 3; ap++
call rel -11
[ap] = 2; ap++
[ap] = 3; ap++
call rel -17
[ap] = 2; ap++
[ap] = 3; ap++
call rel -23
[ap + (-1)] = 1
"""


def test_func_args():
    scope = TEST_SCOPE
    code = """\
struct T:
    member s : felt
    member t : felt
end
func f(x, y : T, z : T*):
    x = 1; ap++
    y.s = 2; ap++
    z.t = y.t; ap++
    ret
end
"""
    program = preprocess_str(code=code, prime=PRIME, main_scope=scope)
    reference_x = program.instructions[-1].flow_tracking_data.resolve_reference(
        reference_manager=program.reference_manager, name=scope + 'f.x')
    assert reference_x.value.format() == '[cast(fp + (-6), felt*)]'
    reference_y = program.instructions[-1].flow_tracking_data.resolve_reference(
        reference_manager=program.reference_manager, name=scope + 'f.y')
    assert reference_y.value.format() == f'[cast(fp + (-5), {scope}.T*)]'
    reference_z = program.instructions[-1].flow_tracking_data.resolve_reference(
        reference_manager=program.reference_manager, name=scope + 'f.z')
    assert reference_z.value.format() == f'[cast(fp + (-3), {scope}.T**)]'
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


def test_with_statement():
    code = """
let x = 1000
[ap] = 0
with x:
    [ap] = 1
    [ap] = 2
    [ap] = x
    let x = 1001
end
[ap] = x
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
[ap] = 0
[ap] = 1
[ap] = 2
[ap] = 1000
[ap] = 1001
"""


def test_with_statement_locals():
    code = """
func foo() -> (z):
    ret
end

func bar():
    alloc_locals
    local x = 0
    with x:
        let (local z) = foo()
    end
    ret
end
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
ret
ap += 2
[fp] = 0
call rel -5
[fp + 1] = [ap + (-1)]
ret
"""


def test_with_statement_failure():
    verify_exception("""
with x:
    [ap] = [ap]
end
""", """
file:?:?: Unknown reference 'x'.
with x:
     ^
""")
    verify_exception("""
const x = 0
with x:
    [ap] = [ap]
end
""", """
file:?:?: Expected 'x' to be a reference, found: const.
with x:
     ^
""")
    verify_exception("""
let x = 0
with x as y:
    [ap] = [ap]
end
""", """
file:?:?: The 'as' keyword is not supported in 'with' statements.
with x as y:
          ^
""")


def test_implicit_args():
    code = """\
struct T:
    member a : felt
    member b : felt
end

func f{x: T}() -> ():
    # Rebind x.
    let x = [cast(fp - 1234, T*)]
    return ()
end

func g{x: T, y}(z, w) -> (res):
    x.a = 0
    x.b = 1
    y = 2
    z = 3
    w = 4
    # Rebind y. This affects the implicit return values.
    let y = z
    # We don't need a 'with' statement, since x and y are implicit arguments.
    f()
    return (res=z + w)
end

func h():
    let y = 10
    let x: T = [cast(fp - 100, T*)]
    with x, y:
        let (res2) = g(0, 0)
    end
    # Below, x and y refer to the implicit return values.
    tempvar a = x.a + y
    tempvar b = res2
    ret
end
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
[ap] = [fp + (-1234)]; ap++
[ap] = [fp + (-1233)]; ap++
ret
[fp + (-7)] = 0
[fp + (-6)] = 1
[fp + (-5)] = 2
[fp + (-4)] = 3
[fp + (-3)] = 4
[ap] = [fp + (-7)]; ap++
[ap] = [fp + (-6)]; ap++
call rel -15
[ap] = [fp + (-4)]; ap++
[ap] = [fp + (-4)] + [fp + (-3)]; ap++
ret
[ap] = [fp + (-100)]; ap++
[ap] = [fp + (-99)]; ap++
[ap] = 10; ap++
[ap] = 0; ap++
[ap] = 0; ap++
call rel -25
[ap] = [ap + (-4)] + [ap + (-2)]; ap++
[ap] = [ap + (-2)]; ap++
ret
"""


def test_implicit_args_failures():
    verify_exception("""
func f{x}(x):
    ret
end
""", """
file:?:?: Arguments and return values cannot have the same name of an implicit argument.
func f{x}(x):
          ^
""")
    verify_exception("""
func f{x}() -> (x):
    ret
end
""", """
file:?:?: Arguments and return values cannot have the same name of an implicit argument.
func f{x}() -> (x):
                ^
""")
    verify_exception("""
func f{x}():
    ret
end

func g():
    f()
    ret
end
""", """
file:?:?: While trying to retrieve the implicit argument 'x' in:
    f()
    ^*^
file:?:?: Unknown identifier 'x'.
func f{x}():
       ^
""")
    verify_exception("""
func f{x}(y):
    ret
end
func g(x):
    with x:
        f(0)
    end
    # This should fail, as it is outside the "with x".
    f(1)
    ret
end
""", """
file:?:?: While trying to update the implicit return value 'x' in:
    f(1)
    ^**^
file:?:?: 'x' cannot be used as an implicit return value. Consider using a 'with' statement.
func f{x}(y):
       ^
""")
    verify_exception("""
func f{x}():
    let x = cast(0, felt*)
    return ()
end
""", """
file:?:?: Reference rebinding must preserve the reference type. Previous type: 'felt', new type: \
'felt*'.
    let x = cast(0, felt*)
        ^
""")
    verify_exception("""
func f{x}():
    ret
end
func g():
    const x = 0
    f()
    ret
end
""", """
file:?:?: While trying to update the implicit return value 'x' in:
    f()
    ^*^
file:?:?: Redefinition of 'test_scope.g.x'.
func f{x}():
       ^
""")


def test_implcit_argument_bindings():
    code = """\
func f{x, y}():
    ret
end

func g{x, y, z}():
    f{y=z}()
    return ()
end
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
ret
[ap] = [fp + (-5)]; ap++
[ap] = [fp + (-3)]; ap++
call rel -3
[ap] = [ap + (-2)]; ap++
[ap] = [fp + (-4)]; ap++
[ap] = [ap + (-3)]; ap++
ret
"""


def test_implcit_argument_bindings_failures():
    verify_exception("""
func foo{x}(y) -> (z):
    ret
end

func bar():
    let x = foo{5}(0)
    ret
end
""", """
file:?:?: Implicit argument binding must be of the form: arg_name=var.
    let x = foo{5}(0)
                ^
""")
    verify_exception("""
func foo{x}(y) -> (z):
    ret
end

func bar():
    let x = 0
    let (res) = foo{y=x}(0)
    ret
end
""", """
file:?:?: Unexpected implicit argument binding: y.
    let (res) = foo{y=x}(0)
                    ^
""")
    verify_exception("""
func foo{x}(y) -> (z):
    ret
end

func bar():
    foo{x=2}(0)
    ret
end
""", """
file:?:?: Implicit argument binding must be an identifier.
    foo{x=2}(0)
          ^
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
struct S:
    member a : felt
    member b : felt
end

struct T:
    member s : felt
    member t : S
end
func f(x, y : T, z : T):
    let t : T = [cast(ap, T*)]
    let res = f(x=2, y=z, z=t)
    return()
end
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
[ap] = 2; ap++
[ap] = [fp + (-5)]; ap++
[ap] = [fp + (-4)]; ap++
[ap] = [fp + (-3)]; ap++
[ap] = [ap + (-4)]; ap++
[ap] = [ap + (-4)]; ap++
[ap] = [ap + (-4)]; ap++
call rel -8
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
    member s : felt
    member t : felt
end
struct S:
    member s : felt
    member t : felt
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
""", main_scope=ScopedName())


def test_func_by_value_return():
    code = """\
struct T:
    member s : felt
    member t : felt
end
func f(s : T) -> (x : T, y : T):
    let t : T = [cast(ap - 100, T*)]
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


@pytest.mark.parametrize('jmp_code', [
    'jmp loop if [ap] != 0',
    'jmp rel 3',
    'jmp abs 3',
    'jmp rel [ap + 3] if [ap] != 0',
])
def test_function_flow_revoke(jmp_code):
    verify_exception(f"""
func foo():
    loop:
    {jmp_code}
    ret
end

func bar():
    tempvar x = 0
    foo()
    assert x = 0
    ret
end
""", """
file:?:?: Reference 'x' was revoked.
    assert x = 0
           ^
Reference was defined here:
file:?:?
    tempvar x = 0
            ^
""")


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
from a import f as g, h as h2
call g
call h2
""",
        'a': """
func f():
  jmp f
end

func h():
  jmp h
end
"""
    }
    program = preprocess_codes(
        codes=[(files['.'], '.')],
        pass_manager=default_pass_manager(prime=PRIME, read_module=read_file_from_dict(files)))

    assert program.format() == """\
jmp rel 0
jmp rel 0
call rel -4
call rel -4
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
        codes=[(files['.'], '.')],
        pass_manager=default_pass_manager(prime=PRIME, read_module=read_file_from_dict(files)),
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
file:?:?: Redefinition of 'test_scope.bar'.
from foo import bar
                ^*^
""", files={'foo': 'const bar=0'})

    verify_exception(f"""
const lambda = 0
from foo import bar as lambda
""", """
file:?:?: Redefinition of 'test_scope.lambda'.
from foo import bar as lambda
                       ^****^
""", files={'foo': 'const bar=0'})

    verify_exception('from foo import bar', """ \
file:?:?: Cannot import 'bar' from 'foo'.
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
file:?:?: Unexpected '.' after 'test_scope.x' which is const.
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
file:?:?: Redefinition of 'test_scope.name'.
const name = 0
      ^**^
""")
    verify_exception("""
const name = 0
let name = ap
""", """
file:?:?: Redefinition of 'test_scope.name'.
let name = ap
    ^**^
""")
    verify_exception("""
let name = ap
name:
""", """
file:?:?: Redefinition of 'test_scope.name'.
name:
^**^
""")
    verify_exception("""
func f(name, x, name):
    [ap + name] = 1
    [ap + x] = 2
end
""", """
file:?:?: Redefinition of 'test_scope.f.Args.name'.
func f(name, x, name):
                ^**^
""")
    verify_exception("""
func f() -> (name, x, name):
    [ap] = 1
    [ap] = 2
end
""", """
file:?:?: Redefinition of 'test_scope.f.Return.name'.
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
    verify_exception("""
%lang abc
""", """
file:?:?: Unsupported %lang directive. Are you using the correct compiler?
%lang abc
^*******^
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


def test_hints_good():
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


def test_builtins_failures():
    verify_exception("""
%builtins a
%builtins b
""", """
file:?:?: Redefinition of builtins directive.
%builtins b
^*********^
""")


def test_builtin_directive_duplicate_entry():
    verify_exception("""
%builtins pedersen ecdsa pedersen
""", """
file:?:?: The builtin 'pedersen' appears twice in builtins directive.
%builtins pedersen ecdsa pedersen
^*******************************^
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
    scope = TEST_SCOPE
    program = preprocess_str(code="""
struct T:
    member t : felt
end

func foo():
    let a = cast(0, T***)
    tempvar b = [a]
    tempvar c : felt* = [a]
    let d = [b]
    let e : felt* = [b]
    return ()
end
""", prime=PRIME, main_scope=scope)

    def get_reference_type(name):
        identifier_definition = program.identifiers.get_by_full_name(scope + name)
        assert isinstance(identifier_definition, ReferenceDefinition)
        assert len(identifier_definition.references) == 1
        _, expr_type = simplify_type_system(identifier_definition.references[0].value)
        return expr_type

    assert get_reference_type('foo.a').format() == f'{scope}.T***'
    assert get_reference_type('foo.b').format() == f'{scope}.T**'
    assert get_reference_type('foo.c').format() == 'felt*'
    assert get_reference_type('foo.d').format() == f'{scope}.T*'
    assert get_reference_type('foo.e').format() == 'felt*'


def test_rebind_reference():
    program = preprocess_str(code="""
struct T:
    member pad0 : felt
    member pad1 : felt
    member t : felt
end

let x : T* = cast(ap + 1, T*)
let y = &x.t
[cast(x, felt)] = x.t
let x : T* = cast(fp - 3, T*)
[cast(x, felt)] = x.t
[y] = [y]
""", prime=PRIME)
    assert program.format() == """\
[ap + 1] = [ap + 3]
[fp + (-3)] = [fp + (-1)]
[ap + 3] = [ap + 3]
"""


def test_rebind_reference_failures():
    verify_exception("""
let x = cast(ap, felt*)
let x = cast(ap, felt**)
""", """
file:?:?: Reference rebinding must preserve the reference type. Previous type: 'felt*', \
new type: 'felt**'.
let x = cast(ap, felt**)
    ^
""")


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
Reference was defined here:
file:?:?
let x = ap + 1
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
Reference was defined here:
file:?:?
let x = ap + 1
    ^
""")


@pytest.mark.parametrize('revoking_instruction, has_def_location', [
    ('ap += [fp]', True),
    ('call label', True),
    ('call rel 0', True),
    ('ret', False),
    ('jmp label', False),
    ('jmp rel 0', False),
    ('jmp abs 0', False),
])
def test_references_revoked(revoking_instruction, has_def_location):
    def_loction_str = """\
Reference was defined here:
file:?:?
let x = ap
    ^
""" if has_def_location else ''

    verify_exception(f"""
label:
let x = ap
{revoking_instruction}
[x] = 0
""", f"""
file:?:?: Reference 'x' was revoked.
[x] = 0
 ^
{def_loction_str}
""")


def test_references_revoked_multiple_location():
    verify_exception(f"""
if [ap] == 0:
    let x = ap
else:
    let y = ap
    let x = y
end
ap += [fp]
[x] = 0
""", """

file:?:?: Reference 'x' was revoked.
[x] = 0
 ^
Reference was defined here:
file:?:?
    let x = y
        ^
file:?:?
    let x = ap
        ^
""")


def test_references_failures():
    verify_exception("""
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


def test_implicit_arg_revocation():
    verify_exception("""
func foo{x}(y):
    foo(y=1)
    ap += [fp]
    return foo(y=2)
end
""", """
file:?:?: While trying to retrieve the implicit argument 'x' in:
    return foo(y=2)
           ^******^
file:?:?: Reference 'x' was revoked.
func foo{x}(y):
         ^
Reference was defined here:
file:?:?
    foo(y=1)
    ^******^
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
    scope = TEST_SCOPE
    program = preprocess_str(code="""
func main():
    struct T:
        member pad0 : felt
        member pad1 : felt
        member pad2 : felt
        member b : T*
    end

    struct Struct:
        member pad0 : felt
        member pad1 : felt
        member a : T*
    end

    let x : Struct* = cast(ap + 10, Struct*)
    let y : Struct = [x]

    [fp] = x.a
    assert [fp] = cast(x.a.b, felt)
    assert [fp] = cast(x.a.b.b, felt)

    [fp] = y.a + 1
    ret
end
""", prime=PRIME, main_scope=scope)

    def get_reference(name):
        scoped_name = scope + name
        assert isinstance(program.identifiers.get_by_full_name(scoped_name), ReferenceDefinition)

        return program.instructions[-1].flow_tracking_data.resolve_reference(
            reference_manager=program.reference_manager, name=scoped_name)

    expected_type_x = mark_type_resolved(parse_type(f'{scope}.main.Struct*'))
    assert simplify_type_system(get_reference('main.x').value)[1] == expected_type_x

    expected_type_y = mark_type_resolved(parse_type(f'{scope}.main.Struct'))
    reference = get_reference('main.y')
    assert simplify_type_system(reference.value)[1] == expected_type_y

    assert reference.value.format() == f'[cast(ap + 10, {scope}.main.Struct*)]'
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
let x = fp
x.a = x.a
""", """
file:?:?: Cannot apply dot-operator to non-struct type 'felt'.
x.a = x.a
^*^
""", exc_type=CairoTypeError)
    verify_exception(f"""
struct T:
    member z : felt
end

let x : T = ap
x.z = x.z
""", """
file:?:?: Cannot assign an expression of type 'felt' to a reference of type 'test_scope.T'.
let x : T = ap
        ^
""")
    verify_exception(f"""
struct T:
    member z : felt
end

let x : T* = [cast(ap, T*)]
""", """
file:?:?: Cannot assign an expression of type 'test_scope.T' to a reference of type 'test_scope.T*'.
let x : T* = [cast(ap, T*)]
        ^^
""")


def test_return_value_reference():
    scope = TEST_SCOPE
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
""", prime=PRIME, main_scope=scope)

    def get_reference(name):
        scoped_name = scope + name
        assert isinstance(program.identifiers.get_by_full_name(scoped_name), ReferenceDefinition)

        return program.instructions[-1].flow_tracking_data.resolve_reference(
            reference_manager=program.reference_manager, name=scoped_name)

    expected_type = mark_type_resolved(parse_type(
        f'{scope}.foo.{CodeElementFunction.RETURN_SCOPE}'))
    assert simplify_type_system(get_reference('main.x').value)[1] == expected_type

    expected_type = mark_type_resolved(parse_type(
        f'{scope}.main.{CodeElementFunction.RETURN_SCOPE}'))
    assert simplify_type_system(get_reference('main.y').value)[1] == expected_type

    expected_type = parse_type('felt')
    assert simplify_type_system(get_reference('main.z').value)[1] == expected_type

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
file:?:?: Member 'a' does not appear in definition of struct 'test_scope.foo.Return'.
[x.a] = 0
 ^*^
""", exc_type=CairoTypeError)
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
  member s : felt
end
let x : T* = cast(ap, T*)
[ap] = x.a
""", """
file:?:?: Member 'a' does not appear in definition of struct 'test_scope.T'.
[ap] = x.a
       ^*^
""", exc_type=CairoTypeError)


def test_unpacking():
    code = """\
struct T:
    member a : felt
    member b : felt
end
func f() -> (a, b, c, d , e : T):
    return (1,2,3,4,[cast(5,T*)])
end
func g():
    alloc_locals
    let (a, local b, local c, d : T*, e) = f()
    a = d.b
    a = b + c; ap++
    a = b + c
    # The type of e is deduced from the return type of f().
    a = e.b
    let (_, _, local c, _, _) = f()
    ret
end
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
[ap] = 5; ap++
[ap] = 6; ap++
[ap] = 1; ap++
[ap] = 2; ap++
[ap] = 3; ap++
[ap] = 4; ap++
[ap] = [[ap + (-6)]]; ap++
[ap] = [[ap + (-6)]]; ap++
ret
ap += 3
call rel -17
[fp] = [ap + (-5)]
[fp + 1] = [ap + (-4)]
[ap + (-6)] = [[ap + (-3)] + 1]
[ap + (-6)] = [fp] + [fp + 1]; ap++
[ap + (-7)] = [fp] + [fp + 1]
[ap + (-7)] = [ap + (-2)]
call rel -25
[fp + 2] = [ap + (-4)]
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
    member a : felt
    member b : felt
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
    member a : felt
    member b : felt
end
func foo() -> (a, b):
    ret
end
let (a, b : T) = foo()
""", """
file:?:?: Expected expression of type 'felt', got 'test_scope.T'.
let (a, b : T) = foo()
        ^***^
""")

    verify_exception(f"""
struct T:
    member a : felt
    member b : felt
end
struct S:
    member a : felt
    member b : felt
end
func foo() -> (a, b : T):
    ret
end
func test():
    alloc_locals
    let (a, local b : S) = foo()
    ret
end
""", """
file:?:?: Expected expression of type 'test_scope.T', got 'test_scope.S'.
    let (a, local b : S) = foo()
            ^*********^

""")

    verify_exception(f"""
struct T:
end

func foo() -> (a : T*):
    ret
end

func test():
    alloc_locals
    let (local _ : T*) = foo()
    ret
end
""", """
file:?:?: Reference name cannot be '_'.
    let (local _ : T*) = foo()
         ^**********^
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


def test_member_def_failures():
    verify_exception("""
struct T:
    member t
end
""", """
file:?:?: Struct members must be explicitly typed (e.g., member x : felt).
    member t
           ^
""")

    verify_exception("""
member t : felt
""", """
file:?:?: The member keyword may only be used inside a struct.
member t : felt
       ^******^
""")

    verify_exception("""
struct T:
    member local t
end
""", """
file:?:?: Unexpected modifier 'local'.
    member local t
           ^***^
""")


def test_bad_struct():
    verify_exception("""
struct T:
    return()
end
""", """
file:?:?: Unexpected statement inside a struct definition.
    return()
    ^******^
""")


def test_bad_type_annotation():
    verify_exception("""
func foo():
    local a : foo
    ret
end
""", """
file:?:?: Expected 'test_scope.foo' to be a struct. Found: 'function'.
    local a : foo
              ^*^
""")

    verify_exception("""
func foo():
    struct test:
        member a : foo*
    end

    ret
end
""", """
file:?:?: Expected 'foo' to be a struct. Found: 'function'.
        member a : foo*
                   ^*^
""")

    verify_exception("""
func foo():
    struct test:
        member a : foo.abc*
    end

    ret
end
""", """
file:?:?: Unknown identifier 'test_scope.foo.abc'.
        member a : foo.abc*
                   ^*****^
""")


def test_cast_failure():
    verify_exception("""
struct A:
end

func foo(a : A*):
    let a = cast(5, A)
    return ()
end
""", """
file:?:?: Cannot cast 'felt' to 'test_scope.A'.
    let a = cast(5, A)
            ^********^
""", exc_type=CairoTypeError)


def test_nested_function_failure():
    verify_exception("""
func foo():
    func bar():
        return()
    end
    return ()
end
""", """
file:?:?: Nested functions are not supported.
    func bar():
         ^*^
Outer function was defined here: file:?:?
func foo():
     ^*^
""")


def test_namespace_inside_function_failure():
    verify_exception("""
func foo():
    namespace MyNamespace:
    end
    return ()
end


""", """
file:?:?: Cannot define a namespace inside a function.
    namespace MyNamespace:
              ^*********^
Outer function was defined here: file:?:?
func foo():
     ^*^
""")


def test_struct_assignments():
    struct_def = """\
struct B:
    member a : felt
    member b : felt
end

struct T:
    member a : B
    member b : felt
end
"""

    code = f"""\
{struct_def}
func f(t : T*):
    alloc_locals
    local a : T = [t]
    return ()
end
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
ap += 3
[fp] = [[fp + (-3)]]
[fp + 1] = [[fp + (-3)] + 1]
[fp + 2] = [[fp + (-3)] + 2]
ret
"""

    code = f"""\
{struct_def}
func copy(src : T**, dest: T**):
    assert [[dest]] = [[src]]
    return ()
end
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
[ap] = [[fp + (-3)]]; ap++
[ap] = [[fp + (-4)]]; ap++
[ap] = [[ap + (-1)]]; ap++
[[ap + (-3)]] = [ap + (-1)]
[ap] = [[fp + (-3)]]; ap++
[ap] = [[fp + (-4)]]; ap++
[ap] = [[ap + (-1)] + 1]; ap++
[[ap + (-3)] + 1] = [ap + (-1)]
[ap] = [[fp + (-3)]]; ap++
[ap] = [[fp + (-4)]]; ap++
[ap] = [[ap + (-1)] + 2]; ap++
[[ap + (-3)] + 2] = [ap + (-1)]
ret
"""


def test_subscript_operator():
    code = """\
struct T:
    member x: felt
    member y: felt
end

struct S:
    member a : T
    member b : T
    member c : T
end

func f(s_arr : S*, table : felt**, perm : felt*):
    assert s_arr[0].b.x = s_arr[1].a.y
    assert (&s_arr[0].a)[2].x = (&s_arr[1].b.y)[-2]

    assert table[1][2] = 11

    assert perm[0] = 1
    assert perm[1] = 0
    assert perm[perm[0]] = 0

    tempvar i = 2
    tempvar j = 5
    tempvar k = -13
    assert (&(&s_arr[i].b)[j].x)[k] = s_arr[1].c.y
    assert table[i][j] = 17

    return()
end
"""
    program = preprocess_str(code=code, prime=PRIME)
    expected_result = """\
[ap] = [[fp + (-5)] + 7]; ap++                  # push s_arr[1].a.y
[[fp + (-5)] + 2] = [ap + (-1)]                 # assert s_arr[0].b.x = s_arr[1].a.y

[ap] = [[fp + (-5)] + 7]; ap++                  # push (&s_arr[1].b.y)[-2]
[[fp + (-5)] + 4] = [ap + (-1)]                 # assert (&s_arr[0].a)[2].x = (&s_arr[1].b.y)[-2]


[ap] = [[fp + (-4)] + 1]; ap++                  # push table[1]
[ap] = 11; ap++                                 # push 11
[[ap + (-2)] + 2] = [ap + (-1)]                 # assert table[1][2] = 11


[ap] = 1; ap++                                  # push 1
[[fp + (-3)]] = [ap + (-1)]                     # assert perm[0] = 1

[ap] = 0; ap++                                  # push 0
[[fp + (-3)] + 1] = [ap + (-1)]                 # assert perm[1] = 0

[ap] = [[fp + (-3)]]; ap++                      # push perm[0]
[ap] = [fp + (-3)] + [ap + (-1)]; ap++          # push perm + perm[0]
[ap] = 0; ap++                                  # push 0
[[ap + (-2)]] = [ap + (-1)]                     # assert perm[perm[0]] = 0


[ap] = 2; ap++                                  # tempvar i = 2
[ap] = 5; ap++                                  # tempvar j = 5
[ap] = -13; ap++                                # tempvar k = -13

[ap] = [ap + (-3)] * 6; ap++                    # push i * 6
[ap] = [ap + (-1)] + 2; ap++                    # push i * 6 + 2
[ap] = [fp + (-5)] + [ap + (-1)]; ap++          # push &s_arr[i].b ( = s_arr + i * 6 + 2)
[ap] = [ap + (-5)] * 2; ap++                    # push j * 2
[ap] = [ap + (-2)] + [ap + (-1)]; ap++          # push &(&s_arr[i].b)[j].x
[ap] = [ap + (-1)] + [ap + (-6)]; ap++          # push &(&s_arr[i].b)[j].x + k
[ap] = [[fp + (-5)] + 11]; ap++                 # push s_arr[1].b.y
[[ap + (-2)]] = [ap + (-1)]                     # assert (&(&s_arr[i].a)[j].x)[k] = s_arr[1].b.y

[ap] = [fp + (-4)] + [ap + (-10)]; ap++         # push table + i
[ap] = [[ap + (-1)]]; ap++                      # push table[i]
[ap] = [ap + (-1)] + [ap + (-11)]; ap++         # push table[i] + j
[ap] = 17; ap++                                 # push 17
[[ap + (-2)]] = [ap + (-1)]                     # assert table[i][j] = 17
ret
"""
    assert program.format() == strip_comments_and_linebreaks(expected_result)


def test_dot_operator():
    code = """\
struct R:
    member x: felt
    member r : R*
end

struct S:
    member x : felt
    member y : felt
end

struct T:
    member x : felt
    member s : S
    member sp : S*
end

func f():
    alloc_locals
    let __fp__ = [fp - 100]

    local s : S
    local s2 : S
    local t : T
    local r1 : R

    s.x = 14
    (s).y = 2
    (&t).x = 7
    assert t.s = s

    ((t).s).x = t.x * 2
    assert t.s = (t).s
    assert (t.s).x = t.s.x
    assert (&(t.s)).y = ((t).s).y

    assert t.sp = &s
    assert t.sp.x = 14
    assert [t.sp].y = 2
    assert [t.sp] = s
    assert [t.sp] = (&t).s
    assert &((t).s) = t.sp + 5

    assert t.sp + 2 = &s2
    assert [t.sp + 2].x = s.x
    assert (t.sp + 2).y = s.y

    assert [r1.r.r].r.r.r.r = &r1

    return()
end
"""
    program = preprocess_str(code=code, prime=PRIME)
    expected_result = """\
ap += 10                             # alloc_locals
[fp] = 14                            # s.x = 14
[fp + 1] = 2                         # (s).y = 2
[fp + 4] = 7                         # (&t).x = 7
[fp + 5] = [fp]                      # assert t.s = s (x member)
[fp + 6] = [fp + 1]                  # assert t.s = s (y member)

[fp + 5] = [fp + 4] * 2              # ((t).s).x = t.x * 2
[fp + 5] = [fp + 5]                  # assert t.s = (t).s  (x member)
[fp + 6] = [fp + 6]                  # assert t.s = (t).s  (y member)
[fp + 5] = [fp + 5]                  # assert (t.s).x = t.s.x
[fp + 6] = [fp + 6]                  # assert (&(t.s)).y = ((t).s).y

[fp + 7] = [fp + (-100)]             # assert t.sp = &s
[ap] = 14; ap++                      #   push 14
[[fp + 7]] = [ap + (-1)]             # assert t.sp.x = 14
[ap] = 2; ap++                       #   push 2
[[fp + 7] + 1] = [ap + (-1)]         # assert [t.sp].y = 2
[[fp + 7]] = [fp]                    # assert [t.sp] = s (x member)
[[fp + 7] + 1] = [fp + 1]            # assert [t.sp] = s (y member)
[[fp + 7]] = [fp + 5]                # assert [t.sp] = (&t).s (x member)
[[fp + 7] + 1] = [fp + 6]            # assert [t.sp] = (&t).s (y member)
[ap] = [fp + 7] + 5; ap++            #    push t.sp + 5
[fp + (-100)] + 5 = [ap + (-1)]      # assert &(t.s) = t.sp + 5

[ap] = [fp + (-100)] + 2; ap++       #   push &s2
[fp + 7] + 2 = [ap + (-1)]           # assert t.sp + 2 = &s2
[[fp + 7] + 2] = [fp]                # assert [t.sp + 2].x = s.x
[[fp + 7] + 3] = [fp + 1]            # assert (t.sp + 2).y = s.y

                                     # assert [r1.r.r].r.r.r.r = &r1 :
[ap] = [[fp + 9] + 1]; ap++          #   push (r1.r).r ([fp + 9] = r1.r)
[ap] = [[ap + (-1)] + 1]; ap++       #   push (r1.r.r).r
[ap] = [[ap + (-1)] + 1]; ap++       #   push (r1.r.r.r).r
[ap] = [[ap + (-1)] + 1]; ap++       #   push (r1.r.r.r.r).r
[ap] = [fp + (-100)] + 8; ap++       #   push &r1
[[ap + (-2)] + 1] = [ap + (-1)]      #   assert (r1.r.r.r.r.r).r = &r1
ret
"""
    assert program.format() == strip_comments_and_linebreaks(expected_result)


def test_tuple_assertions():
    code = f"""\
func f():
    alloc_locals
    local var : (felt, felt) = [cast(ap, (felt, felt)*)]
    return ()
end
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
ap += 2
[fp] = [ap]
[fp + 1] = [ap + 1]
ret
"""


def test_tuple_expression():
    code = """\
struct A:
    member x : felt
    member y : felt*
end
struct B:
    member x : felt
    member y : A
    member z : A*
end
func foo(a : A*):
    alloc_locals
    let a : A* = cast([fp], A*)
    local b : B = cast((1, [a], a), B)

    assert (b.x, b.z, a) = (5, a, a)
    return ()
end
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == """\
ap += 4
[fp] = 1
[fp + 1] = [[fp]]
[fp + 2] = [[fp] + 1]
[fp + 3] = [fp]
[fp] = 5
[fp + 3] = [fp]
[fp] = [fp]
ret
"""


def test_tuple_expression_failures():
    verify_exception("""
struct A:
    member x : felt
end
struct B:
end
let a = cast(fp, A*)
let b = cast((1, a), B)
""", """
file:?:?: Cannot cast an expression of type '(felt, test_scope.A*)' to 'test_scope.B'.
The former has 2 members while the latter has 0 members.
let b = cast((1, a), B)
             ^****^
""", exc_type=CairoTypeError)

    verify_exception("""
struct A:
    member x : felt
    member y : felt
end
struct B:
    member a : felt
    member b : felt
end
let a = [cast(fp, A*)]
let b = cast((a, 1), B)
""", """
file:?:?: While expanding the reference 'a' in:
let b = cast((a, 1), B)
              ^
file:?:?: Cannot cast 'test_scope.A' to 'felt'.
let a = [cast(fp, A*)]
        ^************^
""", exc_type=CairoTypeError)

    verify_exception("""
struct A:
    member x : felt
    member y : felt
end
struct B:
    member a : felt
    member b : A
end
let b = cast([cast(ap, (felt, felt*)*)], B)
""", """
file:?:?: Cannot cast 'felt*' to 'test_scope.A'.
let b = cast([cast(ap, (felt, felt*)*)], B)
             ^************************^
""", exc_type=CairoTypeError)

    verify_exception("""
struct B:
end
let b = cast([cast(ap, (felt, felt*)*)], B)
""", """
file:?:?: Cannot cast an expression of type '(felt, felt*)' to 'test_scope.B'.
The former has 2 members while the latter has 0 members.
let b = cast([cast(ap, (felt, felt*)*)], B)
             ^************************^
""", exc_type=CairoTypeError)
    verify_exception("""
(1, 1) = 1
""", """
file:?:?: Expected a 'felt' or a pointer type. Got: '(felt, felt)'.
(1, 1) = 1
^****^
""")

    verify_exception("""
assert (1, 1) = 1
""", """
file:?:?: Cannot compare '(felt, felt)' and 'felt'.
assert (1, 1) = 1
^***************^
""")


def test_struct_constructor():
    code = """\
struct M:
end
struct A:
    member x : M*
    member y : felt
end
struct B:
    member x : felt
    member y : A
    member z : A
    member w : A*
end
func foo(m_ptr: M*, a_ptr : A*):
    alloc_locals
    local b1 : B = B(x=0, y=A(m_ptr, 2), z=[a_ptr], w=a_ptr)
    let a = A(x=a_ptr.x, y=0)
    assert a = A(x=m_ptr, y=2)

    let b2 : B = B(x=0, y=A(m_ptr, 2), z=[a_ptr], w=a_ptr)
    assert b2 = b2

    tempvar y: felt* = cast(1, felt*)
    tempvar x: A* = cast(0, A*)
    assert [x] = A(x=m_ptr, y=[y])
    return ()
end
"""
    program = preprocess_str(code=code, prime=PRIME)
    expected_result = """\
ap += 6
# Populate b1.
[fp] = 0
[fp + 1] = [fp + (-4)]
[fp + 2] = 2
[fp + 3] = [[fp + (-3)]]
[fp + 4] = [[fp + (-3)] + 1]
[fp + 5] = [fp + (-3)]

# assert a = A(x=m_ptr, y=2) (x component).
[[fp + (-3)]] = [fp + (-4)]

# assert a = A(x=m_ptr, y=2) (y component).
[ap] = 2; ap++
0 = [ap + (-1)]

# assert b2 = b2.
[ap] = 0; ap++
0 = [ap + (-1)]
[fp + (-4)] = [fp + (-4)]
[ap] = 2; ap++
2 = [ap + (-1)]
[ap] = [[fp + (-3)]]; ap++
[[fp + (-3)]] = [ap + (-1)]
[ap] = [[fp + (-3)] + 1]; ap++
[[fp + (-3)] + 1] = [ap + (-1)]
[fp + (-3)] = [fp + (-3)]

# tempvar y: felt* = cast(1, felt*).
[ap] = 1; ap++
# tempvar x: A* = cast(0, A*).
[ap] = 0; ap++
# assert [x] = A(x=m_ptr, y=[y]).
[[ap + (-1)]] = [fp + (-4)]
[ap] = [[ap + (-2)]]; ap++
[[ap + (-2)] + 1] = [ap + (-1)]
ret
"""
    assert program.format() == strip_comments_and_linebreaks(expected_result)


def test_struct_constructor_failures():
    verify_exception("""
func foo():
    ret
end

foo(3) = foo(4)
""", """
file:?:?: Expected 'foo' to be a struct. Found: 'function'.
foo(3) = foo(4)
^****^
""")
    verify_exception("""
struct A:
    member next: A*
end

assert A(next=0) = A(next=0)
""", """
file:?:?: Cannot cast 'felt' to 'test_scope.A*'.
assert A(next=0) = A(next=0)
              ^
""", exc_type=CairoTypeError)

    def verify_exception_for_expr(expr_str: str, expected_error: str):
        verify_exception(f"""
struct T:
    member x : felt
    member y : felt
end

func foo(a):
    alloc_locals
    local a : T = {expr_str}
end
""", expected_error, exc_type=CairoTypeError)

    verify_exception_for_expr('T(5, 6, 7)', """
file:?:?: Cannot cast an expression of type '(felt, felt, felt)' to 'test_scope.T'.
The former has 3 members while the latter has 2 members.
    local a : T = T(5, 6, 7)
                  ^********^
""")

    verify_exception_for_expr('&T(5, 6)', """
file:?:?: Expression has no address.
    local a : T = &T(5, 6)
                   ^*****^
""")

    verify_exception_for_expr('T(5, 6).x', """
file:?:?: Accessing struct members for r-value structs is not supported yet.
    local a : T = T(5, 6).x
                  ^*******^
""")

    verify_exception_for_expr('T{a}(5, 6)', """
file:?:?: Implicit arguments cannot be used with struct constructors.
    local a : T = T{a}(5, 6)
                    ^
""")


def test_unsupported_decorator():
    verify_exception("""
@external
func foo():
    return()
end
""", """
file:?:?: Unsupported decorator: 'external'.
@external
^*******^
""")


def test_skipped_functions():
    files = {'module': """
func func0():
    tempvar x = 0
    return ()
end
func func1():
    tempvar x = 1
    return ()
end
func func2():
    tempvar x = 2
    return func1()
end
""", '.': """
from module import func2
func2()
"""}
    program = preprocess_codes(
        codes=[(files['.'], '.')],
        pass_manager=default_pass_manager(prime=PRIME, read_module=read_file_from_dict(files)))
    assert program.format() == """\
[ap] = 1; ap++
ret
[ap] = 2; ap++
call rel -5
ret
call rel -5
"""
    program = preprocess_codes(
        codes=[(files['.'], '.')],
        pass_manager=default_pass_manager(
            prime=PRIME,
            read_module=read_file_from_dict(files),
            opt_unused_functions=False))
    assert program.format() == """\
[ap] = 0; ap++
ret
[ap] = 1; ap++
ret
[ap] = 2; ap++
call rel -5
ret
call rel -5
"""


def test_known_ap_change_decorator():
    # Positive case.
    code = """\
func bar():
    return ()
end

@known_ap_change
func foo(arg : felt):
    alloc_locals
    local local_var
    tempvar tmp = 0
    bar()
    return ()
end

"""
    preprocess_str(code=code, prime=PRIME)

    # Negative case.
    verify_exception("""
@known_ap_change
func foo():
    foo()
    return ()
end
""", """
file:?:?: The compiler was unable to deduce the change of the ap register, as required by this \
decorator.
@known_ap_change
^**************^
""")
