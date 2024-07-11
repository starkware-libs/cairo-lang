from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo
from starkware.starknet.cli.reconstruct_starknet_traceback import reconstruct_starknet_traceback


def test_reconstruct_traceback():
    code1 = """
func main() {
    assert 1 = 2;
    return ();
}
"""

    code2 = """
func main() {
    assert 2 = 3;
    return ();
}
"""

    traceback_txt = """
Transaction execution has failed:
Error in the called contract (contract address: 0x1234, class hash: 0x4444, selector: 0xDEAD):
Error at pc=0:0:
Error message 1
Error in the called contract (contract address: 0x5678, class hash: 0x5555, selector: 0xBEEF):
Error at pc=0:0:
Error message 2
"""

    program_with_debug_info1 = compile_cairo(
        code=[(code1, "filename")], prime=DEFAULT_PRIME, debug_info=True
    )
    program_with_debug_info2 = compile_cairo(
        code=[(code2, "filename")], prime=DEFAULT_PRIME, debug_info=True
    )

    # Fix both 0x1234 and 0x5678.
    res = reconstruct_starknet_traceback(
        contracts={0x1234: program_with_debug_info1, 0x5678: program_with_debug_info2},
        traceback_txt=traceback_txt,
    )
    expected_res = """
Transaction execution has failed:
Error in the called contract (contract address: 0x1234, class hash: 0x4444, selector: 0xDEAD):
filename:3:16: Error at pc=0:0:
    assert 1 = 2;
               ^
Error message 1
Error in the called contract (contract address: 0x5678, class hash: 0x5555, selector: 0xBEEF):
filename:3:16: Error at pc=0:0:
    assert 2 = 3;
               ^
Error message 2
"""
    assert res == expected_res

    # Fix only 0x1234.
    res = reconstruct_starknet_traceback(
        contracts={0x1234: program_with_debug_info1},
        traceback_txt=traceback_txt,
    )
    expected_res = """
Transaction execution has failed:
Error in the called contract (contract address: 0x1234, class hash: 0x4444, selector: 0xDEAD):
filename:3:16: Error at pc=0:0:
    assert 1 = 2;
               ^
Error message 1
Error in the called contract (contract address: 0x5678, class hash: 0x5555, selector: 0xBEEF):
Error at pc=0:0:
Error message 2
"""
    assert res == expected_res
