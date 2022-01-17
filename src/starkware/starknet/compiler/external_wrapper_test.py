import pytest

from starkware.cairo.lang.compiler.identifier_definition import FunctionDefinition
from starkware.cairo.lang.compiler.preprocessor.preprocessor_test_utils import (
    strip_comments_and_linebreaks,
)
from starkware.starknet.compiler.starknet_preprocessor import WRAPPER_SCOPE
from starkware.starknet.compiler.test_utils import preprocess_str, verify_exception


def test_missing_range_check_in_builtin_directive():
    verify_exception(
        """
%lang starknet
%builtins pedersen
@external
func foo() -> (res):
end
""",
        f"""
file:?:?: In order to use external functions, the '%builtins' directive must include the \
'range_check' builtin.
func foo() -> (res):
     ^*^
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


@pytest.mark.parametrize("builtins_directive", [False, True])
def test_wrapper_with_implicit_args(builtins_directive: bool):
    program = preprocess_str(
        f"""
%lang starknet
{"%builtins pedersen range_check ecdsa" if builtins_directive else ""}

struct HashBuiltin:
end

@external
func f{{ecdsa_ptr, pedersen_ptr : HashBuiltin*}}(a : felt, b : felt):
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
[ap] = [[fp + (-5)] + 3]; ap++           # Pass ecdsa_ptr.
[ap] = [[fp + (-5)] + 1]; ap++           # Pass pedersen_ptr.
[ap] = [[fp + (-3)]]; ap++               # Pass a.
[ap] = [[fp + (-3)] + 1]; ap++           # Pass b.
call rel -10                             # Call f.
%{ memory[ap] = segments.add() %}        # Allocate memory for return value.
ap += 1
[ap] = [[fp + (-5)]]; ap++               # Return syscall_ptr.
[ap] = [ap + (-3)]; ap++                 # Return pedersen_ptr.
[ap] = [[fp + (-5)] + 2]; ap++           # Return range_check.
[ap] = [ap + (-6)]; ap++                 # Return ecdsa.
[ap] = 0; ap++                           # Return retdata_size=0.
[ap] = [ap + (-6)]; ap++                 # Return retdata_ptr.
ret
"""
    )
    assert program.format() == expected_result


@pytest.mark.parametrize("builtins_directive", [False, True])
def test_wrapper_with_return_values(builtins_directive: bool):
    """
    Tests that the external wrapper works with return values.
    In addition, also tests that the builtins are collected correctly and reordered according to
    SUPPORTED_BUILTINS.
    """
    program = preprocess_str(
        f"""
%lang starknet
{"%builtins pedersen range_check ecdsa" if builtins_directive else ""}

struct Point:
    member x : felt
    member y : felt
end

struct EcdsaBuiltin:
end

struct HashBuiltin:
end

@external
func f{{ecdsa_ptr : EcdsaBuiltin*}}(a : felt, b : felt) -> (c_len : felt, c : felt*, d : Point):
    return (c_len=1, c=cast(0, felt*), d=Point(2, 3))
end

@view
func g{{pedersen_ptr : HashBuiltin*}}():
    return ()
end
"""
    )

    assert isinstance(program.identifiers.get_by_full_name(WRAPPER_SCOPE + "f"), FunctionDefinition)

    expected_result = "%builtins pedersen range_check ecdsa\n" + strip_comments_and_linebreaks(
        """\
# A dummy memcpy().
ap += [ap]
ret

# Implementation of f.
[ap] = [fp + (-5)]; ap++                 # Return ecdsa_ptr.
[ap] = 1; ap++                           # Return c_len=1
[ap] = 0; ap++                           # Return c=0
[ap] = 2; ap++                           # Return d.x=2
[ap] = 3; ap++                           # Return d.y=3
ret

# Implementation of __wrappers__.f_encode_return.
%{ memory[ap] = segments.add() %}        # Allocate memory for return value.
ap += 3
[[fp]] = [fp + (-7)]                     # [retdata_ptr] = c_len
[[fp + (-3)]] = [fp + (-7)]              # Range check c_len.
[fp + 1] = [fp + (-3)] + 1               # Updated range_check_ptr.
[ap] = [fp] + 1; ap++                    # Updated __return_value_ptr.
[fp + 2] = [ap + (-1)] + [fp + (-7)]     # Updated __return_value_ptr.
[ap] = [fp] + 1; ap++                    # Pass old __return_value_ptr.
[ap] = [fp + (-6)]; ap++                 # Pass c.
[ap] = [fp + (-7)]; ap++                 # Pass c_len.
call rel -25                             # Call memcpy.
[[fp + 2]] = [fp + (-5)]                 # [retdata_ptr + 1] = d.x.
[[fp + 2] + 1] = [fp + (-4)]             # [retdata_ptr + 2] = d.y.
[ap] = [fp + 2] + 2; ap++                # Updated __return_value_ptr.
[ap] = [fp + 1]; ap++                    # Return range_check.
[ap] = [ap + (-2)] - [fp]; ap++          # Return data_len.
[ap] = [fp]; ap++                        # Return data.
ret

# Implementation of __wrappers__.f.
ap += 1
[ap] = [fp + (-3)] + 2; ap++             # Compute effective calldata end.
[fp + (-4)] = [ap + (-1)] - [fp + (-3)]  # Verify calldata size (2).
[ap] = [[fp + (-5)] + 3]; ap++           # Pass ecdsa_ptr.
[ap] = [[fp + (-3)]]; ap++               # Pass a.
[ap] = [[fp + (-3)] + 1]; ap++           # Pass b.
call rel -41                             # Call f.
[fp] = [ap + (-5)]                       # Copy ecdsa_ptr to a local variable.
[ap] = [[fp + (-5)] + 2]; ap++           # Pass range_check_ptr.
call rel -35                             # Call f_encode_return.
[ap] = [[fp + (-5)]]; ap++               # Return syscall_ptr.
[ap] = [[fp + (-5)] + 1]; ap++           # Return pedersen_ptr.
[ap] = [ap + (-5)]; ap++                 # Return range_check_ptr.
[ap] = [fp]; ap++                        # Return ecdsa_ptr.
[ap] = [ap + (-6)]; ap++                 # Return retdata_size.
[ap] = [ap + (-6)]; ap++                 # Return retdata_ptr (__return_value_ptr_start).
ret

# Implementation of g.
[ap] = [fp + (-3)]; ap++                 # Return pedersen_ptr.
ret

# Implementation of __wrappers__.g.
[fp + (-4)] = [fp + (-3)] - [fp + (-3)]  # Verify calldata size (0).
[ap] = [[fp + (-5)] + 1]; ap++           # Pass pedersen_ptr.
call rel -4                              # Call g.
%{ memory[ap] = segments.add() %}        # Allocate memory for return value.
ap += 1
[ap] = [[fp + (-5)]]; ap++               # Return syscall_ptr.
[ap] = [ap + (-3)]; ap++                 # Return pedersen_ptr.
[ap] = [[fp + (-5)] + 2]; ap++           # Return range_check_ptr
[ap] = [[fp + (-5)] + 3]; ap++           # Return ecdsa_ptr.
[ap] = 0; ap++                           # Return retdata_size.
[ap] = [ap + (-6)]; ap++                 # Return retdata_ptr.
ret
"""
    )
    assert program.format() == expected_result


def test_fallback_wrapper():
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
%{ memory[ap] = segments.add() %}        # Allocate memory for return value.
ap += 1
[ap] = [[fp + (-5)]]; ap++               # Return syscall_ptr.
[ap] = [[fp + (-5)] + 1]; ap++           # Return ecdsa.
[ap] = 0; ap++                           # Return retdata_size=0.
[ap] = [ap + (-4)]; ap++                 # Return retdata_ptr.
ret
"""
    )
    assert program.format() == expected_result


def test_valid_default_entry_point():
    program = preprocess_str(
        """
%lang starknet
%builtins pedersen range_check

@external
@raw_input
@raw_output
func __default__{syscall_ptr, range_check_ptr}(
        selector : felt, calldata_size : felt, calldata : felt*) -> (
        retdata_size : felt, retdata : felt*):
    return (retdata_size=1, retdata=cast([fp], felt*))
end
"""
    )

    assert isinstance(
        program.identifiers.get_by_full_name(WRAPPER_SCOPE + "__default__"), FunctionDefinition
    )

    expected_result = "%builtins pedersen range_check\n\n" + strip_comments_and_linebreaks(
        """\
[ap] = [fp + (-7)]; ap++   # Return syscall_ptr.
[ap] = [fp + (-6)]; ap++   # Return range_check_ptr.
[ap] = 1; ap++             # Return retdata_len=1.
[ap] = [fp]; ap++          # Return retdata = [fp].
ret
# Implementation of __wrappers__.__default__
[ap] = [[fp + (-5)]]; ap++               # Push syscall_ptr.
[ap] = [[fp + (-5)] + 2]; ap++           # Push range_check_ptr.
[ap] = [fp + (-6)]; ap++                 # Push selector.
[ap] = [fp + (-4)]; ap++                 # Push calldata_size.
[ap] = [fp + (-3)]; ap++                 # Push calldata.
# Call __default__
call rel -11
[ap] = [ap + (-4)]; ap++                # Return syscall_ptr.
[ap] = [[fp + (-5)] + 1]; ap++          # Return pedersen_ptr.
[ap] = [ap + (-5)]; ap++                # Return range_check_ptr.
[ap] = [ap + (-5)]; ap++                # Return retdata_size.
[ap] = [ap + (-5)]; ap++                # Return retdata.
ret
"""
    )
    assert program.format() == expected_result


def test_valid_l1_default_entry_point():
    program = preprocess_str(
        """
%lang starknet
%builtins range_check

@l1_handler
@raw_input
func __l1_default__{syscall_ptr, range_check_ptr}(
        selector : felt, calldata_size : felt, calldata : felt*):
    return ()
end
"""
    )

    assert isinstance(
        program.identifiers.get_by_full_name(WRAPPER_SCOPE + "__l1_default__"), FunctionDefinition
    )

    expected_result = "%builtins range_check\n\n" + strip_comments_and_linebreaks(
        """\
[ap] = [fp + (-7)]; ap++   # Return syscall_ptr.
[ap] = [fp + (-6)]; ap++   # Return range_check_ptr.
ret
# Implementation of __wrappers__.__default__
[ap] = [[fp + (-5)]]; ap++               # Push syscall_ptr.
[ap] = [[fp + (-5)] + 1]; ap++           # Push range_check_ptr.
[ap] = [fp + (-6)]; ap++                 # Push selector.
[ap] = [fp + (-4)]; ap++                 # Push calldata_size.
[ap] = [fp + (-3)]; ap++                 # Push calldata.
# Call __default__
call rel -8
%{ memory[ap] = segments.add() %}        # Allocate memory for return value.
ap += 1                                  #
[ap] = [ap + (-3)]; ap++                 # Return syscall_ptr.
[ap] = [ap + (-3)]; ap++                 # Return range_check_ptr.
[ap] = 0; ap++                           # Return retdata_size=0.
[ap] = [ap + (-4)]; ap++                 # Return retdata_ptr.
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
%{ memory[ap] = segments.add() %}        # Allocate memory for return value.
ap += 1
[ap] = [[fp + (-5)]]; ap++               # Return syscall_ptr.
[ap] = [[fp + (-5)] + 1]; ap++           # Return ecdsa.
[ap] = 0; ap++                           # Return retdata_size=0.
[ap] = [ap + (-4)]; ap++                 # Return retdata_ptr.
ret
"""
    )
    assert program.format() == expected_result


def test_raw_input_failures():
    verify_exception(
        """
%lang starknet

@external
@raw_input
func foo(bad_arg):
    return ()
end
""",
        """
file:?:?: @raw_input requires the following arguments:
(selector: felt, calldata_size: felt, calldata: felt*).
func foo(bad_arg):
         ^*****^
""",
    )


def test_raw_output_failures():
    verify_exception(
        """
%lang starknet

@external
@raw_output
func foo(selector : felt, calldata_size: felt, calldata: felt*):
    return ()
end
""",
        """
file:?:?: @raw_output requires the following return values:
(retdata_size: felt, retdata: felt*).
func foo(selector : felt, calldata_size: felt, calldata: felt*):
     ^*^
""",
    )

    verify_exception(
        """
%lang starknet

@external
@raw_output
func foo(selector : felt, calldata_size: felt, calldata: felt*) -> (bad_ret):
    return ()
end
""",
        """
file:?:?: @raw_output requires the following return values:
(retdata_size: felt, retdata: felt*).
func foo(selector : felt, calldata_size: felt, calldata: felt*) -> (bad_ret):
                                                                    ^*****^
""",
    )

    verify_exception(
        """
%lang starknet

@external
@l1_handler
func __default__():
    return ()
end
""",
        """
file:?:?: The __default__ entry point may only be decorated with '@external'.
@l1_handler
 ^********^

""",
    )

    verify_exception(
        """
%lang starknet

@external
@l1_handler
func __l1_default__():
    return ()
end
""",
        """
file:?:?: The __l1_default__ entry point may only be decorated with '@l1_handler'.
@external
 ^******^

""",
    )

    verify_exception(
        """
%lang starknet

func __default__():
    return ()
end
""",
        """
file:?:?: The __default__ entry point needs to be decorated with '@external'.
func __default__():
     ^*********^

""",
    )


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


def test_constructor_failures():
    verify_exception(
        """
%lang starknet

@constructor
func constructor():
    return ()
end

namespace abc:
    @constructor
    func constructor():
        return ()
    end
end
""",
        """
file:?:?: Multiple constructors definitions are not supported.
    func constructor():
         ^*********^
file:?:?: The constructor was previously defined here:
func constructor():
     ^*********^
""",
    )

    verify_exception(
        """
%lang starknet

@constructor
func badly_named_constructor(a : felt):
    return ()
end
""",
        """
file:?:?: The constructor name must be 'constructor'.
func badly_named_constructor(a : felt):
     ^*********************^
""",
    )

    verify_exception(
        """
%lang starknet

@constructor
func constructor() -> (a : felt):
    return (a=5)
end
""",
        """
file:?:?: A constructor can not have a return value.
func constructor() -> (a : felt):
                       ^******^
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
file:?:?: Only pointers to types that consist of felts are supported.
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
file:?:?: Only pointers to types that consist of felts are supported.
func fc() -> (arg : felt**):
                    ^****^
""",
    )
