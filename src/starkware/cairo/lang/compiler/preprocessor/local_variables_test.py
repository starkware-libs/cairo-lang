from starkware.cairo.lang.compiler.preprocessor.preprocessor_test_utils import (
    PRIME,
    preprocess_str,
    verify_exception,
)
from starkware.cairo.lang.compiler.type_casts import CairoTypeError


def test_local_variable():
    code = """\
struct MyStruct {
    a: felt,
    b: felt,
}

func main() {
    ap += 5 + SIZEOF_LOCALS;
    local x;
    local y: MyStruct;
    local z = x * y.a;
    x = y.a;
    y.b = z;
    local w: MyStruct* = cast(17, MyStruct*);
    // Check implicit cast from MyStruct* to felt*.
    local w_as_felt_ptr: felt* = w;
    z = w.b;
    ret;
}

func no_locals() {
    ap += SIZEOF_LOCALS;
    ret;
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
ap += 11;
[fp + 3] = [fp] * [fp + 1];
[fp] = [fp + 1];
[fp + 2] = [fp + 3];
[fp + 4] = 17;
[fp + 5] = [fp + 4];
[fp + 3] = [[fp + 4] + 1];
ret;
ap += 0;
ret;
"""
    )


def test_local_variable_unpack_binding():
    code = """\
struct MyStruct {
    a: felt,
    b: felt,
}

func foo() -> (x: MyStruct*, y: MyStruct, z: felt) {
    ret;
}

func main() {
    alloc_locals;
    let (local x, y, local z) = foo();
    x.b = z;
    y.a = z;
    y.b = z;
    z = z;
    ret;
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
ret;
ap += 2;
call rel -3;
[fp] = [ap + (-4)];
[fp + 1] = [ap + (-1)];
[[fp] + 1] = [fp + 1];
[ap + (-3)] = [fp + 1];
[ap + (-2)] = [fp + 1];
[fp + 1] = [fp + 1];
ret;
"""
    )


def test_local_rebinding():
    code = """\
func main() {
    alloc_locals;
    local x = 5;
    local x = x * x;
    local x = x + x;
    local x = x * x;
    ret;
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
ap += 4;
[fp] = 5;
[fp + 1] = [fp] * [fp];
[fp + 2] = [fp + 1] + [fp + 1];
[fp + 3] = [fp + 2] * [fp + 2];
ret;
"""
    )


def test_n_locals_used_in_static_assert():
    code = """\
func main() {
    static_assert 3 == SIZEOF_LOCALS + 2;
    local x;
    ret;
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
ret;
"""
    )


def test_inner_scopes_local_variables():
    code = """\
func main() {
    alloc_locals;

    if (1 == 1) {
        local a;
    }

    with_attr error_message("test") {
        local b;
    }

    let x = 0;
    with x {
        local c;
    }

    return ();
}
"""
    program = preprocess_str(code=code, prime=PRIME)
    assert (
        program.format()
        == """\
ap += 3;
[ap] = 0, ap++;
jmp rel 2 if [ap + (-1)] != 0;
ret;
"""
    )


def test_local_variable_failures():
    verify_exception(
        """
func main(SIZEOF_LOCALS) {
    static_assert SIZEOF_LOCALS == SIZEOF_LOCALS;
    local x;
}
""",
        """
file:?:?: The name 'SIZEOF_LOCALS' is reserved and cannot be used as an argument name.
func main(SIZEOF_LOCALS) {
          ^***********^
""",
    )
    verify_exception(
        """
func main() {
    local x;
}
""",
        """
file:?:?: A function with local variables must use alloc_locals.
    local x;
    ^******^
""",
    )
    verify_exception(
        """
func main() {
    alloc_locals;
    local x = x + x;
}
""",
        """
file:?:?: Identifier 'x' referenced before definition.
    local x = x + x;
              ^
""",
    )
    for inst in ["tempvar a = 0", "ret", "ap += [ap]"]:
        verify_exception(
            f"""
func main() {{
    {inst};
    alloc_locals;
}}
""",
            """
file:?:?: alloc_locals must be used before any instruction that changes the ap register.
    alloc_locals;
    ^***********^
""",
        )
    verify_exception(
        """
alloc_locals;
""",
        """
file:?:?: alloc_locals cannot be used outside of a function.
alloc_locals;
^***********^
""",
    )


def test_local_variable_type_failures():
    verify_exception(
        """
struct T {
    a: felt,
}

func main() {
    alloc_locals;
    local x: T* = [ap];
    ret;
}
""",
        """
file:?:?: Cannot cast 'felt' to 'test_scope.T*'.
    local x: T* = [ap];
                  ^**^
""",
        exc_type=CairoTypeError,
    )


def test_local_variable_modifier_failures():
    verify_exception(
        """
func main() {
    local local x;
}
""",
        """
file:?:?: Unexpected modifier 'local'.
    local local x;
          ^***^
""",
    )
