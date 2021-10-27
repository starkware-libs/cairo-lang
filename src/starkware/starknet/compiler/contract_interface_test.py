from starkware.starknet.compiler.test_utils import preprocess_str, verify_exception
from starkware.starknet.public.abi import get_selector_from_name


def test_contract_interface_success():
    selector = get_selector_from_name("foo")
    usage_code = """
func main{syscall_ptr : felt*, range_check_ptr}():
    let (y0, y1) = Contract.foo(contract_address=0, x0=0, x1=0, arr_len=0, arr=cast(0, felt*))
    return()
end
"""

    code = f"""
%lang starknet

{usage_code}

@contract_interface
namespace Contract:
    func foo(x0 : felt, x1 : felt, arr_len : felt, arr : felt*) -> (y0 : felt, y1 : felt):
    end
end
"""

    expected_code = f"""
%lang starknet

# Dummy library functions.

func alloc() -> (result):
    ret
end

func memcpy(dst : felt*, src : felt*, len):
    ap += [ap]
    ret
end

func call_contract{{syscall_ptr : felt*}}(
        contract_address : felt, function_selector : felt, calldata_size : felt,
        calldata : felt*) -> (retdata_size : felt, retdata : felt*):
    ret
end

{usage_code}

namespace Contract:
    func foo{{syscall_ptr : felt*, range_check_ptr}}(
            contract_address : felt, x0 : felt, x1 : felt,
            arr_len : felt, arr : felt*) -> (y0 : felt, y1 : felt):
        alloc_locals
        let (local __calldata_ptr_start : felt*) = alloc()
        let __calldata_ptr = __calldata_ptr_start
        assert [__calldata_ptr] = x0
        let __calldata_ptr = __calldata_ptr + 1
        assert [__calldata_ptr] = x1
        let __calldata_ptr = __calldata_ptr + 1
        assert [__calldata_ptr] = arr_len
        let __calldata_ptr = __calldata_ptr + 1

        # Check that the length is non-negative.
        assert [range_check_ptr] = arr_len
        # Store the updated range_check_ptr as a local variable to keep it available after
        # the memcpy.
        local range_check_ptr = range_check_ptr + 1
        # Keep a reference to __calldata_ptr.
        let __calldata_ptr_copy = __calldata_ptr
        # Store the updated __calldata_ptr as a local variable to keep it available after
        # the memcpy.
        local __calldata_ptr : felt* = __calldata_ptr + arr_len
        memcpy(dst=__calldata_ptr_copy, src=arr, len=arr_len)

        let (retdata_size, retdata) = call_contract(
            contract_address=contract_address,
            function_selector={selector},
            calldata_size=__calldata_ptr - __calldata_ptr_start,
            calldata=__calldata_ptr_start)
        let __return_value_ptr = retdata
        let y0 = [__return_value_ptr]
        let __return_value_ptr = __return_value_ptr + 1
        let y1 = [__return_value_ptr]
        let __return_value_ptr = __return_value_ptr + 1
        let __return_value_actual_size = __return_value_ptr - cast(retdata, felt*)
        assert retdata_size = __return_value_actual_size
        return (y0, y1)
    end
end
"""
    program = preprocess_str(code)
    expected_program = preprocess_str(expected_code)

    assert program.format() == expected_program.format()


def test_contract_interface_failures():
    verify_exception(
        """
@contract_interface
namespace Contract:
end
""",
        """
file:?:?: @contract_interface can only be used in source files that contain the \
"%lang starknet" directive.
@contract_interface
 ^****************^
""",
    )
    verify_exception(
        """
%lang starknet
@contract_interface
@another_decorator
func f():
end
""",
        """
file:?:?: @contract_interface can only be used with namespaces.
func f():
     ^
""",
    )
    verify_exception(
        """
%lang starknet
@contract_interface
@another_decorator
namespace f:
end
""",
        """
file:?:?: Unexpected decorator for a contract interface.
@another_decorator
 ^***************^
""",
    )
    verify_exception(
        """
%lang starknet
@contract_interface
namespace f:
    const X = 0
end
""",
        """
file:?:?: Only functions are supported within a contract interface.
    const X = 0
    ^*********^
""",
    )


def test_contract_interface_function_failures():
    template = """
%lang starknet
@contract_interface
namespace f:
{}
end
"""
    verify_exception(
        template.format(
            """
@decorator
func foo():
end
"""
        ),
        """
file:?:?: Unexpected decorator for a contract interface function.
@decorator
 ^*******^
""",
    )
    verify_exception(
        template.format(
            """
func foo():
    # Empty line.
    const X = 0
end
"""
        ),
        """
file:?:?: Contract interface functions must have an empty body.
    const X = 0
    ^*********^
""",
    )
    verify_exception(
        template.format(
            """
func foo{x}():
end
"""
        ),
        """
file:?:?: Contract interface functions must have no implicit arguments.
func foo{x}():
         ^
""",
    )
    verify_exception(
        template.format(
            """
func foo(arr : felt*):
end
"""
        ),
        """
file:?:?: Array argument "arr" must be preceded by a length argument named "arr_len" of type felt.
func foo(arr : felt*):
         ^*^
""",
    )


def test_missing_range_check_ptr():
    autogen_file = (
        "autogen/starknet/contract_interface/Contract/foo/"
        "172b67737f06d64900ecbb9f0d7d90d8c82e23b9d4d9fbb104eb7bfafeebed25.cairo"
    )

    verify_exception(
        """\
%lang starknet

@contract_interface
namespace Contract:
    func foo():
    end
end

func test{syscall_ptr : felt*}():
    Contract.foo(contract_address=0)
    return()
end
""",
        """
file:?:?: While trying to retrieve the implicit argument 'range_check_ptr' in:
    Contract.foo(contract_address=0)
    ^******************************^
file:?:?: While handling contract interface function:
    func foo():
         ^*^
file:?:?: Unknown identifier 'range_check_ptr'.
func foo{syscall_ptr : felt*, range_check_ptr}(
                              ^*************^
""",
    )
