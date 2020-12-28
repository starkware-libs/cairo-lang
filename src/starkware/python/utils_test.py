import re

import pytest

from starkware.python.utils import WriteOnceDict, indent, unique


def test_indent():
    assert indent('aa\n  bb', 2) == '  aa\n    bb'
    assert indent('aa\n  bb\n', 2) == '  aa\n    bb\n'
    assert indent('  aa\n  bb\n\ncc\n', 2) == '    aa\n    bb\n\n  cc\n'


def test_unique():
    assert unique([3, 7, 5, 8, 7, 6, 3, 9]) == [3, 7, 5, 8, 6, 9]


def test_write_once_dict():
    d = WriteOnceDict()

    key = 5
    value = None
    d[key] = value
    with pytest.raises(AssertionError, match=re.escape(
            f"Trying to set key=5 to 'b' but key=5 is already set to 'None'.")):
        d[key] = 'b'
