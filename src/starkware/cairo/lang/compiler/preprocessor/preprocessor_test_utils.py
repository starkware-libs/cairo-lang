import re
from typing import Dict, Optional, Type

import pytest

from starkware.cairo.lang.compiler.preprocessor.default_pass_manager import default_pass_manager
from starkware.cairo.lang.compiler.preprocessor.pass_manager import PassManager
from starkware.cairo.lang.compiler.preprocessor.preprocess_codes import preprocess_codes
from starkware.cairo.lang.compiler.preprocessor.preprocessor import (
    PreprocessedProgram,
    Preprocessor,
)
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.test_utils import read_file_from_dict

PRIME = 3 * 2 ** 30 + 1

# Note that the TEST_SCOPE is hardcoded in the tests.
TEST_SCOPE = ScopedName.from_string("test_scope")


CAIRO_TEST_MODULES = {
    "starkware.cairo.lang.compiler.lib.registers": """
@known_ap_change
func get_ap() -> (ap_val):
    ret
end
""",
}


def strip_comments_and_linebreaks(program: str):
    """
    Removes all comments and empty lines from the given program.
    """
    program = re.sub(r"\s*#.*\n", "\n", program)
    return re.sub("\n+", "\n", program).lstrip()


def default_read_module(module_name: str):
    raise Exception(f"Error: trying to read module {module_name}, no reading algorithm provided.")


def preprocess_str(
    code: str,
    prime: int,
    main_scope: Optional[ScopedName] = None,
    preprocessor_cls: Optional[Type[Preprocessor]] = None,
) -> PreprocessedProgram:
    return preprocess_str_ex(
        code=code,
        pass_manager=default_pass_manager(
            prime=prime,
            read_module=read_file_from_dict(CAIRO_TEST_MODULES),
            preprocessor_cls=preprocessor_cls,
        ),
        main_scope=main_scope,
    )


def preprocess_str_ex(
    code: str, pass_manager: PassManager, main_scope: Optional[ScopedName] = None
) -> PreprocessedProgram:
    if main_scope is None:
        main_scope = TEST_SCOPE
    return preprocess_codes([(code, "")], pass_manager=pass_manager, main_scope=main_scope)


def verify_exception(
    code: str,
    error: str,
    files: Dict[str, str] = {},
    main_scope: Optional[ScopedName] = None,
    exc_type=PreprocessorError,
    pass_manager: Optional[PassManager] = None,
):
    """
    Verifies that compiling the code results in the given error.
    """
    if main_scope is None:
        main_scope = TEST_SCOPE

    if pass_manager is None:
        pass_manager = default_pass_manager(
            prime=PRIME, read_module=read_file_from_dict({**files, **CAIRO_TEST_MODULES})
        )

    with pytest.raises(exc_type) as e:
        preprocess_codes(codes=[(code, "")], pass_manager=pass_manager, main_scope=main_scope)
    # Remove line and column information from the error using a regular expression.
    assert (
        re.sub("(autogen[a-zA-Z0-9_/.]+)?:[0-9]+:[0-9]+", "file:?:?", str(e.value)) == error.strip()
    ), f"Unexpected error string. Expected:\n{error.strip()}\nFound:\n{e.value}"
