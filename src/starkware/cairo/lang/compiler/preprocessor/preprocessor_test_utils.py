import re
from typing import Dict, Optional, Type

import pytest

from starkware.cairo.lang.compiler.preprocessor.preprocessor import (
    PreprocessedProgram, Preprocessor, preprocess_codes)
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.test_utils import read_file_from_dict

PRIME = 3 * 2**30 + 1

# Note that the TEST_SCOPE is hardcoded in the tests.
TEST_SCOPE = ScopedName.from_string('test_scope')


def default_read_module(module_name: str):
    raise Exception(
        f'Error: trying to read module {module_name}, no reading algorithm provided.')


def preprocess_str(
        code: str, prime: int, main_scope: Optional[ScopedName] = None) -> PreprocessedProgram:
    if main_scope is None:
        main_scope = TEST_SCOPE
    return preprocess_codes(
        [(code, '')], prime, read_module=default_read_module, main_scope=main_scope)


def verify_exception(
        code: str, error: str, files: Dict[str, str] = {}, main_scope: Optional[ScopedName] = None,
        exc_type=PreprocessorError, preprocessor_cls: Optional[Type[Preprocessor]] = None):
    """
    Verifies that compiling the code results in the given error.
    """
    if main_scope is None:
        main_scope = TEST_SCOPE

    with pytest.raises(exc_type) as e:
        preprocess_codes(
            [(code, '')], prime=PRIME, read_module=read_file_from_dict(files),
            main_scope=main_scope, preprocessor_cls=preprocessor_cls)
    # Remove line and column information from the error using a regular expression.
    assert re.sub(':[0-9]+:[0-9]+', 'file:?:?', str(e.value)) == error.strip()
