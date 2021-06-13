import re

import pytest

from starkware.python.utils import WriteOnceDict, indent, safe_zip, unique


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


def test_safe_zip():
    # Test empty case.
    assert list(safe_zip()) == list(zip())

    # Test equal-length iterables (including a generator).
    assert (
        list(safe_zip((i for i in range(3)), range(3, 6), [1, 2, 3])) ==
        list(zip((i for i in range(3)), range(3, 6), [1, 2, 3])))

    # Test unequal-length iterables.
    test_cases = [[range(4), range(3)], [[], range(3)]]
    for iterables in test_cases:
        with pytest.raises(AssertionError, match='Iterables to safe_zip are not equal in length.'):
            list(safe_zip(*iterables))  # Consume generator to get to the error.
