import re

import pytest

from starkware.python.utils import (
    WriteOnceDict,
    all_subclasses,
    blockify,
    composite,
    gather_in_chunks,
    indent,
    iter_blockify,
    safe_zip,
    unique,
)


def test_indent():
    assert indent("aa\n  bb", 2) == "  aa\n    bb"
    assert indent("aa\n  bb\n", 2) == "  aa\n    bb\n"
    assert indent("  aa\n  bb\n\ncc\n", 2) == "    aa\n    bb\n\n  cc\n"


def test_unique():
    assert unique([3, 7, 5, 8, 7, 6, 3, 9]) == [3, 7, 5, 8, 6, 9]


def test_write_once_dict():
    d = WriteOnceDict()

    key = 5
    value = None
    d[key] = value
    with pytest.raises(
        AssertionError,
        match=re.escape(f"Trying to set key=5 to 'b' but key=5 is already set to 'None'."),
    ):
        d[key] = "b"


def test_safe_zip():
    # Test empty case.
    assert list(safe_zip()) == list(zip())

    # Test equal-length iterables (including a generator).
    assert list(safe_zip((i for i in range(3)), range(3, 6), [1, 2, 3])) == list(
        zip((i for i in range(3)), range(3, 6), [1, 2, 3])
    )

    # Test unequal-length iterables.
    test_cases = [[range(4), range(3)], [[], range(3)]]
    for iterables in test_cases:
        with pytest.raises(AssertionError, match="Iterables to safe_zip are not equal in length."):
            list(safe_zip(*iterables))  # Consume generator to get to the error.


def test_composite():
    # Define the function: (2 * (x - y) + 1) ** 2.
    f = composite(lambda x: x ** 2, lambda x: 2 * x + 1, lambda x, y: x - y)
    assert f(3, 5) == 9


def test_blockify_sliceable():
    data = [1, 2, 3, 4, 5, 6, 7]

    # Edge cases.
    assert list(blockify(data=[], chunk_size=2)) == []
    assert list(blockify(data=data, chunk_size=len(data))) == [data]
    with pytest.raises(expected_exception=AssertionError, match="chunk_size"):
        blockify(data=data, chunk_size=0)

    assert list(blockify(data=data, chunk_size=4)) == [[1, 2, 3, 4], [5, 6, 7]]
    assert list(blockify(data=data, chunk_size=2)) == [[1, 2], [3, 4], [5, 6], [7]]


def test_blockify_iterable():
    data_length = 7
    get_data_generator = lambda: (i for i in range(data_length))

    # Edge cases.
    assert list(iter_blockify(data=[], chunk_size=2)) == []
    assert list(iter_blockify(data=get_data_generator(), chunk_size=data_length)) == [
        list(get_data_generator())
    ]
    with pytest.raises(expected_exception=AssertionError, match="chunk_size"):
        list(iter_blockify(data=get_data_generator(), chunk_size=0))

    assert list(iter_blockify(data=get_data_generator(), chunk_size=2)) == [
        [0, 1],
        [2, 3],
        [4, 5],
        [6],
    ]


@pytest.mark.asyncio
async def test_gather_in_chunks():
    async def foo(i: int):
        return i

    n_awaitables = 7
    result = await gather_in_chunks(awaitables=(foo(i) for i in range(n_awaitables)), chunk_size=2)
    assert result == list(range(n_awaitables))


def test_all_subclasses():
    # Inheritance graph, the lower rows inherit from the upper rows.
    #   A   B
    #  / \ /
    # C   D
    #  \ /|
    #   E F
    class A:
        pass

    class B:
        pass

    class C(A):
        pass

    class D(B, A):
        pass

    class E(C, D):
        pass

    class F(D):
        pass

    all_subclass_objects = all_subclasses(A)
    all_subclasses_set = set(all_subclass_objects)
    assert len(all_subclass_objects) == len(all_subclasses_set)
    assert all_subclasses_set == {A, C, D, E, F}
