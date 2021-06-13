from starkware.cairo.lang.compiler.preprocessor.preprocessor_test_utils import (
    strip_comments_and_linebreaks)
from starkware.starknet.compiler.test_utils import preprocess_str, verify_exception
from starkware.starknet.public.abi import starknet_keccak


def test_storage_var_success():
    program = preprocess_str("""
%lang starknet
from starkware.starknet.core.storage.storage import Storage
from starkware.cairo.common.cairo_builtins import HashBuiltin

func g{storage_ptr : Storage*, pedersen_ptr : HashBuiltin*}():
    alloc_locals
    let (x) = my_var.read()
    my_var.write(value=x + 1)
    local storage_ptr : Storage* = storage_ptr
    let (my_var2_addr) = my_var2.addr(1, 2)
    my_var2.write(1, 2, 3)
    return ()
end

@storage_var
func my_var() -> (res : felt):
    # Comment.

end

@storage_var
func my_var2(x, y) -> (res : felt):
end
""")
    addr = starknet_keccak(b'my_var')
    addr2 = starknet_keccak(b'my_var2')
    expected_result = f"""\
# Code for the dummy modules.
ret
ret
ret

# Implementation of g.
ap += 1
[ap] = [fp + (-4)]; ap++       # Push storage_ptr.
[ap] = [fp + (-3)]; ap++       # Push pedersen_ptr.
call rel 30                    # Call my_var.read.
[ap] = [ap + (-3)]; ap++       # Push (updated) storage_ptr.
[ap] = [ap + (-3)]; ap++       # Push (updated) pedersen_ptr.
[ap] = [ap + (-3)] + 1; ap++   # Push value.
call rel 35                    # Call my_var.write.
[fp] = [ap + (-2)]             # Copy storage_ptr to a local variable.
[ap] = 1; ap++                 # Push 1.
[ap] = 2; ap++                 # Push 2.
call rel 38                    # Call my_var2.addr.
[ap] = [fp]; ap++              # Push storage_ptr.
[ap] = [ap + (-3)]; ap++       # Push pedersen_ptr.
[ap] = 1; ap++                 # Push 1.
[ap] = 2; ap++                 # Push 2.
[ap] = 3; ap++                 # Push 2.
call rel 38                    # Call my_var2.write.
ret

# Implementation of my_var.addr.
[ap] = [fp + (-3)]; ap++       # Return pedersen_ptr.
[ap] = {addr}; ap++            # Return address.
ret

# Implementation of my_var.read.
[ap] = [fp + (-3)]; ap++       # Pass pedersen_ptr.
call rel -5                    # Call my_var.addr().
[ap] = [fp + (-4)]; ap++       # Pass storage_ptr.
[ap] = [ap + (-2)]; ap++       # Pass address.
call rel -41                   # Call storage_read().
[ap] = [ap + (-2)]; ap++       # Return storage_ptr.
[ap] = [ap + (-7)]; ap++       # Return (updated) pedersen_ptr.
[ap] = [ap + (-3)]; ap++       # Return value.
ret

# Implementation of my_var.write.
[ap] = [fp + (-4)]; ap++       # Pass pedersen_ptr.
call rel -16                   # Call my_var.addr().
[ap] = [fp + (-5)]; ap++       # Pass storage_ptr.
[ap] = [ap + (-2)]; ap++       # Pass address.
[ap] = [fp + (-3)]; ap++       # Pass value.
call rel -52                   # Call storage_write().
[ap] = [ap + (-7)]; ap++       # Return (updated) pedersen_ptr.
ret

# Implementation of my_var2.addr.
[ap] = [fp + (-5)]; ap++       # Push pedersen_ptr.
[ap] = {addr2}; ap++           # Push address.
[ap] = [fp + (-4)]; ap++       # Push x.
call rel -62                   # Call hash2(res, x).
[ap] = [fp + (-3)]; ap++       # Push y.
call rel -65                   # Call hash2(res, y).
ret

# Implementation of my_var2.write.
[ap] = [fp + (-6)]; ap++       # Pass pedersen_ptr.
[ap] = [fp + (-5)]; ap++       # Pass x.
[ap] = [fp + (-4)]; ap++       # Pass y.
call rel -13                   # Call my_var.addr().
[ap] = [fp + (-7)]; ap++       # Pass storage_ptr.
[ap] = [ap + (-2)]; ap++       # Pass address.
[ap] = [fp + (-3)]; ap++       # Pass value.
call rel -74                   # Call storage_write().
[ap] = [ap + (-7)]; ap++       # Return (updated) pedersen_ptr.
ret
"""
    assert program.format() == strip_comments_and_linebreaks(expected_result).lstrip()


def test_storage_var_failures():
    verify_exception("""
@storage_var
func f() -> (res : felt):
end
""", """
file:?:?: @storage_var can only be used in source files that contain the "%lang starknet" directive.
@storage_var
^**********^
""")
    verify_exception("""
%lang starknet
@storage_var
func f():
    return ()  # Comment.
end
""", """
file:?:?: Storage variables must have an empty body.
    return ()  # Comment.
    ^*******^
""")
    verify_exception("""
%lang starknet
@storage_var
func f():
    0 = 1  # Comment.
end
""", """
file:?:?: Storage variables must have an empty body.
func f():
     ^
""")
    verify_exception("""
%lang starknet
@storage_var
func f{x, y}():
end
""", """
file:?:?: Storage variables must have no implicit arguments.
func f{x, y}():
       ^**^
""")
    verify_exception("""
%lang starknet
@storage_var
@invalid_decorator
func f():
end
""", """
file:?:?: Storage variables must have no decorators in addition to @storage_var.
@invalid_decorator
^****************^
""")
    verify_exception("""
%lang starknet
@storage_var
func f(x, y : felt*):
end
""", """
file:?:?: Only felt arguments are supported in storage variables.
func f(x, y : felt*):
              ^***^
""")
    verify_exception("""
%lang starknet
@storage_var
func f():
end
""", """
file:?:?: Storage variables must return a single value of type felt.
func f():
     ^
""")
    verify_exception("""
%lang starknet
@storage_var
func f() -> (x: felt, y: felt):
end
""", """
file:?:?: Storage variables must return a single value of type felt.
func f() -> (x: felt, y: felt):
             ^**************^
""")
