from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.preprocessor.preprocessor_test_utils import preprocess_str_ex
from starkware.cairo.lang.compiler.preprocessor.preprocessor_test_utils import (
    verify_exception as generic_verify_exception)
from starkware.cairo.lang.compiler.test_utils import read_file_from_dict
from starkware.starknet.compiler.starknet_pass_manager import starknet_pass_manager
from starkware.starknet.compiler.starknet_preprocessor import StarknetPreprocessedProgram

TEST_MODULES = {
    'starkware.starknet.common.storage': """
struct Storage:
end

func storage_read{storage_ptr : Storage*}(address : felt) -> (value : felt):
    ret
end

func storage_write{storage_ptr : Storage*}(address : felt, value : felt):
    ret
end

func normalize_address{range_check_ptr}(addr : felt) -> (res : felt):
    ret
end
""",
    'starkware.cairo.common.cairo_builtins': """
struct HashBuiltin:
end
""",
    'starkware.cairo.common.hash': """
from starkware.cairo.common.cairo_builtins import HashBuiltin

func hash2{hash_ptr : HashBuiltin*}(x, y) -> (result):
    ret
end
"""}


def preprocess_str(code: str) -> StarknetPreprocessedProgram:
    preprocessed = preprocess_str_ex(
        code=code,
        pass_manager=starknet_pass_manager(
            prime=DEFAULT_PRIME, read_module=read_file_from_dict(TEST_MODULES)))
    assert isinstance(preprocessed, StarknetPreprocessedProgram)
    return preprocessed


def verify_exception(code: str, error: str, exc_type=PreprocessorError):
    return generic_verify_exception(
        code=code,
        error=error,
        pass_manager=starknet_pass_manager(
            prime=DEFAULT_PRIME, read_module=read_file_from_dict(TEST_MODULES)),
        exc_type=exc_type)
