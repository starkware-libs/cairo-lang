import re
from typing import Dict, Optional, Type

import pytest

from starkware.cairo.lang.compiler.preprocessor.preprocessor import Preprocessor, preprocess_codes
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.test_utils import read_file_from_dict

PRIME = 3 * 2**30 + 1


def verify_exception(
        code: str, error: str, files: Dict[str, str] = {}, main_scope: ScopedName = ScopedName(),
        exc_type=PreprocessorError, preprocessor_cls: Optional[Type[Preprocessor]] = None):
    """
    Verifies that compiling the code results in the given error.
    """
    with pytest.raises(exc_type) as e:
        preprocess_codes(
            [(code, '')], prime=PRIME, read_module=read_file_from_dict(files),
            main_scope=main_scope, preprocessor_cls=preprocessor_cls)
    # Remove line and column information from the error using a regular expression.
    assert re.sub(':[0-9]+:[0-9]+: ', 'file:?:?: ', str(e.value)) == error.strip()
