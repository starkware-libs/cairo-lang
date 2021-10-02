from starkware.cairo.lang.compiler.identifier_definition import FunctionDefinition
from starkware.cairo.lang.compiler.preprocessor.preprocessor_test_utils import (
    strip_comments_and_linebreaks,
)
from starkware.starknet.compiler.starknet_preprocessor import WRAPPER_SCOPE
from starkware.starknet.compiler.test_utils import preprocess_str, verify_exception
from starkware.starknet.services.api.contract_definition import SUPPORTED_BUILTINS


def test_missing_lang_directive():
    verify_exception(
        """
@external
func f{}():
    return()
end
""",
        """
file:?:?: External decorators can only be used in source files that contain the \
"%lang starknet" directive.
@external
^*******^
""",
    )


def test_builtin_directive_after_external():
    verify_exception(
        """
%lang starknet
@external
func f{}():
    return()
end
%builtins pedersen range_check ecdsa
""",
        """
file:?:?: Directives must appear at the top of the file.
%builtins pedersen range_check ecdsa
^**********************************^
""",
    )


def test_storage_in_builtin_directive():
    verify_exception(
        """
%builtins storage
""",
        f"""
file:?:?: ['storage'] is not a subsequence of {SUPPORTED_BUILTINS}.
%builtins storage
^***************^
""",
    )


def test_output_in_builtin_directive():
    verify_exception(
        """
%builtins output range_check
""",
        f"""
file:?:?: ['output', 'range_check'] is not a subsequence of {SUPPORTED_BUILTINS}.
%builtins output range_check
^**************************^
""",
    )


def test_lang_directive():
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


def test_bad_implicit_arg_name():
    verify_exception(
        """
%lang starknet
%builtins pedersen range_check ecdsa
@external
func f{hello}():
    return()
end
""",
        """
file:?:?: Unexpected implicit argument 'hello' in an external function.
func f{hello}():
       ^***^
""",
    )


def test_wrapper_with_implicit_args():
    program = preprocess_str(
        """
%lang starknet
%builtins pedersen range_check ecdsa

struct HashBuiltin:
end

@external
func f{ecdsa_ptr, pedersen_ptr : HashBuiltin*}(a : felt, b : felt):
    return ()
end
"""
    )

    assert isinstance(program.identifiers.get_by_full_name(WRAPPER_SCOPE + "f"), FunctionDefinition)

    expected_result = "%builtins pedersen range_check ecdsa\n" + strip_comments_and_linebreaks(
        """\
# Implementation of f
[ap] = [fp + (-6)]; ap++                 # Return ecdsa_ptr.
[ap] = [fp + (-5)]; ap++                 # Return pedersen_ptr.
ret

# Implementation of __wrappers__.f
[ap] = [fp + (-3)] + 2; ap++             # Compute effective calldata end.
[fp + (-4)] = [ap + (-1)] - [fp + (-3)]  # Verify calldata size (2).
[ap] = [[fp + (-5)] + 4]; ap++           # Pass ecdsa_ptr.
[ap] = [[fp + (-5)] + 2]; ap++           # Pass pedersen_ptr.
[ap] = [[fp + (-3)]]; ap++               # Pass a.
[ap] = [[fp + (-3)] + 1]; ap++           # Pass b.
call rel -10                             # Call f.
%{ memory[ap] = segments.add() %}        # Allocate memory for return value
ap += 1
[ap] = [[fp + (-5)]]; ap++               # Return syscall_ptr
[ap] = [[fp + (-5)] + 1]; ap++           # Return storage_ptr
[ap] = [ap + (-4)]; ap++                 # Return pedersen_ptr.
[ap] = [[fp + (-5)] + 3]; ap++           # Return range_check.
[ap] = [ap + (-7)]; ap++                 # Return ecdsa.
[ap] = 0; ap++                           # Return retdata_size=0
[ap] = [ap + (-7)]; ap++                 # Return retdata_ptr
ret
"""
    )
    assert program.format() == expected_result


def test_wrapper_with_return_args():
    program = preprocess_str(
        """
%lang starknet
%builtins pedersen range_check ecdsa

struct Point:
    member x : felt
    member y : felt
end

struct HashBuiltin:
end

@external
func f{ecdsa_ptr}(a : felt, b : felt) -> (c : felt, d : Point):
    return (c=1, d=Point(2, 3))
end
"""
    )

    assert isinstance(program.identifiers.get_by_full_name(WRAPPER_SCOPE + "f"), FunctionDefinition)

    expected_result = "%builtins pedersen range_check ecdsa\n" + strip_comments_and_linebreaks(
        """\
# Implementation of f
[ap] = [fp + (-5)]; ap++                 # Return ecdsa_ptr.
[ap] = 1; ap++                           # Return c=1
[ap] = 2; ap++                           # Return d.x=2
[ap] = 3; ap++                           # Return d.y=3
ret

# Implementation of __wrappers__.f
[ap] = [fp + (-3)] + 2; ap++             # Compute effective calldata end.
[fp + (-4)] = [ap + (-1)] - [fp + (-3)]  # Verify calldata size (2).
[ap] = [[fp + (-5)] + 4]; ap++           # Pass ecdsa_ptr.
[ap] = [[fp + (-3)]]; ap++               # Pass a.
[ap] = [[fp + (-3)] + 1]; ap++           # Pass b.
call rel -14                             # Call f.
%{ memory[ap] = segments.add() %}        # Allocate memory for return value
ap += 1
[[ap + (-1)]] = [ap + (-4)]              # [retdata_ptr] = c
[[ap + (-1)] + 1] = [ap + (-3)]          # [retdata_ptr + 1] = d.x
[[ap + (-1)] + 2] = [ap + (-2)]          # [retdata_ptr + 2] = d.y
[ap] = [[fp + (-5)]]; ap++               # Return syscall_ptr
[ap] = [[fp + (-5)] + 1]; ap++           # Return storage_ptr
[ap] = [[fp + (-5)] + 2]; ap++           # Return pedersen_ptr.
[ap] = [[fp + (-5)] + 3]; ap++           # Return range_check.
[ap] = [ap + (-9)]; ap++                 # Return ecdsa.
[ap] = 3; ap++                           # Return retdata_size=3
[ap] = [ap + (-7)]; ap++                 # Return retdata_ptr
ret
"""
    )
    assert program.format() == expected_result


def test_wrapper_without_implicit_args():
    program = preprocess_str(
        """
%lang starknet
%builtins ecdsa

@external
func f():
    return ()
end
"""
    )

    assert isinstance(program.identifiers.get_by_full_name(WRAPPER_SCOPE + "f"), FunctionDefinition)

    expected_result = "%builtins ecdsa\n\n" + strip_comments_and_linebreaks(
        """\
ret
[fp + (-4)] = [fp + (-3)] - [fp + (-3)]  # Verify calldata size (0).
call rel -2                              # Call f.
%{ memory[ap] = segments.add() %}        # Allocate memory for return value
ap += 1
[ap] = [[fp + (-5)]]; ap++               # Return syscall_ptr
[ap] = [[fp + (-5)] + 1]; ap++           # Return storage_ptr.
[ap] = [[fp + (-5)] + 2]; ap++           # Return ecdsa.
[ap] = 0; ap++                           # Return retdata_size=0
[ap] = [ap + (-5)]; ap++                 # Return retdata_ptr
ret
"""
    )
    assert program.format() == expected_result


def test_valid_l1_handler():
    program = preprocess_str(
        """
%lang starknet
%builtins ecdsa

@l1_handler
func f(from_address : felt):
    return ()
end
"""
    )

    assert isinstance(program.identifiers.get_by_full_name(WRAPPER_SCOPE + "f"), FunctionDefinition)

    expected_result = "%builtins ecdsa\n\n" + strip_comments_and_linebreaks(
        """\
ret
[ap] = [fp + (-3)] + 1; ap++             # Compute effective calldata end.
[fp + (-4)] = [ap + (-1)] - [fp + (-3)]  # Verify calldata size (1).
[ap] = [[fp + (-3)]]; ap++               # Pass from_address.
call rel -5                              # Call f.
%{ memory[ap] = segments.add() %}        # Allocate memory for return value
ap += 1
[ap] = [[fp + (-5)]]; ap++               # Return syscall_ptr
[ap] = [[fp + (-5)] + 1]; ap++           # Return storage_ptr.
[ap] = [[fp + (-5)] + 2]; ap++           # Return ecdsa.
[ap] = 0; ap++                           # Return retdata_size=0
[ap] = [ap + (-5)]; ap++                 # Return retdata_ptr
ret
"""
    )
    assert program.format() == expected_result


def test_l1_handler_failures():
    verify_exception(
        """
%lang starknet

@l1_handler
func f():
    return ()
end
""",
        """
file:?:?: The first argument of an L1 handler must be named 'from_address'.
func f():
     ^
""",
    )

    verify_exception(
        """
%lang starknet

@l1_handler
func f(abc):
    return ()
end
""",
        """
file:?:?: The first argument of an L1 handler must be named 'from_address'.
func f(abc):
       ^*^
""",
    )

    verify_exception(
        """
%lang starknet

@l1_handler
func f(from_address: felt*):
    return ()
end
""",
        """
file:?:?: The type of 'from_address' must be felt.
func f(from_address: felt*):
                     ^***^
""",
    )

    verify_exception(
        """
%lang starknet

@l1_handler
func f(from_address) -> (ret_val):
    return (ret_val=0)
end
""",
        """
file:?:?: An L1 handler can not have a return value.
func f(from_address) -> (ret_val):
                         ^*****^
""",
    )


def test_bad_implicit_arg_type():
    verify_exception(
        """
%lang starknet
%builtins pedersen

struct HashBuiltin:
end

@external
func f{pedersen_ptr : HashBuiltin}():
    return ()
end
""",
        """
file:?:?: While expanding the reference 'pedersen_ptr' in:
func f{pedersen_ptr : HashBuiltin}():
     ^
file:?:?: Expected a 'felt' or a pointer type. Got: 'test_scope.HashBuiltin'.
func f{pedersen_ptr : HashBuiltin}():
       ^**********^
""",
    )


def test_unsupported_args():
    verify_exception(
        """
%lang starknet
@external
func fc(arg : felt**):
    return ()
end
""",
        """
file:?:?: Unsupported argument type felt**.
func fc(arg : felt**):
              ^****^
""",
    )


def test_unsupported_return_type():
    verify_exception(
        """
%lang starknet
@external
func fc() -> (arg : felt**):
    return (cast(0, felt**))
end
""",
        """
file:?:?: Unsupported return value type felt**.
func fc() -> (arg : felt**):
                    ^****^
""",
    )


def test_invalid_hint():
    verify_exception(
        """
%lang starknet
@external
func fc():
    %{ __storage.commitment_update() %}
    return ()
end
""",
        """
file:?:?: Hint is not whitelisted.
This may indicate that this library function cannot be used in StarkNet contracts.
    %{ __storage.commitment_update() %}
    ^*********************************^
""",
    )


def test_abi_basic():
    program = preprocess_str(
        """
%lang starknet
%builtins range_check

namespace MyNamespace:
    struct ExternalStruct:
        member y: (felt, felt)
    end
end

struct ExternalStruct2:
    member x: (felt, MyNamespace.ExternalStruct)
end

struct NonExternalStruct:
end

struct ExternalStruct3:
    member x: felt
end

@external
func f(a : felt, arr_len : felt, arr : felt*) -> (b : felt, c : felt):
    return (0, 1)
end

@view
func g() -> (a: ExternalStruct3):
    return (ExternalStruct3(0))
end

@l1_handler
func handler(from_address, a: ExternalStruct2):
    return ()
end
"""
    )

    assert program.abi == [
        {
            "type": "struct",
            "name": "ExternalStruct3",
            "members": [{"name": "x", "offset": 0, "type": "felt"}],
            "size": 1,
        },
        {
            "type": "struct",
            "name": "ExternalStruct2",
            "members": [{"name": "x", "offset": 0, "type": "(felt, ExternalStruct)"}],
            "size": 3,
        },
        {
            "type": "struct",
            "name": "ExternalStruct",
            "members": [{"name": "y", "offset": 0, "type": "(felt, felt)"}],
            "size": 2,
        },
        {
            "inputs": [
                {"name": "a", "type": "felt"},
                {"name": "arr_len", "type": "felt"},
                {"name": "arr", "type": "felt*"},
            ],
            "name": "f",
            "outputs": [
                {"name": "b", "type": "felt"},
                {"name": "c", "type": "felt"},
            ],
            "type": "function",
        },
        {
            "inputs": [],
            "name": "g",
            "outputs": [
                {"name": "a", "type": "ExternalStruct3"},
            ],
            "type": "function",
            "stateMutability": "view",
        },
        {
            "inputs": [
                {"name": "from_address", "type": "felt"},
                {"name": "a", "type": "ExternalStruct2"},
            ],
            "name": "handler",
            "outputs": [],
            "type": "l1_handler",
        },
    ]


def test_abi_failures():
    verify_exception(
        """
%lang starknet

namespace a:
    struct MyStruct:
    end
end

namespace b:
    struct MyStruct:
    end

    struct MyStruct2:
        member x: ((MyStruct, MyStruct), felt)
    end
end

@external
func f(x : (felt, a.MyStruct)):
    return()
end

@view
func g(y : b.MyStruct2):
    return()
end
""",
        """
file:?:?: Found two external structs named MyStruct: test_scope.a.MyStruct, test_scope.b.MyStruct.
    struct MyStruct:
           ^******^
""",
    )
