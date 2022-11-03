import pytest

from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo
from starkware.cairo.lang.compiler.error_handling import LocationError
from starkware.cairo.lang.compiler.identifier_definition import (
    ConstDefinition,
    FunctionDefinition,
    LabelDefinition,
    ReferenceDefinition,
    TypeDefinition,
)
from starkware.cairo.lang.compiler.identifier_manager import IdentifierError
from starkware.cairo.lang.compiler.instruction_builder import InstructionBuilderError
from starkware.cairo.lang.compiler.parser import parse_type
from starkware.cairo.lang.compiler.preprocessor.default_pass_manager import default_pass_manager
from starkware.cairo.lang.compiler.preprocessor.flow import FlowTrackingDataActual
from starkware.cairo.lang.compiler.preprocessor.preprocess_codes import preprocess_codes
from starkware.cairo.lang.compiler.preprocessor.preprocessor import AttributeScope
from starkware.cairo.lang.compiler.preprocessor.preprocessor_test_utils import (
    CAIRO_TEST_MODULES,
    PRIME,
    TEST_SCOPE,
    preprocess_str,
    strip_comments_and_linebreaks,
    verify_exception,
)
from starkware.cairo.lang.compiler.preprocessor.reg_tracking import RegTrackingData
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.test_utils import read_file_from_dict
from starkware.cairo.lang.compiler.type_casts import CairoTypeError
from starkware.cairo.lang.compiler.type_system import mark_type_resolved
from starkware.cairo.lang.compiler.type_system_visitor import simplify_type_system


def test_compiler():
    program = preprocess_str(
        code="""
const x = 5;
const y = 2 * x;
[ap] = [[fp + 2 * 0x3] + ((7 - 1 + y))], ap++;
ap += 3 + 'a';
dw x + 5;

// An empty line with a comment.
[ap] = [fp];  // This is a comment.
let z = ap - 3;
[ap] = [ap - x];
jmp rel 2 - 3;
ret;

label:
jmp label if [fp + 3 + 1] != 0;
""",
        prime=PRIME,
    )
    assert (
        program.format()
        == """\
[ap] = [[fp + 6] + 16], ap++;
ap += 100;
dw 10;
[ap] = [fp];
[ap] = [ap + (-5)];
jmp rel -1;
ret;
jmp rel 0 if [fp + 4] != 0;
"""
    )


def test_scope_const():
    code = """\
const x = 5;
[ap] = x, ap++;
func f() {
    const x = 1234;
    [ap + 1] = x, ap++;
    [ap + 2] = f.x, ap++;
    ret;
}
[ap + 3] = x, ap++;
[ap + 4] = f.x, ap++;
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[ap] = 5, ap++;
[ap + 1] = 1234, ap++;
[ap + 2] = 1234, ap++;
ret;
[ap + 3] = 5, ap++;
[ap + 4] = 1234, ap++;
"""
    )


def test_pow_failure():
    verify_exception(
        """\
func foo(x: felt) {
    tempvar y = x ** 2;
}
""",
        """
file:?:?: Operator '**' is only supported for constant values.
    tempvar y = x ** 2;
                ^****^
""",
    )
    verify_exception(
        """\
const X = 2;
const Y = 2 ** (2 * 3);
const Z = 2 ** (X * 3);
""",
        """
file:?:?: Identifier 'X' is not allowed in this context.
const Z = 2 ** (X * 3);
                ^
""",
        exc_type=CairoTypeError,
    )


def test_referenced_before_definition_failure():
    verify_exception(
        """
const x = 5;
func f() {
    [ap + 1] = x, ap++;
    const x = 1234;
}
""",
        """
file:?:?: Identifier 'x' referenced before definition.
    [ap + 1] = x, ap++;
               ^
""",
    )
    verify_exception(
        """
foo.x = 6;
func foo() {
    const x = 6;
}
""",
        """
file:?:?: Identifier 'foo.x' referenced before definition.
foo.x = 6;
^***^
""",
    )


def test_assign_future_label():
    code = """\
[ap] = future_label2 - future_label1, ap++;
[ap] = future_label1, ap++;

future_label1:
[ap] = future_label2, ap++;

future_label2:
[ap] = 8, ap++;
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[ap] = 2, ap++;
[ap] = 4, ap++;
[ap] = 6, ap++;
[ap] = 8, ap++;
"""
    )


def test_assign_future_function_label():
    code = """\
start:
g(f - start);
g((f - start + 1) * 2 + 3);

func f() -> () {
    ret;
}
func g(x: felt) -> () {
    ret;
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    f_definition = program.identifiers.get_by_full_name(ScopedName.from_string("test_scope.f"))
    assert isinstance(f_definition, FunctionDefinition)
    assert (
        program.format()
        == f"""\
[ap] = {f_definition.pc}, ap++;
call rel 13;
[ap] = {f_definition.pc}, ap++;
[ap] = [ap + (-1)] + 1, ap++;
[ap] = [ap + (-1)] * 2, ap++;
[ap] = [ap + (-1)] + 3, ap++;
call rel 3;
ret;
ret;
"""
    )


def test_temporary_variable():
    code = """\
struct T {
    pad0: felt,
    t: felt,
}
tempvar x = [ap - 1] + [fp - 3];
ap += 3;
tempvar y: T* = cast(x, T*);
ap += 4;
[fp] = y.t;
ap += 5;
tempvar z: (felt, felt) = (1, 2);
// Check the expression pushing optimization.
tempvar z: (felt, felt) = ([ap - 1], 3);
tempvar q: T;
assert q.t = 0;
tempvar w;
tempvar h1 = nondet %{ 5**i %};
tempvar h2: felt* = cast(nondet %{ segments.add_temp_segment() %}, felt*) + 3;
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[ap] = [ap + (-1)] + [fp + (-3)], ap++;
ap += 3;
[ap] = [ap + (-4)], ap++;
ap += 4;
[fp] = [[ap + (-5)] + 1];
ap += 5;
[ap] = 1, ap++;
[ap] = 2, ap++;
[ap] = 3, ap++;
ap += 2;
[ap + (-1)] = 0;
ap += 1;
%{ memory[ap] = to_felt_or_relocatable(5**i) %}
ap += 1;
%{ memory[ap] = to_felt_or_relocatable(segments.add_temp_segment()) %}
ap += 1;
[ap] = [ap + (-1)] + 3, ap++;
"""
    )


def test_temporary_variable_failures():
    verify_exception(
        """
tempvar x: felt = cast([ap], felt*);
""",
        """
file:?:?: Cannot assign an expression of type 'felt*' to a temporary variable of type 'felt'.
tempvar x: felt = cast([ap], felt*);
           ^**^
""",
    )
    verify_exception(
        """
tempvar _ = 0;
""",
        """
file:?:?: Reference name cannot be '_'.
tempvar _ = 0;
        ^
""",
    )
    verify_exception(
        """
struct T {
    x: felt,
    y: felt,
}
tempvar a: T = nondet %{ 1 %};
""",
        """
file:?:?: Hint tempvars must be of type felt or a pointer.
tempvar a: T = nondet %{ 1 %};
               ^************^
""",
    )


def test_tempvar_modifier_failures():
    verify_exception(
        """
func main() {
    tempvar local x = 5;
}
""",
        """
file:?:?: Unexpected modifier 'local'.
    tempvar local x = 5;
            ^***^
""",
    )

    verify_exception(
        """
tempvar x = [ap - 1] + [fp - 3];
[x] = [[ap]];
""",
        """
file:?:?: While expanding the reference 'x' in:
[x] = [[ap]];
 ^
file:?:?: Expected a register. Found: [ap + (-1)].
tempvar x = [ap - 1] + [fp - 3];
        ^
Preprocessed instruction:
[[ap + (-1)]] = [[ap]]
""",
        exc_type=InstructionBuilderError,
    )


def test_static_assert():
    code = """\
static_assert 3 + fp + 10 == 0 + fp + 13;
let x = ap;
ap += 3;
static_assert x + 7 == ap + 4;
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
ap += 3;
"""
    )


def test_static_assert_failures():
    verify_exception(
        """
static_assert 3 + fp + 10 == 0 + fp + 14;
""",
        """
file:?:?: Static assert failed: fp + 13 != fp + 14.
static_assert 3 + fp + 10 == 0 + fp + 14;
^***************************************^
""",
    )
    verify_exception(
        """
let x = ap;
ap += 3;
static_assert x + 7 == 0;
""",
        """
file:?:?: Static assert failed: ap + 4 != 0.
static_assert x + 7 == 0;
^***********************^
""",
    )


@pytest.mark.parametrize(
    "last_statement",
    [
        "jmp body if [ap] != 0",
        "ap += 0",
        "[ap] = [ap]",
        "[ap] = [ap], ap++",
    ],
)
def test_func_failures(last_statement):
    verify_exception(
        f"""
func f(x) {{
    body:
    ret;
    {last_statement};
}}
""",
        """
file:?:?: Function must end with a return instruction or a jump.
func f(x) {
     ^
""",
    )


def test_func_modifier_failures():
    verify_exception(
        """
func f(local x) {
    ret;
}
""",
        """
file:?:?: Unexpected modifier 'local'.
func f(local x) {
       ^***^
""",
    )


def test_return():
    code = """\
func f() -> (a: felt, b: felt, c: felt) {
    return (a=1, b=[fp], c=[fp + 1] + 2);

    tempvar z = 5;
    tempvar x = 1;
    tempvar y = 2;
    return (x, y, z);

    tempvar x = 1;
    tempvar y = 2;
    return (x, y, x + x + y);

    tempvar tup = (1, 2, 3);
    return tup;
}
func g() {
    return ();
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[ap] = 1, ap++;
[ap] = [fp], ap++;
[ap] = [fp + 1] + 2, ap++;
ret;
[ap] = 5, ap++;
[ap] = 1, ap++;
[ap] = 2, ap++;
[ap] = [ap + (-3)], ap++;
ret;
[ap] = 1, ap++;
[ap] = 2, ap++;
[ap] = [ap + (-2)] + [ap + (-2)], ap++;
[ap] = [ap + (-3)], ap++;
[ap] = [ap + (-3)], ap++;
[ap] = [ap + (-3)] + [ap + (-4)], ap++;
ret;
[ap] = 1, ap++;
[ap] = 2, ap++;
[ap] = 3, ap++;
ret;
ret;
"""
    )


def test_return_failures():
    # Named after positional.
    verify_exception(
        """
func f() -> (a: felt, b: felt, c: felt) {
    return (a=1, b=1, [fp] + 1);
}
""",
        """
file:?:?: All fields in a named tuple must have a name.
    return (a=1, b=1, [fp] + 1);
           ^******************^
""",
    )
    # Wrong num.
    verify_exception(
        """
func f() -> (a: felt, b: felt, c: felt, d: felt) {
    return (1, [fp] + 1);
}
""",
        """
file:?:?: Cannot cast an expression of type '(felt, felt)' to \
'(a: felt, b: felt, c: felt, d: felt)'.
The former has 2 members while the latter has 4 members.
    return (1, [fp] + 1);
           ^***********^
""",
        exc_type=CairoTypeError,
    )
    # Wrong num.
    verify_exception(
        """
func f() -> (a: felt, b: felt) {
    return ();
}
""",
        """
file:?:?: Cannot cast an expression of type '()' to '(a: felt, b: felt)'.
The former has 0 members while the latter has 2 members.
    return ();
           ^^
""",
        exc_type=CairoTypeError,
    )
    # Unknown name.
    verify_exception(
        """
func f() -> (a: felt, b: felt, c: felt) {
    return (a=1, d=1, c=[fp] + 1);
}
""",
        """
file:?:?: Cannot cast '(a: felt, d: felt, c: felt)' to '(a: felt, b: felt, c: felt)'.
Expected argument name 'b'. Found: 'd'.
    return (a=1, d=1, c=[fp] + 1);
           ^********************^
""",
        exc_type=CairoTypeError,
    )
    # Not in func.
    verify_exception(
        """
return (a=1, [fp] + 1);
""",
        """
file:?:?: return cannot be used outside of a function.
return (a=1, [fp] + 1);
^*********************^
""",
    )

    verify_exception(
        """
func f() -> (a: felt) {
    return 2 * 3;
}
""",
        """
file:?:?: Expected expression of type '(a: felt)', got 'felt'.
    return 2 * 3;
           ^***^
""",
    )

    verify_exception(
        """
struct MyStruct {
}
func f() -> (a: felt) {
    return MyStruct();
}
""",
        """
file:?:?: Expected MyStruct to be a function name. Found: struct.
    return MyStruct();
           ^******^
""",
    )


def test_tail_call():
    code = """\
func f(a) -> (a: felt) {
    return f(a);
}
func g(a, b) -> (a: felt) {
    return f(a);
}
"""
    program = preprocess_str(
        code=code, prime=PRIME, main_scope=ScopedName.from_string("test_scope")
    )
    assert (
        program.format()
        == """\
[ap] = [fp + (-3)], ap++;
call rel -1;
ret;
[ap] = [fp + (-4)], ap++;
call rel -5;
ret;
"""
    )


def test_tail_call_failure():
    verify_exception(
        """
func g() -> (a: felt) {
    return (a=0);
}
return g();
""",
        """
file:?:?: return cannot be used outside of a function.
return g();
^*********^
""",
    )

    verify_exception(
        """
func g() -> (a: felt) {
    return (a=0);
}
func f(x, y) -> (a: felt, b: felt, c: felt, d: felt, e: felt) {
    return g();
}
""",
        """
file:?:?: Cannot convert the return type of g to the return type of f.
    return g();
    ^*********^
""",
    )

    verify_exception(
        """
func g{x, y}() -> (a: felt) {
    return (a=0);
}
func f{y, x}() -> (a: felt) {
    return g();
}
""",
        """
file:?:?: Cannot convert the implicit arguments of g to the implicit arguments of f.
    return g();
    ^*********^
The implicit arguments of 'g' were defined here:
file:?:?
func g{x, y}() -> (a: felt) {
       ^**^
The implicit arguments of 'f' were defined here:
file:?:?
func f{y, x}() -> (a: felt) {
       ^**^
""",
    )

    verify_exception(
        """
func f(x, y) -> (a: felt, b: felt, c: felt, d: felt, e: felt) {
    return g();
}
""",
        """
file:?:?: Unknown identifier 'g'.
    return g();
           ^
""",
    )

    verify_exception(
        """
func g(x, y) -> (a: felt) {
    return (a=5);
}
func f(x, y) -> (a: felt*) {
    return g(x, y);
}
""",
        """
file:?:?: Cannot convert the return type of g to the return type of f.
    return g(x, y);
    ^*************^
""",
    )


def test_function_call():
    code = """\
func foo(a, b) -> (c: felt) {
    bar(a=a);
    return (c=1);
}
func bar(a) {
    return ();
}
foo(2, 3);
foo(2, b=3);
let res = foo(a=2, b=3);
res.c = 1;
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[ap] = [fp + (-4)], ap++;
call rel 5;
[ap] = 1, ap++;
ret;
ret;
[ap] = 2, ap++;
[ap] = 3, ap++;
call rel -11;
[ap] = 2, ap++;
[ap] = 3, ap++;
call rel -17;
[ap] = 2, ap++;
[ap] = 3, ap++;
call rel -23;
[ap + (-1)] = 1;
"""
    )


def test_func_args():
    scope = TEST_SCOPE
    code = """\
struct T {
    s: felt,
    t: felt,
}
func f(x, y: T, z: T*) {
    x = 1, ap++;
    y.s = 2, ap++;
    z.t = y.t, ap++;
    ret;
}
"""
    program = preprocess_str(code=code, prime=PRIME, main_scope=scope)
    reference_x = program.instructions[-1].flow_tracking_data.resolve_reference(
        reference_manager=program.reference_manager, name=scope + "f.x"
    )
    assert reference_x.value.format() == "[cast(fp + (-6), felt*)]"
    reference_y = program.instructions[-1].flow_tracking_data.resolve_reference(
        reference_manager=program.reference_manager, name=scope + "f.y"
    )
    assert reference_y.value.format() == f"[cast(fp + (-5), {scope}.T*)]"
    reference_z = program.instructions[-1].flow_tracking_data.resolve_reference(
        reference_manager=program.reference_manager, name=scope + "f.z"
    )
    assert reference_z.value.format() == f"[cast(fp + (-3), {scope}.T**)]"
    assert (
        program.format()
        == """\
[fp + (-6)] = 1, ap++;
[fp + (-5)] = 2, ap++;
[[fp + (-3)] + 1] = [fp + (-4)], ap++;
ret;
"""
    )


def test_func_args_failures():
    verify_exception(
        """
func f(x) {
    [ap] = [x] + 1;
}
""",
        """
file:?:?: While expanding the reference 'x' in:
    [ap] = [x] + 1;
            ^
file:?:?: Expected a register. Found: [fp + (-3)].
func f(x) {
       ^
Preprocessed instruction:
[ap] = [[fp + (-3)]] + 1
""",
        exc_type=InstructionBuilderError,
    )


def test_with_statement():
    code = """
let x = 1000;
[ap] = 0;
with x {
    [ap] = 1;
    [ap] = 2;
    [ap] = x;
    let x = 1001;
}
[ap] = x;
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[ap] = 0;
[ap] = 1;
[ap] = 2;
[ap] = 1000;
[ap] = 1001;
"""
    )


def test_with_statement_locals():
    code = """
func foo() -> (z: felt) {
    ret;
}

func bar() {
    alloc_locals;
    local x = 0;
    with x {
        let (local z) = foo();
    }
    ret;
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
ret;
ap += 2;
[fp] = 0;
call rel -5;
[fp + 1] = [ap + (-1)];
ret;
"""
    )


def test_with_statement_failure():
    verify_exception(
        """
with x {
    [ap] = [ap];
}
""",
        """
file:?:?: Unknown reference 'x'.
with x {
     ^
""",
    )
    verify_exception(
        """
const x = 0;
with x {
    [ap] = [ap];
}
""",
        """
file:?:?: Expected 'x' to be a reference, found: const.
with x {
     ^
""",
    )
    verify_exception(
        """
let x = 0;
with x as y {
    [ap] = [ap];
}
""",
        """
file:?:?: The 'as' keyword is not supported in 'with' statements.
with x as y {
          ^
""",
    )


def test_with_attr_statement():
    code = """
func a() {
    alloc_locals;
    local x = 0;
    ap += 7;
    with_attr attr_name("attribute value") {
        [ap] = 1;
    }
    [ap] = 2;
    ret;
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
ap += 1;
[fp] = 0;
ap += 7;
[ap] = 1;
[ap] = 2;
ret;
"""
    )
    expected_flow_tracking_data = FlowTrackingDataActual(
        ap_tracking=RegTrackingData(group=0, offset=8),
        reference_ids={ScopedName.from_string("test_scope.a.x"): 0},
    )
    expected_accessible_scopes = [
        ScopedName.from_string("test_scope"),
        ScopedName.from_string("test_scope.a"),
    ]
    expected_attributes = [
        AttributeScope(
            name="attr_name",
            value="attribute value",
            start_pc=6,
            end_pc=8,
            flow_tracking_data=expected_flow_tracking_data,
            accessible_scopes=expected_accessible_scopes,
        )
    ]
    assert program.attributes == expected_attributes


def test_attribute_scope_deserialization_with_missing_fields():
    """
    Check that AttributeScope can be deserialized even if accessible_scopes or flow_tracking_data
    are missing from the serialization.
    """
    code = """
with_attr attr_name("attribute value") {
    [ap] = 1;
}
"""
    program = compile_cairo(code, prime=DEFAULT_PRIME)
    assert len(program.attributes) == 1

    serialized_program = program.dump()
    serialized_attribute = serialized_program["attributes"][0]
    del serialized_attribute["accessible_scopes"]
    del serialized_attribute["flow_tracking_data"]

    deserialized_attribute = program.load(data=serialized_program).attributes[0]
    assert deserialized_attribute.accessible_scopes == []
    assert deserialized_attribute.flow_tracking_data is None


def test_implicit_args():
    code = """\
struct T {
    a: felt,
    b: felt,
}

func f{x: T}() -> () {
    // Rebind x.
    let x = [cast(fp - 1234, T*)];
    return ();
}

func g{x: T, y}(z, w) -> (res: felt) {
    x.a = 0;
    x.b = 1;
    y = 2;
    z = 3;
    w = 4;
    // Rebind y. This affects the implicit return values.
    let y = z;
    // We don't need a 'with' statement, since x and y are implicit arguments.
    f();
    return (res=z + w);
}

func h() {
    let y = 10;
    let x: T = [cast(fp - 100, T*)];
    with x, y {
        let (res2) = g(0, 0);
    }
    // Below, x and y refer to the implicit return values.
    tempvar a = x.a + y;
    tempvar b = res2;
    ret;
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[ap] = [fp + (-1234)], ap++;
[ap] = [fp + (-1233)], ap++;
ret;
[fp + (-7)] = 0;
[fp + (-6)] = 1;
[fp + (-5)] = 2;
[fp + (-4)] = 3;
[fp + (-3)] = 4;
[ap] = [fp + (-7)], ap++;
[ap] = [fp + (-6)], ap++;
call rel -15;
[ap] = [fp + (-4)], ap++;
[ap] = [fp + (-4)] + [fp + (-3)], ap++;
ret;
[ap] = [fp + (-100)], ap++;
[ap] = [fp + (-99)], ap++;
[ap] = 10, ap++;
[ap] = 0, ap++;
[ap] = 0, ap++;
call rel -25;
[ap] = [ap + (-4)] + [ap + (-2)], ap++;
[ap] = [ap + (-2)], ap++;
ret;
"""
    )


def test_implicit_args_failures():
    verify_exception(
        """
func f{x}(x: felt) {
    ret;
}
""",
        """
file:?:?: An argument cannot have the same name as an implicit argument.
func f{x}(x: felt) {
          ^
""",
    )
    verify_exception(
        """
func f{x}() {
    ret;
}

func g() {
    f();
    ret;
}
""",
        """
file:?:?: While trying to retrieve the implicit argument 'x' in:
    f();
    ^*^
file:?:?: Unknown identifier 'x'.
func f{x}() {
       ^
""",
    )
    verify_exception(
        """
func f{x}(y) {
    ret;
}
func g(x) {
    with x {
        f(0);
    }
    // This should fail, as it is outside the "with x".
    f(1);
    ret;
}
""",
        """
file:?:?: While trying to update the implicit return value 'x' in:
    f(1);
    ^**^
file:?:?: 'x' cannot be used as an implicit return value. Consider using a 'with' statement.
func f{x}(y) {
       ^
""",
    )
    verify_exception(
        """
func f{x}() {
    let x = cast(0, felt*);
    return ();
}
""",
        """
file:?:?: Reference rebinding must preserve the reference type. Previous type: 'felt', new type: \
'felt*'.
    let x = cast(0, felt*);
        ^
""",
    )
    verify_exception(
        """
func f{x}() {
    ret;
}
func g() {
    const x = 0;
    f();
    ret;
}
""",
        """
file:?:?: While trying to update the implicit return value 'x' in:
    f();
    ^*^
file:?:?: Redefinition of 'test_scope.g.x'.
func f{x}() {
       ^
""",
    )


def test_implcit_argument_bindings():
    code = """\
func f{x, y}() {
    ret;
}

func g{x, y, z}() {
    f{y=z}();
    return ();
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
ret;
[ap] = [fp + (-5)], ap++;
[ap] = [fp + (-3)], ap++;
call rel -3;
[ap] = [ap + (-2)], ap++;
[ap] = [fp + (-4)], ap++;
[ap] = [ap + (-3)], ap++;
ret;
"""
    )


def test_implcit_argument_bindings_failures():
    verify_exception(
        """
func foo{x}(y) -> (z: felt) {
    ret;
}

func bar() {
    let x = foo{5}(0);
    ret;
}
""",
        """
file:?:?: Implicit argument binding must be of the form: arg_name=var.
    let x = foo{5}(0);
                ^
""",
    )
    verify_exception(
        """
func foo{x}(y) -> (z: felt) {
    ret;
}

func bar() {
    let x = 0;
    let (res) = foo{y=x}(0);
    ret;
}
""",
        """
file:?:?: Unexpected implicit argument binding: y.
    let (res) = foo{y=x}(0);
                    ^
""",
    )
    verify_exception(
        """
func foo{x}(y) -> (z: felt) {
    ret;
}

func bar() {
    foo{x=2}(0);
    ret;
}
""",
        """
file:?:?: Implicit argument binding must be an identifier.
    foo{x=2}(0);
          ^
""",
    )


def test_func_args_scope():
    code = """\
const x = 1234;
[ap] = x, ap++;
func f(x, y, z) {
    x = 1, ap++;
    y = 2, ap++;
    z = 3, ap++;
    ret;
}
[ap + 4] = x, ap++;
[ap + 5] = f.Args.z, ap++;
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[ap] = 1234, ap++;
[fp + (-5)] = 1, ap++;
[fp + (-4)] = 2, ap++;
[fp + (-3)] = 3, ap++;
ret;
[ap + 4] = 1234, ap++;
[ap + 5] = 2, ap++;
"""
    )


def test_func_args_and_rets_scope():
    code = """\
const x = 1234;
[ap] = x, ap++;
func f(x, y, z) -> (a: felt, b: felt, x: felt) {
    x = 1, ap++;
    y = 2, ap++;
    [ap] = Args.y, ap++;
    ret;
}
[ap + 4] = x, ap++;
[ap + 5] = f.Args.x, ap++;
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[ap] = 1234, ap++;
[fp + (-5)] = 1, ap++;
[fp + (-4)] = 2, ap++;
[ap] = 1, ap++;
ret;
[ap + 4] = 1234, ap++;
[ap + 5] = 0, ap++;
"""
    )


def test_func_named_args():
    code = """\
func f(x, y, z) {
    ret;
}

let f_args = cast(ap, f.Args*);
f_args.z = 2, ap++;
f_args.x = 0, ap++;
f_args.y = 1, ap++;
static_assert f_args + f.Args.SIZE == ap;
call f;
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
ret;
[ap + 2] = 2, ap++;
[ap + (-1)] = 0, ap++;
[ap + (-1)] = 1, ap++;
call rel -7;
"""
    )


def test_func_named_args_failures():
    verify_exception(
        """
func f(x, y, z) {
    ret;
}

let f_args = cast(ap, f.Args*);
f_args.z = 2, ap++;
f_args.x = 0, ap++;
static_assert f_args + f.Args.SIZE == ap;
call f;
""",
        """
file:?:?: Static assert failed: ap + 1 != ap.
static_assert f_args + f.Args.SIZE == ap;
^***************************************^
""",
    )


def test_function_call_by_value_args():
    code = """\
struct S {
    a: felt,
    b: felt,
}

struct T {
    s: felt,
    t: S,
}
func f(w: S, x, y: T, z: T) {
    let s = S(a=13, b=17);
    let t: T = [cast(ap, T*)];
    let res = f(w=s, x=2, y=z, z=t);
    return ();
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[ap] = 13, ap++;
[ap] = 17, ap++;
[ap] = 2, ap++;
[ap] = [fp + (-5)], ap++;
[ap] = [fp + (-4)], ap++;
[ap] = [fp + (-3)], ap++;
[ap] = [ap + (-6)], ap++;
[ap] = [ap + (-6)], ap++;
[ap] = [ap + (-6)], ap++;
call rel -12;
ret;
"""
    )


@pytest.mark.parametrize(
    "test_line, expected_type, actual_type, arrow",
    [
        ("f(1, y=13)", "T", "felt", "^^"),
        ("f(1, y=&y)", "T", "T*", "^^"),
        ("f(1, y=t)", "T", "S", "^"),
    ],
)
def test_func_by_value_args_failures(test_line, expected_type, actual_type, arrow):
    verify_exception(
        f"""
struct T {{
    s: felt,
    t: felt,
}}
struct S {{
    s: felt,
    t: felt,
}}
func f(x, y: {expected_type}) {{
    local t: {actual_type};
    alloc_locals;
    {test_line};
    ret;
}}
""",
        f"""
file:?:?: Expected expression of type '{expected_type}', got '{actual_type}'.
    {test_line};
           {arrow}
""",
        main_scope=ScopedName(),
    )


def test_func_by_value_return():
    code = """\
struct T {
    s: felt,
    t: felt,
}
func f(s: T) -> (x: T, y: T) {
    let t: T = [cast(ap - 100, T*)];
    return (x=s, y=t);
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[ap] = [fp + (-4)], ap++;
[ap] = [fp + (-3)], ap++;
[ap] = [ap + (-102)], ap++;
[ap] = [ap + (-102)], ap++;
ret;
"""
    )


def test_unnamed_return_tuple_flow():
    code = """\
func foo() -> (felt*, felt) {
    return (cast(1, felt*), 2);
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[ap] = 1, ap++;
[ap] = 2, ap++;
ret;
"""
    )


def test_return_type_def():
    code = """\
using A = (felt*, felt);
func foo() -> A {
    return (cast(1, felt*), 2);
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[ap] = 1, ap++;
[ap] = 2, ap++;
ret;
"""
    )


def test_func_composition_flow1():
    code = """\
@known_ap_change
func foo{x}(arg: felt) -> felt {
    return 1;
}

func bar{x, y}() {
    tempvar res = 0;
    tempvar res2 = foo(1) + foo(res);
    tempvar res3 = foo(3 + foo(res2) + foo{x=y}(res) + foo(res2) + 2);
    return ();
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == strip_comments_and_linebreaks(
        """\
// foo.
[ap] = [fp + (-4)], ap++;
[ap] = 1, ap++;
ret;

// tempvar res = 0;
[ap] = 0, ap++;

// tempvar res2 = foo(1) + foo(res);
[ap] = [fp + (-4)], ap++;
[ap] = 1, ap++;
call rel -9;
[ap] = [ap + (-2)], ap++;
[ap] = [ap + (-8)], ap++;
call rel -13;
[ap] = [ap + (-7)] + [ap + (-1)], ap++;

// tempvar res3 = foo(3 + foo(res2) + foo{x=y}(res) + foo(res2) + 2);
[ap] = [ap + (-3)], ap++;
[ap] = [ap + (-2)], ap++;
call rel -18;
[ap] = [ap + (-1)] + 3, ap++;
[ap] = [fp + (-3)], ap++;
[ap] = [ap + (-22)], ap++;
call rel -24;
[ap] = [ap + (-7)] + [ap + (-1)], ap++;
[ap] = [ap + (-10)], ap++;
[ap] = [ap + (-16)], ap++;
call rel -29;
[ap] = [ap + (-1)] + 2, ap++;
[ap] = [ap + (-3)], ap++;
[ap] = [ap + (-9)] + [ap + (-2)], ap++;
call rel -35;
[ap] = [ap + (-2)], ap++;
[ap] = [ap + (-17)], ap++;
ret;
"""
    )

    code = """\
@known_ap_change
func foo{x}() -> felt* {
    return cast(1, felt*);
}

func bar{x}() -> felt {
    return foo() - foo();
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == strip_comments_and_linebreaks(
        """\
// foo.
[ap] = [fp + (-3)], ap++;
[ap] = 1, ap++;
ret;

// bar.
// tempvar res = foo() + 3;
[ap] = [fp + (-3)], ap++;
call rel -5;
[ap] = [ap + (-2)], ap++;
call rel -8;
[ap] = [ap + (-2)], ap++;
[ap] = [ap + (-7)] - [ap + (-2)], ap++;
ret;
"""
    )

    code = """\
@known_ap_change
func foo(x: felt) -> felt {
    return x;
}

tempvar res = foo([ap - 1]) + foo([ap - 1]);
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == strip_comments_and_linebreaks(
        """\
// foo.
[ap] = [fp + (-3)], ap++;
ret;

// tempvar res = foo([ap - 1]) + foo([ap - 1]);
call rel -2;
[ap] = [ap + (-4)], ap++;
call rel -5;
[ap] = [ap + (-5)] + [ap + (-1)], ap++;
"""
    )


def test_func_composition_flow2():
    code = """\
@known_ap_change
func foo{x, y, z}(arg1: felt, arg2: felt) -> felt {
    return 1;
}

func bar{x, y, z, w}() -> felt {
    if (foo{y=w}(foo{x=w}(1, 2), 3) != foo{x=z, z=w}(2, 1)) {
        return 1;
    }

    return foo{z=y}(foo(1, 1) + foo{x=w, y=z}(3, 1) + foo(w, x), 4) + foo{y=x}(x, y);
}
"""
    program1 = preprocess_str(code=code, prime=PRIME)

    code = """\
@known_ap_change
func foo{x, y, z}(arg1: felt, arg2: felt) -> felt {
    return 1;
}

func bar{x, y, z, w}() -> felt {
    let foo_1_2 = foo{x=w}(1, 2);
    let lhs = foo{y=w}(foo_1_2, 3);
    let rhs = foo{x=z, z=w}(2, 1);
    if (lhs != rhs) {
        return 1;
    }

    let foo_1_1 = foo(1, 1);
    let foo_3_1 = foo{x=w, y=z}(3, 1);
    tempvar sum = foo_1_1 + foo_3_1;
    let foo_w_x = foo(w, x);

    let temp = foo{z=y}(sum + foo_w_x, 4);
    let foo_x_y = foo{y=x}(x, y);
    let res = temp + foo_x_y;
    return res;
}
"""

    program2 = preprocess_str(code=code, prime=PRIME)

    assert program1.format() == program2.format()


def test_func_composition_failure():
    verify_exception(
        """
func foo() {
    ret;
}

foo(3) = foo(4);
""",
        """
file:?:?: Only functions with a simple return type are supported inside an expression. Got: '()'.
foo(3) = foo(4);
^****^
""",
        exc_type=CairoTypeError,
    )

    verify_exception(
        """
@known_ap_change
func foo() -> (felt, felt) {
    return (1, 2);
}

tempvar res = foo();
""",
        """
file:?:?: Only functions with a simple return type are supported inside an expression. \
Got: '(felt, felt)'.
tempvar res = foo();
              ^***^
""",
        exc_type=CairoTypeError,
    )

    verify_exception(
        """
func foo() -> felt {
    ap += [ap];
    return 1;
}

tempvar res = foo() + 3;
""",
        """
file:?:?: Only functions with known ap change may be used in an expression. \
Consider calling 'foo' in a separate line.
tempvar res = foo() + 3;
              ^***^
""",
    )

    verify_exception(
        """
@known_ap_change
func foo(p: felt*) -> felt {
    return 1;
}

tempvar res = foo(2) + 3;
""",
        """
file:?:?: Expected expression of type 'felt*', got 'felt'.
tempvar res = foo(2) + 3;
                  ^
""",
    )

    verify_exception(
        """
@known_ap_change
func foo{x}() -> felt {
    return (1);
}


tempvar res = foo{x=[ap]}();
""",
        """
file:?:?: Implicit argument binding must be an identifier.
tempvar res = foo{x=[ap]}();
                    ^**^
""",
    )


def test_func_call_in_reference():
    verify_exception(
        """\
@known_ap_change
func foo(p: felt*) -> felt {
    return 1;
}

let res = foo(2) + 3;
""",
        """
file:?:?: Function calls are not allowed inside reference expressions.
let res = foo(2) + 3;
          ^****^
""",
    )


@pytest.mark.parametrize(
    "jmp_code",
    [
        "jmp loop if [ap] != 0",
        "jmp rel 3",
        "jmp abs 3",
        "jmp rel [ap + 3] if [ap] != 0",
    ],
)
def test_function_flow_revoke(jmp_code):
    verify_exception(
        f"""
func foo() {{
    loop:
    {jmp_code};
    ret;
}}

func bar() {{
    tempvar x = 0;
    foo();
    assert x = 0;
    ret;
}}
""",
        """
file:?:?: Reference 'x' was revoked.
    assert x = 0;
           ^
Reference was defined here:
file:?:?
    tempvar x = 0;
            ^
""",
    )


def test_scope_label():
    code = """\
x:
jmp x;
jmp f;
call f;
func f() {
    jmp x;

    x:
    jmp x;
    jmp f.x;
}
jmp x;
jmp f.x;
jmp f;
call f;
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
jmp rel 0;
jmp rel 4;
call rel 2;
jmp rel 2;
jmp rel 0;
jmp rel -2;
jmp rel -12;
jmp rel -6;
jmp rel -10;
call rel -12;
"""
    )


def test_import():
    files = {
        ".": """
from a import f as g, h as h2
call g;
call h2;
""",
        "a": """
func f() {
    jmp f;
}

func h() {
    jmp h;
}
""",
    }
    program = preprocess_codes(
        codes=[(files["."], ".")],
        pass_manager=default_pass_manager(
            prime=PRIME, read_module=read_file_from_dict(dct={**files, **CAIRO_TEST_MODULES})
        ),
    )

    assert (
        program.format()
        == """\
jmp rel 0;
jmp rel 0;
call rel -4;
call rel -4;
"""
    )


def test_import_identifiers():
    # Define files used in this test.
    files = {
        ".": """
from a.b.c import alpha as x
from a.b.c import beta
from a.b.c import xi
""",
        "a.b.c": """
from tau import xi
const alpha = 0;
const beta = 1;
const gamma = 2;
""",
        "tau": """
const xi = 42;
""",
    }

    # Prepare auxiliary functions for tests.
    scope = ScopedName.from_string

    def get_full_name(name, curr_scope=""):
        try:
            return program.identifiers.search(
                accessible_scopes=[scope(curr_scope)], name=scope(name)
            ).get_canonical_name()
        except IdentifierError:
            return None

    # Preprocess program.
    program = preprocess_codes(
        codes=[(files["."], ".")],
        pass_manager=default_pass_manager(
            prime=PRIME, read_module=read_file_from_dict(dct={**files, **CAIRO_TEST_MODULES})
        ),
        main_scope=scope("__main__"),
    )

    # Verify identifiers are resolved correctly.
    assert get_full_name("x", "__main__") == scope("a.b.c.alpha")
    assert get_full_name("beta", "__main__") == scope("a.b.c.beta")
    assert get_full_name("xi", "__main__") == scope("tau.xi")

    assert get_full_name("alpha", "a.b.c") == scope("a.b.c.alpha")
    assert get_full_name("beta", "a.b.c") == scope("a.b.c.beta")
    assert get_full_name("gamma", "a.b.c") == scope("a.b.c.gamma")
    assert get_full_name("xi", "a.b.c") == scope("tau.xi")

    assert get_full_name("xi", "tau") == scope("tau.xi")

    # Verify inaccessible identifiers.
    assert get_full_name("alpha", "__main__") is None
    assert get_full_name("gamma", "__main__") is None
    assert get_full_name("a.b.c.alpha", "__main__") is None
    assert get_full_name("tau.xi", "__main__") is None


def test_import_errors():
    # Inaccessible import.
    verify_exception(
        """
from foo import bar
""",
        """
file:?:?: Could not load module 'foo'.
Error: 'foo'
from foo import bar
     ^*^
""",
        files={},
        exc_type=LocationError,
    )

    # Ignoring aliasing.
    verify_exception(
        """
from foo import bar as notbar
[ap] = bar;
""",
        """
file:?:?: Unknown identifier 'bar'.
[ap] = bar;
       ^*^
""",
        files={"foo": "const bar = 3;"},
    )

    # Identifier redefinition.
    verify_exception(
        """
const bar = 0;
from foo import bar
""",
        """
file:?:?: Redefinition of 'test_scope.bar'.
from foo import bar
                ^*^
""",
        files={"foo": "const bar = 0;"},
    )

    verify_exception(
        f"""
const lambda = 0;
from foo import bar as lambda
""",
        """
file:?:?: Redefinition of 'test_scope.lambda'.
from foo import bar as lambda
                       ^****^
""",
        files={"foo": "const bar = 0;"},
    )

    verify_exception(
        "from foo import bar",
        """ \
file:?:?: Cannot import 'bar' from 'foo'.
from foo import bar
                ^*^
""",
        files={"foo": ""},
    )


def test_error_scope_redefinition():
    verify_exception(
        """
from a import b
from a.b import c
""",
        """
Scope 'a.b' collides with a different identifier of type 'const'.
""",
        files={"a": "const b = 0;", "a.b": "const c = 1;"},
    )


def test_scope_failures():
    verify_exception(
        """
func f() {
    const x = 5;
    ret;
}
func g() {
    [ap] = x, ap++;
    ret;
}
""",
        """
file:?:?: Unknown identifier 'x'.
    [ap] = x, ap++;
           ^
""",
    )
    verify_exception(
        """
func f() {
    label:
    ret;
}
func g() {
    call label;
    ret;
}
""",
        """
file:?:?: Unknown identifier 'label'.
    call label;
         ^***^
""",
    )


def test_const_failures():
    verify_exception(
        """
const x = y;
""",
        """
file:?:?: Unknown identifier 'y'.
const x = y;
          ^
""",
    )
    verify_exception(
        """
const x = 0;
[ap] = x.y.z;
""",
        """
file:?:?: Unexpected '.' after 'test_scope.x' which is const.
[ap] = x.y.z;
       ^***^
""",
    )

    verify_exception(
        """
const x = [ap] + 5;
""",
        """
file:?:?: Expected a constant expression.
const x = [ap] + 5;
          ^******^
""",
    )


def test_labels():
    scope = ScopedName.from_string("my.cool.scope")
    program = preprocess_str(
        """
const x = 7;

a0:
[ap] = x, ap++;  // Size: 2.
[ap] = [fp] + 123;  // Size: 2.

a1:
[ap] = [fp];  // Size: 1.
jmp rel [fp];  // Size: 1.

a2:
jmp rel x;  // Size: 2.
jmp a3;  // Size: 2.
jmp a3 if [ap] != 0;  // Size: 2.
call a3;  // Size: 2.

a3:
""",
        prime=PRIME,
        main_scope=scope,
    )
    program_labels = {
        name: identifier_definition.pc
        for name, identifier_definition in program.identifiers.get_scope(scope).identifiers.items()
        if isinstance(identifier_definition, LabelDefinition)
    }
    assert program_labels == {"a0": 0, "a1": 4, "a2": 6, "a3": 14}


def test_process_file_scope():
    # Verify the good scenario.
    valid_scope = ScopedName.from_string("some.valid.scope")
    program = preprocess_str("const x = 4;", prime=PRIME, main_scope=valid_scope)

    assert program.identifiers.as_dict() == {valid_scope + "x": ConstDefinition(4)}


def test_label_resolution():
    program = preprocess_str(
        code="""
[ap] = 7, ap++;  // Size: 2.

loop:
[ap] = [ap - 1] + 1;  // Size: 2.
jmp future_label;  // Size: 2.
jmp future_label if [ap] != 0;  // Size: 2.
call future_label;  // Size: 2.
[fp] = [fp];  // Size: 1.

future_label:
jmp loop;  // Size: 2.
jmp loop if [ap] != 0;  // Size: 2.
call loop;  // Size 2.
""",
        prime=PRIME,
    )
    assert (
        program.format()
        == """\
[ap] = 7, ap++;
[ap] = [ap + (-1)] + 1;
jmp rel 7;
jmp rel 5 if [ap] != 0;
call rel 3;
[fp] = [fp];
jmp rel -9;
jmp rel -11 if [ap] != 0;
call rel -13;
"""
    )


def test_labels_failures():
    verify_exception(
        """
jmp x.y.z;
""",
        """
file:?:?: Unknown identifier 'x'.
jmp x.y.z;
    ^***^
""",
    )
    verify_exception(
        """
const x = 0;
jmp x;
""",
        """
file:?:?: Expected a label name. Identifier 'x' is of type const.
jmp x;
    ^
""",
    )


def test_redefinition_failures():
    verify_exception(
        """
name:
const name = 0;
""",
        """
file:?:?: Redefinition of 'test_scope.name'.
const name = 0;
      ^**^
""",
    )
    verify_exception(
        """
const name = 0;
let name = ap;
""",
        """
file:?:?: Redefinition of 'test_scope.name'.
let name = ap;
    ^**^
""",
    )
    verify_exception(
        """
let name = ap;

name:
""",
        """
file:?:?: Redefinition of 'test_scope.name'.
name:
^**^
""",
    )
    verify_exception(
        """
func f(name, x, name) {
    [ap + name] = 1;
    [ap + x] = 2;
}
""",
        """
file:?:?: Redefinition of 'test_scope.f.Args.name'.
func f(name, x, name) {
                ^**^
""",
    )
    verify_exception(
        """
func f() -> (name: felt, x: felt, name: felt) {
    [ap] = 1;
    [ap] = 2;
    ret;
}
""",
        """
file:?:?: Named tuple cannot have two entries with the same name.
func f() -> (name: felt, x: felt, name: felt) {
                                  ^********^
""",
    )


def test_directives():
    program = preprocess_str(
        code="""\
// This is a comment.

%builtins ab cd ef

[fp] = [fp];
""",
        prime=PRIME,
    )
    assert program.builtins == ["ab", "cd", "ef"]
    assert (
        program.format()
        == """\
%builtins ab cd ef

[fp] = [fp];
"""
    )


def test_directives_failures():
    verify_exception(
        """
[fp] = [fp];
%builtins ab cd ef
""",
        """
file:?:?: Directives must appear at the top of the file.
%builtins ab cd ef
^****************^
""",
    )
    verify_exception(
        """
%lang abc
""",
        """
file:?:?: Unsupported %lang directive. Are you using the correct compiler?
%lang abc
^*******^
""",
    )


def test_conditionals():
    program = preprocess_str(
        code="""
let x = 2;
if ([ap] * 2 == [fp] + 3) {
    let x = 3;
    [ap] = x, ap++;
} else {
    let x = 4;
    [ap] = x, ap++;
}
""",
        prime=PRIME,
    )
    assert (
        program.format()
        == """\
[ap] = [ap] * 2, ap++;
[ap] = [fp] + 3, ap++;
[ap] = [ap + (-2)] - [ap + (-1)], ap++;
jmp rel 6 if [ap + (-1)] != 0;
[ap] = 3, ap++;
jmp rel 4;
[ap] = 4, ap++;
"""
    )
    program = preprocess_str(
        code="""
if ([ap] == [fp]) {
    ret;
} else {
    [ap] = [ap];
}
[fp] = [fp];
""",
        prime=PRIME,
    )
    assert (
        program.format()
        == """\
[ap] = [ap] - [fp], ap++;
jmp rel 3 if [ap + (-1)] != 0;
ret;
[ap] = [ap];
[fp] = [fp];
"""
    )
    program = preprocess_str(
        code="""
if ([ap] == 0) {
    ret;
}
[fp] = [fp];
""",
        prime=PRIME,
    )
    assert (
        program.format()
        == """\
jmp rel 3 if [ap] != 0;
ret;
[fp] = [fp];
"""
    )
    # No jump if there is no "Non-equal" block.
    program = preprocess_str(
        code="""
if ([ap] == 0) {
    [fp + 1] = [fp + 1];
}
[fp] = [fp];
""",
        prime=PRIME,
    )
    assert (
        program.format()
        == """\
jmp rel 3 if [ap] != 0;
[fp + 1] = [fp + 1];
[fp] = [fp];
"""
    )
    program = preprocess_str(
        code="""
if ([ap] != 0) {
    ret;
}
[fp] = [fp];
""",
        prime=PRIME,
    )
    assert (
        program.format()
        == """\
jmp rel 4 if [ap] != 0;
jmp rel 3;
ret;
[fp] = [fp];
"""
    )
    # With locals.
    program = preprocess_str(
        code="""
func a() {
    alloc_locals;
    local a;
    if ([ap] != 0) {
        local b = 7;
        a = 5;
    } else {
        // This is a different local named b also.
        local b = 6;
        // This is the same local defined above.
        a = 3;
    }
    [fp] = [fp];
    ret;
}
""",
        prime=PRIME,
    )
    assert (
        program.format()
        == """\
ap += 3;
jmp rel 8 if [ap] != 0;
[fp + 2] = 6;
[fp] = 3;
jmp rel 6;
[fp + 1] = 7;
[fp] = 5;
[fp] = [fp];
ret;
"""
    )


def test_hints_good():
    code = """\
%{ hint0 %}
[fp] = [fp];
%{
    hint1
    hint2
%}
[fp] = [fp];
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == code


def test_hints_unindent():
    before = """\
%{
    hint1
    hint2
%}
[fp] = [fp];
func f() {
    %{
        if a:
            b
    %}
    [fp] = [fp];
    ret;
}
"""
    after = """\
%{
    hint1
    hint2
%}
[fp] = [fp];
%{
    if a:
        b
%}
[fp] = [fp];
ret;
"""
    program = preprocess_str(code=before, prime=PRIME)
    assert program.format() == after


def test_hints_failures():
    verify_exception(
        """
%{
    hint
%}
""",
        """
file:?:?: Found a hint at the end of a code block. Hints must be followed by an instruction.
%{
^^
""",
    )
    verify_exception(
        """
func f() {
    %{
        hint
    %}
}
[ap] = 1;
""",
        """
file:?:?: Found a hint at the end of a code block. Hints must be followed by an instruction.
    %{
    ^^
""",
    )
    verify_exception(
        """
[fp] = [fp];
%{
    hint
%}

label:
[fp] = [fp];
""",
        """
file:?:?: Hints before labels are not allowed.
%{
^^
""",
    )


def test_builtins_failures():
    verify_exception(
        """
%builtins a
%builtins b
""",
        """
file:?:?: Redefinition of builtins directive.
%builtins b
^*********^
""",
    )


def test_builtin_directive_duplicate_entry():
    verify_exception(
        """
%builtins pedersen ecdsa pedersen
""",
        """
file:?:?: The builtin 'pedersen' appears twice in builtins directive.
%builtins pedersen ecdsa pedersen
^*******************************^
""",
    )


def test_references():
    program = preprocess_str(
        code="""
call label1;

label1:
ret;

let x = ap + 1;

label2:
[x] = 1, ap++;
[x + 3] = 2, ap++;
[x - 2] = 3, ap++;
[x - 2] = 3, ap++;
jmp label1 if [x] != 0, ap++;
jmp label3 if [x] != 0;
[x - 2] = 4;
[x - 4] = 5;
[x - 6] = 6, ap++;
[ap] = [ap], ap++;
ap += 4;
[x] = 7;

call label3;

label3:
ret;

let y = ap;
[y] = 0, ap++;
[y] = 0, ap++;
""",
        prime=PRIME,
    )
    assert (
        program.format()
        == """\
call rel 2;
ret;
[ap + 1] = 1, ap++;
[ap + 3] = 2, ap++;
[ap + (-3)] = 3, ap++;
[ap + (-4)] = 3, ap++;
jmp rel -9 if [ap + (-3)] != 0, ap++;
jmp rel 15 if [ap + (-4)] != 0;
[ap + (-6)] = 4;
[ap + (-8)] = 5;
[ap + (-10)] = 6, ap++;
[ap] = [ap], ap++;
ap += 4;
[ap + (-10)] = 7;
call rel 2;
ret;
[ap] = 0, ap++;
[ap + (-1)] = 0, ap++;
"""
    )


def test_reference_type_deduction():
    scope = TEST_SCOPE
    program = preprocess_str(
        code="""
struct T {
    t: felt,
}

func foo() {
    let a = cast(0, T***);
    tempvar b = [a];
    tempvar c: felt* = [a];
    let d = [b];
    let e: felt* = [b];
    return ();
}
""",
        prime=PRIME,
        main_scope=scope,
    )

    def get_reference_type(name):
        identifier_definition = program.identifiers.get_by_full_name(scope + name)
        assert isinstance(identifier_definition, ReferenceDefinition)
        assert len(identifier_definition.references) == 1
        _, expr_type = simplify_type_system(identifier_definition.references[0].value)
        return expr_type

    assert get_reference_type("foo.a").format() == f"{scope}.T***"
    assert get_reference_type("foo.b").format() == f"{scope}.T**"
    assert get_reference_type("foo.c").format() == "felt*"
    assert get_reference_type("foo.d").format() == f"{scope}.T*"
    assert get_reference_type("foo.e").format() == "felt*"


def test_rebind_reference():
    program = preprocess_str(
        code="""
struct T {
    pad0: felt,
    pad1: felt,
    t: felt,
}

let x: T* = cast(ap + 1, T*);
let y = &x.t;
[cast(x, felt)] = x.t;
let x: T* = cast(fp - 3, T*);
[cast(x, felt)] = x.t;
[y] = [y];
""",
        prime=PRIME,
    )
    assert (
        program.format()
        == """\
[ap + 1] = [ap + 3];
[fp + (-3)] = [fp + (-1)];
[ap + 3] = [ap + 3];
"""
    )


def test_rebind_reference_failures():
    verify_exception(
        """
let x = cast(ap, felt*);
let x = cast(ap, felt**);
""",
        """
file:?:?: Reference rebinding must preserve the reference type. Previous type: 'felt*', \
new type: 'felt**'.
let x = cast(ap, felt**);
    ^
""",
    )


def test_invalid_references():
    verify_exception(
        """
let x = 3 * cast(nondet %{ rnadom.randrange(10) %}, felt) + 5;
""",
        """
file:?:?: The use of hints in reference expressions is not allowed.
let x = 3 * cast(nondet %{ rnadom.randrange(10) %}, felt) + 5;
            ^*******************************************^
""",
    )


def test_rvalue_func_call_reference_with_nondet():
    """
    Tests that nondet hints are computed exactly once when used as arguments to function calls
    in a reference expression.
    """
    program = preprocess_str(
        code="""
func foo(val) -> (res: felt) {
    return (res=val);
}
let x = foo(nondet %{ 5 %});
assert x = x;
""",
        prime=PRIME,
    )
    assert (
        program.format()
        == """\
[ap] = [fp + (-3)], ap++;
ret;
%{ memory[ap] = to_felt_or_relocatable(5) %}
ap += 1;
call rel -4;
[ap + (-1)] = [ap + (-1)];
"""
    )


def test_reference_over_calls():
    program = preprocess_str(
        code="""
func f() {
    ap += 3;
    jmp label1 if [ap] != 0, ap++;
    [ap] = [ap], ap++;
    ret;

    label1:
    ap += 1;
    ret;
}

let x = ap + 1;
[x] = 0;
call f;
[x] = 0;
""",
        prime=PRIME,
    )
    assert (
        program.format()
        == """\
ap += 3;
jmp rel 4 if [ap] != 0, ap++;
[ap] = [ap], ap++;
ret;
ap += 1;
ret;
[ap + 1] = 0;
call rel -11;
[ap + (-6)] = 0;
"""
    )


def test_struct_no_revocation():
    program = preprocess_str(
        code="""
struct A {
    x: felt,
    y: felt,
}
func main() -> (res: A) {
    alloc_locals;
    tempvar a: A = A(1, 2);
    ap += [ap];
    return (res=a);
}
""",
        prime=PRIME,
    )
    assert (
        program.format()
        == """\
ap += 2;
[ap] = 1, ap++;
[ap] = 2, ap++;
[fp] = [ap + (-2)];
[fp + 1] = [ap + (-1)];
ap += [ap];
[ap] = [fp], ap++;
[ap] = [fp + 1], ap++;
ret;
"""
    )


def test_reference_over_calls_no_revocation():
    program = preprocess_str(
        code="""
func f() {
    ap += 3;
    jmp label1 if [ap] != 0;
    [ap] = [ap], ap++;

    label1:
    ret;
}

func main() {
    alloc_locals;
    let x = [ap + 1];
    call f;
    x = 0;
    ret;
}
""",
        prime=PRIME,
    )
    assert (
        program.format()
        == """\
ap += 3;
jmp rel 3 if [ap] != 0;
[ap] = [ap], ap++;
ret;
ap += 1;
[fp] = [ap + 1];
call rel -9;
[fp] = 0;
ret;
"""
    )


def test_revoke_correction_invalid_reference():
    verify_exception(
        """
func main() {
    alloc_locals;
    let x = ap;
    ap += [ap];
    x = x;
}
""",
        """\
file:?:?: While auto generating local variable for 'x'.
    let x = ap;
        ^
file:?:?: While expanding the reference 'x' in:
    let x = ap;
        ^
file:?:?: ap may only be used in an expression of the form [ap + <const>].
    let x = ap;
            ^^
""",
    )


def test_dummy_reference_expr_error_flow():
    verify_exception(
        """\
func test() {
    alloc_locals;
    tempvar a;
    ap += [ap];  // Revoke reference to trigger auto locals flow.
    tempvar addr = &a;
    return ();
}
""",
        """
file:?:?: Using the value of fp directly, requires defining a variable named __fp__.
    tempvar addr = &a;
                    ^
""",
    )

    verify_exception(
        """\
struct MyStruct {
}

func test() {
    alloc_locals;
    tempvar a: MyStruct;
    ap += [ap];  // Revoke reference to trigger auto locals flow.
    assert a.missing_member = 5;
    return ();
}
""",
        """
file:?:?: Member 'missing_member' does not appear in definition of struct 'test_scope.MyStruct'.
    assert a.missing_member = 5;
           ^**************^
""",
        exc_type=CairoTypeError,
    )


def test_references_revoked_multiple_location():
    verify_exception(
        """
func main() {
    alloc_locals;
    if ([ap] == 0) {
        let x = [ap];
    } else {
        let y = [ap];
        let x = y;
    }
    ap += [fp];
    x = 0;
}
""",
        """\
file:?:?: Reference 'x' was revoked.
    x = 0;
    ^
Reference was defined here:
file:?:?
        let x = y;
            ^
file:?:?
        let x = [ap];
            ^
""",
    )


def test_auto_locals_inject_failed():
    verify_exception(
        """
func foo{x}() -> felt {
    ret;
}
func bar{x}() {
    alloc_locals;
    if (foo() == 0) {
    }
    ap += [ap];
    x = 0;
    return ();
}
""",
        """\
file:?:?: While trying to retrieve the implicit argument 'x' in:
    return ();
    ^********^
file:?:?: Reference 'x' was revoked.
func bar{x}() {
         ^
Reference was defined here:
file:?:?
    if (foo() == 0) {
        ^***^
""",
    )


@pytest.mark.parametrize(
    "revoking_instruction, alloc_locals, valid, has_def_location",
    [
        ("ap += [fp]", "alloc_locals;", True, None),
        ("ap += [fp]", "", False, True),
        ("ap += [fp]", "ap += SIZEOF_LOCALS;", False, True),
        ("call label", "alloc_locals;", True, None),
        ("call label", "", False, True),
        ("call rel 0", "alloc_locals;", True, None),
        ("call rel 0", "", False, True),
        ("ret", "alloc_locals;", False, False),
        ("jmp label", "alloc_locals;", False, False),
        ("jmp rel 0", "alloc_locals;", False, False),
        ("jmp abs 0", "alloc_locals;", False, False),
    ],
)
def test_references_revoked(revoking_instruction, valid, alloc_locals, has_def_location):
    code = f"""
func main() {{
    {alloc_locals}
    label:
    let x = [ap];
    {revoking_instruction};
    x = 0;
    ret;
}}
"""
    if not valid:
        assert has_def_location is not None
        def_loction_str = (
            """\
Reference was defined here:
file:?:?
    let x = [ap];
        ^
"""
            if has_def_location
            else ""
        )
        verify_exception(
            code,
            f"""
file:?:?: Reference 'x' was revoked.
    x = 0;
    ^
{def_loction_str}
""",
        )
    else:
        preprocess_str(code, prime=PRIME)


def test_references_failures():
    verify_exception(
        """
let ref = [fp];
let ref2 = ref;
[ref2] = [[fp]];
""",
        """
file:?:?: While expanding the reference 'ref2' in:
[ref2] = [[fp]];
 ^**^
file:?:?: While expanding the reference 'ref' in:
let ref2 = ref;
           ^*^
file:?:?: Expected a register. Found: [fp].
let ref = [fp];
          ^**^
Preprocessed instruction:
[[fp]] = [[fp]]
""",
        exc_type=InstructionBuilderError,
    )


@pytest.mark.parametrize(
    "valid, has0, has1, has2",
    [
        (False, True, True, True),
        (False, False, True, True),
        (False, True, False, True),
        (False, True, True, False),
        (False, False, True, False),
        (False, False, False, True),
        (True, True, False, False),
    ],
)
def test_reference_flow_revokes(valid, has0, has1, has2):
    def0 = "let ref = [fp];" if has0 else ""
    def1 = "let ref = [fp + 1];" if has1 else ""
    def2 = "let ref = [fp + 2];" if has2 else ""
    code = f"""
{def0}
jmp b if [ap] != 0;
a:
{def1}
jmp c;
b:
{def2}
c:
[ref] = [fp + 3];
"""
    if valid:
        preprocess_str(code, prime=PRIME)
    else:
        verify_exception(
            code,
            """
file:?:?: Reference 'ref' was revoked.
[ref] = [fp + 3];
 ^*^
""",
        )


def test_implicit_arg_revocation():
    verify_exception(
        """
func foo{x}(y) {
    foo(y=1);
    // The following instruction revokes the implicit argument x
    ap += [fp];
    return foo(y=2);
}
""",
        """
file:?:?: While trying to retrieve the implicit argument 'x' in:
    return foo(y=2);
           ^******^
file:?:?: Reference 'x' was revoked.
func foo{x}(y) {
         ^
Reference was defined here:
file:?:?
    foo(y=1);
    ^******^
""",
    )


def test_implicit_arg_no_revocation():
    program = preprocess_str(
        code="""
struct T {
    a: felt,
    b: felt,
}
func foo{x}(y) {
    alloc_locals;
    tempvar z: T = T(1, 2);
    foo(y=1);
    // The following instruction revokes the implicit argument x, which is therefore copied to a
    // local variable.
    ap += [fp];
    return foo(y=z.a);
}
""",
        prime=PRIME,
    )
    assert (
        program.format()
        == """\
ap += 3;
[ap] = 1, ap++;
[ap] = 2, ap++;
[fp] = [ap + (-2)];
[fp + 1] = [ap + (-1)];
[ap] = [fp + (-4)], ap++;
[ap] = 1, ap++;
call rel -11;
[fp + 2] = [ap + (-1)];
ap += [fp];
[ap] = [fp + 2], ap++;
[ap] = [fp], ap++;
call rel -17;
ret;
"""
    )


def test_reference_flow_converge():
    program = preprocess_str(
        """
if ([ap] != 0) {
    tempvar a = 1;
} else {
    tempvar a = 2;
}

assert a = a;
""",
        prime=PRIME,
    )
    assert (
        program.format()
        == """\
jmp rel 6 if [ap] != 0;
[ap] = 2, ap++;
jmp rel 4;
[ap] = 1, ap++;
[ap + (-1)] = [ap + (-1)];
"""
    )


def test_typed_references():
    scope = TEST_SCOPE
    program = preprocess_str(
        code="""
func main() {
    struct T {
        pad0: felt,
        pad1: felt,
        pad2: felt,
        b: T*,
    }

    struct Struct {
        pad0: felt,
        pad1: felt,
        a: T*,
    }

    let x: Struct* = cast(ap + 10, Struct*);
    let y: Struct = [x];

    [fp] = x.a;
    assert [fp] = cast(x.a.b, felt);
    assert [fp] = cast(x.a.b.b, felt);

    [fp] = y.a + 1;
    ret;
}
""",
        prime=PRIME,
        main_scope=scope,
    )

    def get_reference(name):
        scoped_name = scope + name
        assert isinstance(program.identifiers.get_by_full_name(scoped_name), ReferenceDefinition)

        return program.instructions[-1].flow_tracking_data.resolve_reference(
            reference_manager=program.reference_manager, name=scoped_name
        )

    expected_type_x = mark_type_resolved(parse_type(f"{scope}.main.Struct*"))
    assert simplify_type_system(get_reference("main.x").value)[1] == expected_type_x

    expected_type_y = mark_type_resolved(parse_type(f"{scope}.main.Struct"))
    reference = get_reference("main.y")
    assert simplify_type_system(reference.value)[1] == expected_type_y

    assert reference.value.format() == f"[cast(ap + 10, {scope}.main.Struct*)]"
    assert (
        program.format()
        == """\
[fp] = [ap + 12];
[fp] = [[ap + 12] + 3];
[ap] = [[ap + 12] + 3], ap++;
[fp] = [[ap + (-1)] + 3];
[fp] = [ap + 11] + 1;
ret;
"""
    )


def test_typed_references_failures():
    verify_exception(
        f"""
let x = fp;
x.a = x.a;
""",
        """
file:?:?: Cannot apply dot-operator to non-struct type 'felt'.
x.a = x.a;
^*^
""",
        exc_type=CairoTypeError,
    )
    verify_exception(
        """
struct T {
    z: felt,
}

let x: T = ap;
x.z = x.z;
""",
        """
file:?:?: Cannot assign an expression of type 'felt' to a reference of type 'test_scope.T'.
let x: T = ap;
       ^
""",
    )
    verify_exception(
        """
struct T {
    z: felt,
}

let x: T* = [cast(ap, T*)];
""",
        """
file:?:?: Cannot assign an expression of type 'test_scope.T' to a reference of type 'test_scope.T*'.
let x: T* = [cast(ap, T*)];
       ^^
""",
    )


def test_return_value_reference():
    scope = TEST_SCOPE
    program = preprocess_str(
        code="""
func foo() -> (val: felt, x: felt, y: felt) {
    ret;
}

func main() {
    let x = call foo;
    [ap] = 0, ap++;
    x.val = 9;

    let y: main.Return = call foo;

    let z = call abs 0;
    ret;
}
""",
        prime=PRIME,
        main_scope=scope,
    )

    def get_reference(name):
        scoped_name = scope + name
        assert isinstance(program.identifiers.get_by_full_name(scoped_name), ReferenceDefinition)

        return program.instructions[-1].flow_tracking_data.resolve_reference(
            reference_manager=program.reference_manager, name=scoped_name
        )

    assert simplify_type_system(get_reference("main.x").value)[1] == parse_type(
        "(val: felt, x: felt, y: felt)"
    )

    assert simplify_type_system(get_reference("main.y").value)[1] == parse_type("()")

    assert simplify_type_system(get_reference("main.z").value)[1] == parse_type("felt")

    assert (
        program.format()
        == """\
ret;
call rel -1;
[ap] = 0, ap++;
[ap + (-4)] = 9;
call rel -7;
call abs 0;
ret;
"""
    )


def test_return_value_reference_failures():
    verify_exception(
        """
let x = call foo;
""",
        """
file:?:?: Unknown identifier 'foo'.
let x = call foo;
             ^*^
""",
    )
    verify_exception(
        """
func foo() {
    ret;
}
let x = call foo;
[x.a] = 0;
""",
        """
file:?:?: Member 'a' does not appear in definition of tuple type '()'.
[x.a] = 0;
 ^*^
""",
        exc_type=CairoTypeError,
    )
    verify_exception(
        """
func foo() {
    ret;
}
let x: unknown_type* = call foo;
""",
        """
file:?:?: Unknown identifier 'unknown_type'.
let x: unknown_type* = call foo;
       ^**********^
""",
    )
    verify_exception(
        """
struct T {
    s: felt,
}
let x: T* = cast(ap, T*);
[ap] = x.a;
""",
        """
file:?:?: Member 'a' does not appear in definition of struct 'test_scope.T'.
[ap] = x.a;
       ^*^
""",
        exc_type=CairoTypeError,
    )


def test_unpacking():
    code = """\
struct T {
    a: felt,
    b: felt,
}
func f() -> (a: felt, b: felt, c: felt, d: felt, e: T) {
    return (1, 2, 3, 4, [cast(5, T*)]);
}
func g() {
    alloc_locals;
    let (a, local b, local c, d: T*, e) = f();
    a = d.b;
    a = b + c, ap++;
    a = b + c;
    // The type of e is deduced from the return type of f().
    a = e.b;
    let (a, _, local c, x, _) = f();
    ap += [ap];
    a = a;
    x = x;
    ret;
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[ap] = 5, ap++;
[ap] = 6, ap++;
[ap] = 1, ap++;
[ap] = 2, ap++;
[ap] = 3, ap++;
[ap] = 4, ap++;
[ap] = [[ap + (-6)]], ap++;
[ap] = [[ap + (-6)]], ap++;
ret;
ap += 5;
call rel -17;
[fp] = [ap + (-5)];
[fp + 1] = [ap + (-4)];
[ap + (-6)] = [[ap + (-3)] + 1];
[ap + (-6)] = [fp] + [fp + 1], ap++;
[ap + (-7)] = [fp] + [fp + 1];
[ap + (-7)] = [ap + (-2)];
call rel -25;
[fp + 2] = [ap + (-4)];
[fp + 3] = [ap + (-6)];
[fp + 4] = [ap + (-3)];
ap += [ap];
[fp + 3] = [fp + 3];
[fp + 4] = [fp + 4];
ret;
"""
    )


def test_unpacking_failures():
    verify_exception(
        """
func foo() -> (a: felt) {
    ret;
}
let (a, b) = foo();
""",
        """
file:?:?: Expected 1 unpacking identifier, found 2.
let (a, b) = foo();
     ^**^
""",
    )

    verify_exception(
        f"""
let (a, b) = 1 + 3;
""",
        """
file:?:?: Unpack binding is currently only supported for function calls. Got: 1 + 3.
let (a, b) = 1 + 3;
             ^***^
""",
    )

    verify_exception(
        """
struct T {
    a: felt,
    b: felt,
}
func foo() -> (a: felt, b: T) {
    ret;
}
let (a, b, c) = foo();
""",
        """
file:?:?: Expected 2 unpacking identifiers, found 3.
let (a, b, c) = foo();
     ^*****^
""",
    )

    verify_exception(
        """
struct T {
    a: felt,
    b: felt,
}
func foo() -> (a: felt, b: felt) {
    ret;
}
let (a, b: T) = foo();
""",
        """
file:?:?: Expected expression of type 'felt', got 'test_scope.T'.
let (a, b: T) = foo();
        ^**^
""",
    )

    verify_exception(
        """
struct T {
    a: felt,
    b: felt,
}
struct S {
    a: felt,
    b: felt,
}
func foo() -> (a: felt, b: T) {
    ret;
}
func test() {
    alloc_locals;
    let (a, local b: S) = foo();
    ret;
}
""",
        """
file:?:?: Expected expression of type 'test_scope.T', got 'test_scope.S'.
    let (a, local b: S) = foo();
            ^********^

""",
    )

    verify_exception(
        """
struct T {
}

func foo() -> (a: T*) {
    ret;
}

func test() {
    alloc_locals;
    let (local _: T*) = foo();
    ret;
}
""",
        """
file:?:?: Reference name cannot be '_'.
    let (local _: T*) = foo();
         ^*********^
""",
    )

    verify_exception(
        """
func foo() -> (a: felt) {
    ret;
}
let (a) = foo();
[a] = [a];
""",
        """
file:?:?: While expanding the reference 'a' in:
[a] = [a];
 ^
file:?:?: Expected a register. Found: [ap + (-1)].
let (a) = foo();
     ^
Preprocessed instruction:
[[ap + (-1)]] = [[ap + (-1)]]
""",
        exc_type=InstructionBuilderError,
    )

    verify_exception(
        """
func foo() -> felt {
    ret;
}
func bar() {
    let (a) = foo();
    ret;
}
""",
        """
file:?:?: Cannot unpack the return value of 'foo'. The return type is not a tuple.
    let (a) = foo();
              ^***^
Did you mean:
let a = foo();
""",
    )

    verify_exception(
        """
func foo() -> felt {
    ret;
}
func bar() {
    alloc_locals;
    let (local a) = foo();
    ret;
}
""",
        """
file:?:?: Cannot unpack the return value of 'foo'. The return type is not a tuple.
    let (local a) = foo();
                    ^***^
Did you mean:
local a = foo();
""",
    )

    verify_exception(
        """
func foo() -> felt {
    ret;
}
let (a, b) = foo();
""",
        """
file:?:?: Cannot unpack the return value of 'foo'. The return type is not a tuple.
let (a, b) = foo();
             ^***^

""",
    )


def test_unpacking_modifier_failure():
    verify_exception(
        """
func foo() -> (a: felt, b: felt) {
    ret;
}
let (a, local b) = foo();
""",
        """
file:?:?: Unexpected modifier 'local'.
let (a, local b) = foo();
        ^***^
""",
    )


def test_member_def_failures():
    verify_exception(
        """
struct T {
    t,
}
""",
        """
file:?:?: Struct members must be explicitly typed (e.g., x: felt).
    t,
    ^
""",
    )

    verify_exception(
        """
struct T {
    local t,
}
""",
        """
file:?:?: Unexpected modifier 'local'.
    local t,
    ^***^
""",
    )


def test_bad_type_annotation():
    verify_exception(
        """
func foo() {
    local a: foo;
    ret;
}
""",
        """
file:?:?: Expected 'test_scope.foo' to be struct or type_definition. Found: 'function'.
    local a: foo;
             ^*^
""",
    )

    verify_exception(
        """
func foo() {
    struct test {
        a: foo*,
    }

    ret;
}
""",
        """
file:?:?: Expected 'foo' to be a struct. Found: 'function'.
        a: foo*,
           ^*^
""",
    )

    verify_exception(
        """
func foo() {
    struct test {
        a: foo.abc*,
    }

    ret;
}
""",
        """
file:?:?: Unknown identifier 'test_scope.foo.abc'.
        a: foo.abc*,
           ^*****^
""",
    )


def test_cast_failure():
    verify_exception(
        """
struct A {
}

func foo(a: A*) {
    let a = cast(5, A);
    return ();
}
""",
        """
file:?:?: Cannot cast 'felt' to 'test_scope.A'.
    let a = cast(5, A);
            ^********^
""",
        exc_type=CairoTypeError,
    )


def test_nested_function_failure():
    verify_exception(
        """
func foo() {
    func bar() {
        return ();
    }
    return ();
}
""",
        """
file:?:?: Nested functions are not supported.
    func bar() {
         ^*^
Outer function was defined here: file:?:?
func foo() {
     ^*^
""",
    )


def test_namespace_inside_function_failure():
    verify_exception(
        """
func foo() {
    namespace MyNamespace {
    }
    return ();
}
""",
        """
file:?:?: Cannot define a namespace inside a function.
    namespace MyNamespace {
              ^*********^
Outer function was defined here: file:?:?
func foo() {
     ^*^
""",
    )


def test_namespace_is_not_a_label():
    verify_exception(
        """
namespace MyNamespace {
}
jmp MyNamespace;
""",
        """
file:?:?: Expected a label name. Identifier 'MyNamespace' is of type namespace.
jmp MyNamespace;
    ^*********^
""",
    )


def test_struct_assignments():
    struct_def = """\
struct B {
    a: felt,
    b: felt,
}

struct T {
    a: B,
    b: felt,
}
"""

    code = f"""\
{struct_def}
func f(t: T*) {{
    alloc_locals;
    local a: T = [t];
    return ();
}}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
ap += 3;
[fp] = [[fp + (-3)]];
[fp + 1] = [[fp + (-3)] + 1];
[fp + 2] = [[fp + (-3)] + 2];
ret;
"""
    )

    code = f"""\
{struct_def}
func copy(src: T**, dest: T**) {{
    assert [[dest]] = [[src]];
    return ();
}}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[ap] = [[fp + (-3)]], ap++;
[ap] = [[fp + (-4)]], ap++;
[ap] = [[ap + (-1)]], ap++;
[[ap + (-3)]] = [ap + (-1)];
[ap] = [[fp + (-3)]], ap++;
[ap] = [[fp + (-4)]], ap++;
[ap] = [[ap + (-1)] + 1], ap++;
[[ap + (-3)] + 1] = [ap + (-1)];
[ap] = [[fp + (-3)]], ap++;
[ap] = [[fp + (-4)]], ap++;
[ap] = [[ap + (-1)] + 2], ap++;
[[ap + (-3)] + 2] = [ap + (-1)];
ret;
"""
    )


def test_continuous_structs():
    code = """\
struct A {
    a: felt,
    b: felt,
}
struct B {
    a: A,
    b: felt,
}
struct C {
    a: A,
    b: B,
    c: felt,
}

func foo(x: C) {
    x.a.a = 1;
    x.a.b = 2;
    x.b.a.a = 3;
    x.b.a.b = 4;
    x.b.b = 5;
    x.c = 6;
    return ();
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[fp + (-8)] = 1;
[fp + (-7)] = 2;
[fp + (-6)] = 3;
[fp + (-5)] = 4;
[fp + (-4)] = 5;
[fp + (-3)] = 6;
ret;
"""
    )


def test_nested_struct_casting():
    code = """\
struct S {
    a: felt,
    b: felt,
}
func f(x: (felt, S)) {
    return ();
}

func main() {
    let s: S = S(2, 3);
    let arg: (felt, S) = (1, s);
    f(arg);
    return ();
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
ret;
[ap] = 1, ap++;
[ap] = 2, ap++;
[ap] = 3, ap++;
call rel -7;
ret;
"""
    )


def test_subscript_operator():
    code = """\
struct T {
    x: felt,
    y: felt,
}

struct S {
    a: T,
    b: T,
    c: T,
}

func f(s_arr: S*, table: felt**, perm: felt*) {
    assert s_arr[0].b.x = s_arr[1].a.y;
    assert (&s_arr[0].a)[2].x = (&s_arr[1].b.y)[-2];

    assert table[1][2] = 11;

    assert perm[0] = 1;
    assert perm[1] = 0;
    assert perm[perm[0]] = 0;

    tempvar i = 2;
    tempvar j = 5;
    tempvar k = -13;
    assert (&(&s_arr[i].b)[j].x)[k] = s_arr[1].c.y;
    assert table[i][j] = 17;

    return ();
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    expected_result = """\
[ap] = [[fp + (-5)] + 7], ap++;  // push s_arr[1].a.y
[[fp + (-5)] + 2] = [ap + (-1)];  // assert s_arr[0].b.x = s_arr[1].a.y

[ap] = [[fp + (-5)] + 7], ap++;  // push (&s_arr[1].b.y)[-2]
[[fp + (-5)] + 4] = [ap + (-1)];  // assert (&s_arr[0].a)[2].x = (&s_arr[1].b.y)[-2]

[ap] = [[fp + (-4)] + 1], ap++;  // push table[1]
[ap] = 11, ap++;  // push 11
[[ap + (-2)] + 2] = [ap + (-1)];  // assert table[1][2] = 11

[ap] = 1, ap++;  // push 1
[[fp + (-3)]] = [ap + (-1)];  // assert perm[0] = 1

[ap] = 0, ap++;  // push 0
[[fp + (-3)] + 1] = [ap + (-1)];  // assert perm[1] = 0

[ap] = [[fp + (-3)]], ap++;  // push perm[0]
[ap] = [fp + (-3)] + [ap + (-1)], ap++;  // push perm + perm[0]
[ap] = 0, ap++;  // push 0
[[ap + (-2)]] = [ap + (-1)];  // assert perm[perm[0]] = 0

[ap] = 2, ap++;  // tempvar i = 2
[ap] = 5, ap++;  // tempvar j = 5
[ap] = -13, ap++;  // tempvar k = -13

[ap] = [ap + (-3)] * 6, ap++;  // push i * 6
[ap] = [ap + (-1)] + 2, ap++;  // push i * 6 + 2
[ap] = [fp + (-5)] + [ap + (-1)], ap++;  // push &s_arr[i].b ( = s_arr + i * 6 + 2)
[ap] = [ap + (-5)] * 2, ap++;  // push j * 2
[ap] = [ap + (-2)] + [ap + (-1)], ap++;  // push &(&s_arr[i].b)[j].x
[ap] = [ap + (-1)] + [ap + (-6)], ap++;  // push &(&s_arr[i].b)[j].x + k
[ap] = [[fp + (-5)] + 11], ap++;  // push s_arr[1].b.y
[[ap + (-2)]] = [ap + (-1)];  // assert (&(&s_arr[i].a)[j].x)[k] = s_arr[1].b.y

[ap] = [fp + (-4)] + [ap + (-10)], ap++;  // push table + i
[ap] = [[ap + (-1)]], ap++;  // push table[i]
[ap] = [ap + (-1)] + [ap + (-11)], ap++;  // push table[i] + j
[ap] = 17, ap++;  // push 17
[[ap + (-2)]] = [ap + (-1)];  // assert table[i][j] = 17
ret;
"""
    assert program.format() == strip_comments_and_linebreaks(expected_result)


def test_dot_operator():
    code = """\
struct R {
    x: felt,
    r: R*,
}

struct S {
    x: felt,
    y: felt,
}

struct T {
    x: felt,
    s: S,
    sp: S*,
}

func f() {
    alloc_locals;
    let __fp__ = [fp - 100];

    local s: S;
    local s2: S;
    local t: T;
    local r1: R;

    s.x = 14;
    (s).y = 2;
    (&t).x = 7;
    assert t.s = s;

    ((t).s).x = t.x * 2;
    assert t.s = (t).s;
    assert (t.s).x = t.s.x;
    assert (&(t.s)).y = ((t).s).y;

    assert t.sp = &s;
    assert t.sp.x = 14;
    assert [t.sp].y = 2;
    assert [t.sp] = s;
    assert [t.sp] = (&t).s;
    assert &((t).s) = t.sp + 5;

    assert t.sp + 2 = &s2;
    assert [t.sp + 2].x = s.x;
    assert (t.sp + 2).y = s.y;

    assert [r1.r.r].r.r.r.r = &r1;

    return ();
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    expected_result = """\
ap += 10;  // alloc_locals
[fp] = 14;  // s.x = 14
[fp + 1] = 2;  // (s).y = 2
[fp + 4] = 7;  // (&t).x = 7
[fp + 5] = [fp];  // assert t.s = s (x member)
[fp + 6] = [fp + 1];  // assert t.s = s (y member)

[fp + 5] = [fp + 4] * 2;  // ((t).s).x = t.x * 2
[fp + 5] = [fp + 5];  // assert t.s = (t).s  (x member)
[fp + 6] = [fp + 6];  // assert t.s = (t).s  (y member)
[fp + 5] = [fp + 5];  // assert (t.s).x = t.s.x
[fp + 6] = [fp + 6];  // assert (&(t.s)).y = ((t).s).y

[fp + 7] = [fp + (-100)];  // assert t.sp = &s
[ap] = 14, ap++;  // push 14
[[fp + 7]] = [ap + (-1)];  // assert t.sp.x = 14
[ap] = 2, ap++;  // push 2
[[fp + 7] + 1] = [ap + (-1)];  // assert [t.sp].y = 2
[[fp + 7]] = [fp];  // assert [t.sp] = s (x member)
[[fp + 7] + 1] = [fp + 1];  // assert [t.sp] = s (y member)
[[fp + 7]] = [fp + 5];  // assert [t.sp] = (&t).s (x member)
[[fp + 7] + 1] = [fp + 6];  // assert [t.sp] = (&t).s (y member)
[ap] = [fp + 7] + 5, ap++;  // push t.sp + 5
[fp + (-100)] + 5 = [ap + (-1)];  // assert &(t.s) = t.sp + 5

[ap] = [fp + (-100)] + 2, ap++;  // push &s2
[fp + 7] + 2 = [ap + (-1)];  // assert t.sp + 2 = &s2
[[fp + 7] + 2] = [fp];  // assert [t.sp + 2].x = s.x
[[fp + 7] + 3] = [fp + 1];  // assert (t.sp + 2).y = s.y

// assert [r1.r.r].r.r.r.r = &r1 :
[ap] = [[fp + 9] + 1], ap++;  // push (r1.r).r ([fp + 9] = r1.r)
[ap] = [[ap + (-1)] + 1], ap++;  // push (r1.r.r).r
[ap] = [[ap + (-1)] + 1], ap++;  // push (r1.r.r.r).r
[ap] = [[ap + (-1)] + 1], ap++;  // push (r1.r.r.r.r).r
[ap] = [fp + (-100)] + 8, ap++;  // push &r1
[[ap + (-2)] + 1] = [ap + (-1)];  // assert (r1.r.r.r.r.r).r = &r1
ret;
"""
    assert program.format() == strip_comments_and_linebreaks(expected_result)


def test_tuple_assertions():
    code = """\
func f() {
    alloc_locals;
    local var: (felt, felt) = [cast(ap, (felt, felt)*)];
    return ();
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
ap += 2;
[fp] = [ap];
[fp + 1] = [ap + 1];
ret;
"""
    )


def test_tuple_expression():
    code = """\
struct A {
    x: felt,
    y: felt*,
}
struct B {
    x: felt,
    y: A,
    z: A*,
}
func foo(a: A*) {
    alloc_locals;
    let a: A* = cast([fp], A*);
    local b: B = cast((1, [a], a), B);

    assert (b.x, b.z, a) = (5, a, a);
    return ();
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
ap += 4;
[fp] = 1;
[fp + 1] = [[fp]];
[fp + 2] = [[fp] + 1];
[fp + 3] = [fp];
[fp] = 5;
[fp + 3] = [fp];
[fp] = [fp];
ret;
"""
    )


def test_tuple_expression_failures():
    verify_exception(
        """
struct A {
    x: felt,
}
struct B {
}
let a = cast(fp, A*);
let b = cast((1, a), B);
""",
        """
file:?:?: Cannot cast an expression of type '(felt, test_scope.A*)' to 'test_scope.B'.
The former has 2 members while the latter has 0 members.
let b = cast((1, a), B);
             ^****^
""",
        exc_type=CairoTypeError,
    )

    verify_exception(
        """
struct A {
    x: felt,
    y: felt,
}
struct B {
    a: felt,
    b: felt,
}
let a = [cast(fp, A*)];
let b = cast((a, 1), B);
""",
        """
file:?:?: While expanding the reference 'a' in:
let b = cast((a, 1), B);
              ^
file:?:?: Cannot cast 'test_scope.A' to 'felt'.
let a = [cast(fp, A*)];
        ^************^
""",
        exc_type=CairoTypeError,
    )

    verify_exception(
        """
struct A {
    x: felt,
    y: felt,
}
struct B {
    a: felt,
    b: A,
}
let b = cast([cast(ap, (felt, felt*)*)], B);
""",
        """
file:?:?: Cannot cast 'felt*' to 'test_scope.A'.
let b = cast([cast(ap, (felt, felt*)*)], B);
             ^************************^
""",
        exc_type=CairoTypeError,
    )

    verify_exception(
        """
struct B {
}
let b = cast([cast(ap, (felt, felt*)*)], B);
""",
        """
file:?:?: Cannot cast an expression of type '(felt, felt*)' to 'test_scope.B'.
The former has 2 members while the latter has 0 members.
let b = cast([cast(ap, (felt, felt*)*)], B);
             ^************************^
""",
        exc_type=CairoTypeError,
    )
    verify_exception(
        """
(1, 1) = 1;
""",
        """
file:?:?: Expected a 'felt' or a pointer type. Got: '(felt, felt)'.
(1, 1) = 1;
^****^
""",
    )

    verify_exception(
        """
assert (1, 1) = 1;
""",
        """
file:?:?: Cannot compare '(felt, felt)' and 'felt'.
assert (1, 1) = 1;
^****************^
""",
    )

    verify_exception(
        """
let x = (1, a=2, b=(c=()));
""",
        """
file:?:?: All fields in a named tuple must have a name.
let x = (1, a=2, b=(c=()));
        ^****************^
""",
    )


def test_named_tuple_types():
    code = """
func foo(a: (felt, (x: felt, y: felt))) {
    tempvar tmp0 = a[0];
    tempvar tmp1 = a[1].y;
    tempvar tmp2 = a[1][1];
    ret;
}

foo((0, (x=1, y=2)));
// You can pass named to unnamed and vice versa.
foo((a=0, b=(1, 2)));
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[ap] = [fp + (-5)], ap++;
[ap] = [fp + (-3)], ap++;
[ap] = [fp + (-3)], ap++;
ret;
[ap] = 0, ap++;
[ap] = 1, ap++;
[ap] = 2, ap++;
call rel -10;
[ap] = 0, ap++;
[ap] = 1, ap++;
[ap] = 2, ap++;
call rel -18;
"""
    )


def test_named_tuple_types_failure():
    verify_exception(
        """
func foo(arg: (a: (b: felt, b: felt), c: felt)) {
}
""",
        """
file:?:?: Named tuple cannot have two entries with the same name.
func foo(arg: (a: (b: felt, b: felt), c: felt)) {
                            ^*****^
""",
    )
    verify_exception(
        """
let x = (a=(b=1, b=2), c=0);
""",
        """
file:?:?: Named tuple cannot have two entries with the same name.
let x = (a=(b=1, b=2), c=0);
                 ^*^
""",
    )
    verify_exception(
        """
func foo(x: (felt, b: felt)) {
    ret;
}
""",
        """
file:?:?: All fields in a named tuple must have a name.
func foo(x: (felt, b: felt)) {
            ^*************^
""",
    )


def test_struct_constructor():
    code = """\
struct M {
}
struct A {
    x: M*,
    y: felt,
}
struct B {
    x: felt,
    y: A,
    z: A,
    w: A*,
}
func foo(m_ptr: M*, a_ptr: A*) {
    alloc_locals;
    local b1: B = B(x=0, y=A(m_ptr, 2), z=[a_ptr], w=a_ptr);
    let a = A(x=a_ptr.x, y=0);
    assert a = A(x=m_ptr, y=2);

    let b2: B = B(x=0, y=A(m_ptr, 2), z=[a_ptr], w=a_ptr);
    assert b2 = b2;

    tempvar y: felt* = cast(1, felt*);
    tempvar x: A* = cast(0, A*);
    assert [x] = A(x=m_ptr, y=[y]);
    return ();
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    expected_result = """\
ap += 6;
// Populate b1.
[fp] = 0;
[fp + 1] = [fp + (-4)];
[fp + 2] = 2;
[fp + 3] = [[fp + (-3)]];
[fp + 4] = [[fp + (-3)] + 1];
[fp + 5] = [fp + (-3)];

// assert a = A(x=m_ptr, y=2) (x component).
[[fp + (-3)]] = [fp + (-4)];

// assert a = A(x=m_ptr, y=2) (y component).
[ap] = 2, ap++;
0 = [ap + (-1)];

// assert b2 = b2.
[ap] = 0, ap++;
0 = [ap + (-1)];
[fp + (-4)] = [fp + (-4)];
[ap] = 2, ap++;
2 = [ap + (-1)];
[ap] = [[fp + (-3)]], ap++;
[[fp + (-3)]] = [ap + (-1)];
[ap] = [[fp + (-3)] + 1], ap++;
[[fp + (-3)] + 1] = [ap + (-1)];
[fp + (-3)] = [fp + (-3)];

// tempvar y: felt* = cast(1, felt*).
[ap] = 1, ap++;
// tempvar x: A* = cast(0, A*).
[ap] = 0, ap++;
// assert [x] = A(x=m_ptr, y=[y]).
[[ap + (-1)]] = [fp + (-4)];
[ap] = [[ap + (-2)]], ap++;
[[ap + (-2)] + 1] = [ap + (-1)];
ret;
"""
    assert program.format() == strip_comments_and_linebreaks(expected_result)


def test_struct_constructor_failures():
    verify_exception(
        """
using A = (felt, felt);
using B = A;

assert B(1, 2) = 0;
""",
        """
file:?:?: Struct constructor cannot be used for type '(felt, felt)'.
assert B(1, 2) = 0;
       ^*****^
""",
        exc_type=CairoTypeError,
    )
    verify_exception(
        """
struct A {
    next: A*,
}

assert A(next=0) = A(next=0);
""",
        """
file:?:?: Cannot cast 'felt' to 'test_scope.A*'.
assert A(next=0) = A(next=0);
              ^
""",
        exc_type=CairoTypeError,
    )

    def verify_exception_for_expr(expr_str: str, expected_error: str):
        verify_exception(
            f"""
struct T {{
    x: felt,
    y: felt,
}}

func foo(a) {{
    alloc_locals;
    local a: T = {expr_str};
}}
""",
            expected_error,
            exc_type=CairoTypeError,
        )

    verify_exception_for_expr(
        "T(x=5, y=6, z=7)",
        """
file:?:?: Cannot cast an expression of type '(x: felt, y: felt, z: felt)' to 'test_scope.T'.
The former has 3 members while the latter has 2 members.
    local a: T = T(x=5, y=6, z=7);
                 ^**************^
""",
    )

    verify_exception_for_expr(
        "T(x=5)",
        """
file:?:?: Cannot cast an expression of type '(x: felt)' to 'test_scope.T'.
The former has 1 members while the latter has 2 members.
    local a: T = T(x=5);
                 ^****^
""",
    )

    verify_exception_for_expr(
        "&T(5, 6)",
        """
file:?:?: Expression has no address.
    local a: T = &T(5, 6);
                  ^*****^
""",
    )

    verify_exception_for_expr(
        "T(a=5, b=6)",
        """
file:?:?: Argument name mismatch for 'test_scope.T': expected 'x', found 'a'.
    local a: T = T(a=5, b=6);
                   ^
""",
    )

    verify_exception_for_expr(
        "T(5, x=6)",
        """
file:?:?: Argument name mismatch for 'test_scope.T': expected 'y', found 'x'.
    local a: T = T(5, x=6);
                      ^
""",
    )

    verify_exception_for_expr(
        "T(5, 6).x",
        """
file:?:?: Accessing struct/tuple members for r-value structs is not supported yet.
    local a: T = T(5, 6).x;
                 ^*******^
""",
    )

    verify_exception_for_expr(
        "T{a}(5, 6)",
        """
file:?:?: Implicit arguments cannot be used with struct constructors.
    local a: T = T{a}(5, 6);
                   ^
""",
    )


def test_unsupported_decorator():
    verify_exception(
        """
@external
func foo() {
    return ();
}
""",
        """
file:?:?: Unsupported decorator: 'external'.
@external
 ^******^
""",
    )


def test_skipped_functions():
    files = {
        "module": """
func func0() {
    tempvar x = 0;
    return ();
}
func func1() {
    tempvar x = 1;
    return ();
}
func func2() {
    tempvar x = 2;
    return func1();
}
""",
        ".": """
from module import func2
func2();
""",
    }
    program = preprocess_codes(
        codes=[(files["."], ".")],
        pass_manager=default_pass_manager(
            prime=PRIME, read_module=read_file_from_dict(dct={**files, **CAIRO_TEST_MODULES})
        ),
    )
    assert (
        program.format()
        == """\
[ap] = 1, ap++;
ret;
[ap] = 2, ap++;
call rel -5;
ret;
call rel -5;
"""
    )
    program = preprocess_codes(
        codes=[(files["."], ".")],
        pass_manager=default_pass_manager(
            prime=PRIME,
            read_module=read_file_from_dict(dct={**files, **CAIRO_TEST_MODULES}),
            opt_unused_functions=False,
        ),
    )
    assert program.format() == strip_comments_and_linebreaks(
        """\
ret;  // get_ap is here because opt_unused_functions is false.
[ap] = 0, ap++;
ret;
[ap] = 1, ap++;
ret;
[ap] = 2, ap++;
call rel -5;
ret;
call rel -5;
"""
    )


def test_known_ap_change_decorator():
    # Positive case.
    code = """\
func bar() {
    return ();
}

@known_ap_change
func foo(arg: felt) {
    alloc_locals;
    local local_var;
    tempvar tmp = 0;
    bar();
    return ();
}
"""
    preprocess_str(code=code, prime=PRIME)

    # Negative case.
    verify_exception(
        """
@known_ap_change
func foo() {
    foo();
    return ();
}
""",
        """
file:?:?: The compiler was unable to deduce the change of the ap register, as required by this \
decorator.
@known_ap_change
 ^*************^
""",
    )


def test_define_word_failure():
    verify_exception(
        """
tempvar x = 5;
dw x;
""",
        """
file:?:?: While expanding the reference 'x' in:
dw x;
   ^
file:?:?: dw must be followed by a constant expression.
tempvar x = 5;
        ^
Preprocessed instruction:
dw [ap + (-1)]
""",
        exc_type=InstructionBuilderError,
    )


def test_label_arithmetic_flow():
    code = """
label1:
assert 4 = label2 - label1;

label2:
assert 4 = label2 - label1;
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[ap] = 4, ap++;
4 = [ap + (-1)];
[ap] = 4, ap++;
4 = [ap + (-1)];
"""
    )


def test_label_arithmetic_failure():
    verify_exception(
        """
tempvar code_offset: codeoffset;
assert 0 = code_offset - 5;
""",
        """
file:?:?: Operator '-' is not implemented for types 'codeoffset' and 'felt'.
assert 0 = code_offset - 5;
           ^*************^
""",
        exc_type=CairoTypeError,
    )

    verify_exception(
        """
func foo() {
    assert foo = 5;
    return ();
}
""",
        """
file:?:?: Cannot compare 'codeoffset' and 'felt'.
    assert foo = 5;
    ^*************^
""",
    )


def test_future_label_substraction_failure():
    """
    Subtracting two future labels doesn't work at the moment.
    The test is here to check the error message.
    """

    verify_exception(
        """
assert 0 = label2 - label1;

label1:

label2:
""",
        """
file:?:?: Expected a constant expression or a dereference expression.
assert 0 = label2 - label1;
                    ^****^
Preprocessed instruction:
[ap] = [ap + (-1)] - label1, ap++
""",
        exc_type=InstructionBuilderError,
    )


def test_future_label_minus_tempvar():
    code = """
tempvar a = cast(0, codeoffset);
assert 0 = label1 - a;

label1:
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[ap] = 0, ap++;
[ap] = 7, ap++;
[ap] = [ap + (-1)] - [ap + (-2)], ap++;
0 = [ap + (-1)];
"""
    )


def test_new_operator_flow():
    code = """
struct MyStruct {
    a: felt,
    b: felt,
}

func test() -> (my_struct: MyStruct*) {
    tempvar t = 37;
    tempvar my_struct = new MyStruct(a=1, b=2);

    // Check that 't' wasn't revoked and that the type of a is MyStruct*.
    assert cast(t, MyStruct*) = my_struct;
    assert cast(t, MyStruct*) = new MyStruct(a=3, b=[new 4]);
    return (my_struct=my_struct);
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == strip_comments_and_linebreaks(
        """\
// A dummy get_ap().
ret;

[ap] = 37, ap++;

// tempvar my_struct = new MyStruct(a=1, b=2).
[ap] = 1, ap++;
[ap] = 2, ap++;
call rel -7;  // call get_ap()
[ap] = [ap + (-1)] + (-2), ap++;  // [ap] = get_ap() - MyStruct.SIZE
// assert cast(t, MyStruct*) = my_struct.
[ap + (-6)] = [ap + (-1)];

// new 4.
[ap] = 4, ap++;
call rel -14;
[ap] = [ap + (-1)] + (-1), ap++;

// new MyStruct(a=3, b=[new 4]).
[ap] = 3, ap++;
[ap] = [[ap + (-2)]], ap++;
call rel -21;
[ap] = [ap + (-1)] + (-2), ap++;

// assert cast(t, MyStruct*) = new MyStruct(a=3, b=[new 4]).
[ap + (-15)] = [ap + (-1)];
// return (my_struct=my_struct).
[ap] = [ap + (-10)], ap++;
ret;
"""
    )

    code = """
func test() -> (felt_ptr: felt*) {
    return (felt_ptr=new ([fp] + 5));
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == strip_comments_and_linebreaks(
        """\
// A dummy get_ap().
ret;

[ap] = [fp] + 5, ap++;
call rel -3;  // call get_ap()
[ap] = [ap + (-1)] + (-1), ap++;
ret;
"""
    )

    code = """
func test() -> (tuple_ptr: (felt, felt)*) {
    return (tuple_ptr=new (7, 8));
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert program.format() == strip_comments_and_linebreaks(
        """\
// A dummy get_ap().
ret;

[ap] = 7, ap++;
[ap] = 8, ap++;
call rel -5;  // call get_ap()
[ap] = [ap + (-1)] + (-2), ap++;
ret;
"""
    )


def test_new_operator_failure():
    verify_exception(
        """
new MyStruct(a=1, b=2) = 13;
""",
        """
file:?:?: The new operator is not supported outside of a function.
new MyStruct(a=1, b=2) = 13;
^********************^
""",
    )

    verify_exception(
        """
struct MyStruct {
    a: felt,
    b: felt,
}
func test() {
    new MyStruct(a=1, b=2) = 13;
    return ();
}
""",
        """
file:?:?: Expected a dereference expression.
    new MyStruct(a=1, b=2) = 13;
    ^********************^
Preprocessed instruction:
new (1, 2) = 13
""",
        exc_type=InstructionBuilderError,
    )

    verify_exception(
        """
new MyStruct(a=1, b=2) = 13;
""",
        """
file:?:?: The new operator is not supported outside of a function.
new MyStruct(a=1, b=2) = 13;
^********************^
""",
    )
    verify_exception(
        """
func test() {
    alloc_locals;
    local x = new 5;
    return ();
}
""",
        """
file:?:?: Cannot cast 'felt*' to 'felt'.
    local x = new 5;
              ^***^
""",
        exc_type=CairoTypeError,
    )

    verify_exception(
        """
func test() {
    let x = new 5;
    return ();
}
""",
        """
file:?:?: The use of 'new' in reference expressions is not allowed.
    let x = new 5;
            ^***^
""",
    )


def test_type_definition():
    code = """
namespace a {
    namespace b {
        using Point = (felt, felt);
    }
    namespace c {
        using TwoPoints = (b.Point, b.Point);
    }
}

func foo(z: a.b.Point) {
    alloc_locals;
    tempvar x: a.c.TwoPoints = ((0, 1), [cast(fp, a.b.Point*)]);
    local y: a.c.TwoPoints;
    assert x[0] = z;
    return ();
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
ap += 4;
[ap] = 0, ap++;
[ap] = 1, ap++;
[ap] = [fp], ap++;
[ap] = [fp + 1], ap++;
[ap + (-4)] = [fp + (-4)];
[ap + (-3)] = [fp + (-3)];
ret;
"""
    )
    two_points = program.identifiers.get_by_full_name(TEST_SCOPE + "a.c.TwoPoints")
    assert (
        isinstance(two_points, TypeDefinition)
        and two_points.cairo_type.format() == "((felt, felt), (felt, felt))"
    )


def test_type_definition_failure():
    verify_exception(
        """
using Point = Point;
""",
        """
file:?:?: Cannot use a type before its definition.
using Point = Point;
              ^***^
""",
    )
    verify_exception(
        """
using Point2 = (Point, Point);
using Point = (felt, felt);
""",
        """
file:?:?: Cannot use a type before its definition.
using Point2 = (Point, Point);
                ^***^
""",
    )
    verify_exception(
        """
%{ %}
using Point = (felt, felt);
""",
        """
file:?:?: Hints before "using" statements are not allowed.
%{ %}
^***^
""",
    )


def test_if_with_single_and():
    code = """
func main() {
    tempvar a = 10;
    tempvar b = 12;
    if (a == 10 and b == 12) {
        tempvar x = a + b;
    }
    ret;
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
[ap] = 10, ap++;
[ap] = 12, ap++;
[ap] = [ap + (-2)] + (-10), ap++;
jmp rel 7 if [ap + (-1)] != 0;
[ap] = [ap + (-2)] + (-12), ap++;
jmp rel 3 if [ap + (-1)] != 0;
[ap] = [ap + (-4)] + [ap + (-3)], ap++;
ret;
"""
    )
