import re

import pytest

from starkware.cairo.lang.compiler.parser import ParserError, parse_file


def verify_exception(code: str, error: str):
    """
    Verifies that parsing the code results in the given error.
    """
    with pytest.raises(ParserError) as e:
        parse_file(code, '')
    # Remove line and column information from the error using a regular expression.
    assert re.sub(':[0-9]+:[0-9]+: ', 'file:?:?: ', str(e.value)) == error.strip()
