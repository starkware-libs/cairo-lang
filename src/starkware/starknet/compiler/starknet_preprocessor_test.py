from starkware.cairo.lang.compiler.identifier_definition import FunctionDefinition
from starkware.starknet.compiler.starknet_preprocessor import WRAPPER_SCOPE
from starkware.starknet.compiler.test_utils import preprocess_str, verify_exception


def test_builtin_directive_after_external():
    verify_exception("""
@external
func f{}():
    return()
end
%builtins pedersen range_check ecdsa
""", """
file:?:?: Directives must appear at the top of the file.
%builtins pedersen range_check ecdsa
^**********************************^
""")


def test_storage_in_builtin_directive():
    verify_exception("""
%builtins storage
""", """
file:?:?: 'storage' may not appear in the builtins directive.
%builtins storage
^***************^
""")


def test_lang_directive():
    verify_exception("""
%lang abc
""", """
file:?:?: Unsupported %lang directive. Are you using the correct compiler?
%lang abc
^*******^
""")


def test_bad_implicit_arg_name():
    verify_exception("""
%builtins pedersen range_check ecdsa
@external
func f{hello}():
    return()
end
""", """
file:?:?: Unexpected implicit argument 'hello' in an external function.
func f{hello}():
       ^***^
""")


def test_wrapper_with_implicit_args():
    program = preprocess_str("""
%builtins pedersen range_check ecdsa

struct HashBuiltin:
end

@external
func f{ecdsa_ptr, pedersen_ptr : HashBuiltin*}(a : felt, b : felt):
    return ()
end
""")

    assert isinstance(program.identifiers.get_by_full_name(
        WRAPPER_SCOPE + 'f'), FunctionDefinition)

    assert program.format() == """\
%builtins pedersen range_check ecdsa

[ap] = [fp + (-6)]; ap++
[ap] = [fp + (-5)]; ap++
ret
[ap] = [[fp + (-4)] + 3]; ap++
[ap] = [[fp + (-4)] + 1]; ap++
[ap] = [[fp + (-3)]]; ap++
[ap] = [[fp + (-3)] + 1]; ap++
call rel -7
%{ memory[ap] = segments.add() %}
ap += 1
[ap] = [[fp + (-4)]]; ap++
[ap] = [ap + (-3)]; ap++
[ap] = [[fp + (-4)] + 2]; ap++
[ap] = [ap + (-6)]; ap++
[ap] = 0; ap++
[ap] = [ap + (-6)]; ap++
ret
"""


def test_wrapper_with_return_args():
    program = preprocess_str("""
%builtins pedersen range_check ecdsa

struct HashBuiltin:
end

@external
func f{ecdsa_ptr}(a : felt, b : felt) -> (c : felt, d : felt):
    return (c=1, d=2)
end
""")

    assert isinstance(program.identifiers.get_by_full_name(
        WRAPPER_SCOPE + 'f'), FunctionDefinition)

    assert program.format() == """\
%builtins pedersen range_check ecdsa

[ap] = [fp + (-5)]; ap++
[ap] = 1; ap++
[ap] = 2; ap++
ret
[ap] = [[fp + (-4)] + 3]; ap++
[ap] = [[fp + (-3)]]; ap++
[ap] = [[fp + (-3)] + 1]; ap++
call rel -9
%{ memory[ap] = segments.add() %}
ap += 1
[[ap + (-1)]] = [ap + (-3)]
[[ap + (-1)] + 1] = [ap + (-2)]
[ap] = [[fp + (-4)]]; ap++
[ap] = [[fp + (-4)] + 1]; ap++
[ap] = [[fp + (-4)] + 2]; ap++
[ap] = [ap + (-7)]; ap++
[ap] = 2; ap++
[ap] = [ap + (-6)]; ap++
ret
"""


def test_wrapper_without_implicit_args():
    program = preprocess_str("""
%builtins ecdsa
@external
func f():
    return ()
end
""")

    assert isinstance(program.identifiers.get_by_full_name(
        WRAPPER_SCOPE + 'f'), FunctionDefinition)

    assert program.format() == """\
%builtins ecdsa

ret
call rel -1
%{ memory[ap] = segments.add() %}
ap += 1
[ap] = [[fp + (-4)]]; ap++
[ap] = [[fp + (-4)] + 1]; ap++
[ap] = 0; ap++
[ap] = [ap + (-4)]; ap++
ret
"""


def test_bad_implicit_arg_type():
    verify_exception("""
%builtins pedersen

struct HashBuiltin:
end

@external
func f{pedersen_ptr : HashBuiltin}():
    return ()
end
""", """
file:?:?: While expanding the reference 'pedersen_ptr' in:
func f{pedersen_ptr : HashBuiltin}():
     ^
file:?:?: Expected a 'felt' or a pointer type. Got: 'test_scope.HashBuiltin'.
func f{pedersen_ptr : HashBuiltin}():
       ^**********^
""")


def test_unsupported_args():
    verify_exception("""
@external
func fc(arg : felt*):
    return ()
end
""", """
file:?:?: Unsupported argument type felt*.
func fc(arg : felt*):
              ^***^
""")


def test_invalid_hint():
    verify_exception("""
@external
func fc():
    %{ __storage.merkle_update() %}
    return ()
end
""", """
file:?:?: Hint is not whitelisted.
This may indicate that this library function cannot be used in StarkNet contracts.
    %{ __storage.merkle_update() %}
    ^*****************************^
""")


def test_abi():
    program = preprocess_str("""
@external
func f(a: felt) -> (b: felt, c: felt):
    return (0, 1)
end

@view
func g() -> (a: felt):
    return (0)
end
""")

    assert program.abi == [
        {
            'inputs': [
                {'name': 'a', 'type': 'felt'}
            ],
            'name': 'f',
            'outputs': [
                {'name': 'b', 'type': 'felt'},
                {'name': 'c', 'type': 'felt'}
            ],
            'type': 'function',
        },
        {
            'inputs': [],
            'name': 'g',
            'outputs': [
                {'name': 'a', 'type': 'felt'},
            ],
            'type': 'function',
            'stateMutability': 'view',
        },
    ]
