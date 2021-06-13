import asyncio
import itertools
import os
import random
import re
import subprocess
from collections import UserDict
from typing import Any, Iterable, List, Optional


def get_package_path():
    """
    Returns ROOT_PATH s.t. $ROOT_PATH/starkware is the package folder.
    """
    import starkware.python
    return os.path.abspath(os.path.join(os.path.dirname(starkware.python.__file__), '../../'))


def get_build_dir_path(rel_path=''):
    """
    Returns a path to a file inside the build directory (or the docker).
    rel_path is the relative path of the file with respect to the build directory.
    """
    build_root = os.environ['BUILD_ROOT']
    return os.path.join(build_root, rel_path)


def get_source_dir_path(rel_path=''):
    """
    Returns a path to a file inside the source directory. Does not work in docker.
    rel_path is the relative path of the file with respect to the source directory.
    """
    source_root = os.path.join(os.environ['BUILD_ROOT'], '../../')
    assert os.path.exists(os.path.join(source_root, 'src'))
    return os.path.join(source_root, rel_path)


def assert_same_and_get(*args):
    """
    Verifies that all the arguments are the same, and returns this value.
    For example, assert_same_and_get(5, 5, 5) will return 5, and assert_same_and_get(0, 1) will
    raise an AssertionError.
    """
    assert len(set(args)) == 1, 'Values are not the same (%s)' % (args,)
    return args[0]


def unique(x):
    """
    Removes duplicates while preserving order.
    """
    return list(dict.fromkeys(x).keys())


def unique_ordered_union(x, y):
    """
    Returns a list containing the union of 'x' and 'y', preserving order and removing duplicates.
    """
    return list(dict.fromkeys(list(x) + list(y)).keys())


def add_counters(x, y):
    """
    Given two dicts x, y, returns a dict d s.t.
      d[a] = d[x] + d[y]
    """
    return {k: x.get(k, 0) + y.get(k, 0) for k in unique_ordered_union(x.keys(), y.keys())}


def sub_counters(x, y):
    """
    Given two dicts x, y, returns a dict d s.t.
      d[a] = d[x] - d[y]
    """
    return {k: x.get(k, 0) - y.get(k, 0) for k in unique_ordered_union(x.keys(), y.keys())}


def indent(code, indentation):
    """
    Indent code by 'indentation' spaces.
    For example, indent('hello\nworld\n', 2) -> '  hello\n  world\n'.
    """
    if len(code) == 0:
        return code
    if isinstance(indentation, int):
        indentation = ' ' * indentation
    elif not isinstance(indentation, str):
        raise TypeError(f'Supports only int or str, got {type(indentation).__name__}')

    # Replace every occurrence of \n, with \n followed by indentation,
    # unless the \n is the last characther of the string or is followed by another \n.
    # We enforce the "not followed by ..." condition using negative lookahead (?!\n|$),
    # looking for end of string ($) or another \n.
    return indentation + re.sub(r'\n(?!\n|$)', '\n' + indentation, code)


def get_random_instance() -> random.Random:
    """
    Returns the Random instance in the random module level.
    """
    return random._inst  # type: ignore[attr-defined]


def initialize_random(
        random_object: Optional[random.Random] = None, seed: Optional[int] = None) -> random.Random:
    """
    Returns a Random object initialized according to the given parameters.
    If both are None, the Random instance instantiated in the random module is returned.
    """
    if random_object is not None:
        return random_object

    return random.Random(seed) if seed is not None else get_random_instance()


def get_random_bytes(random_object: Optional[random.Random] = None, *, n: int):
    """
    Returns a random bytes object of length n.
    NOTE: This function is unsafe and should only be used for testing.
    """
    r = initialize_random(random_object=random_object)
    return bytes(r.getrandbits(8) for _ in range(n))


def compare_files(src, dst, fix):
    """
    If 'fix' is False, checks that the files are the same.
    If 'fix' is True, overrides dst with src.
    """
    subprocess.check_call(['cp' if fix else 'diff', src, dst])


def remove_trailing_spaces(code):
    """
    Removes spaces from end of lines.
    For example, remove_trailing_spaces('hello \nworld   \n') -> 'hello\nworld\n'.
    """
    return re.sub(' +$', '', code, flags=re.MULTILINE)


def should_discard_key(key, exclude: List[str]) -> bool:
    return any(field_to_discard in key for field_to_discard in exclude)


def discard_key(d: dict, key, to_replace_by: Optional[str]):
    if to_replace_by is None:
        del d[key]
    else:
        d[key] = to_replace_by


class WriteOnceDict(UserDict):
    """
    Write once dictionary.
    A Dict that enforces that each key is set only once.
    Trying to set an existing key to its current value also raises an AssertionError.
    """

    def __setitem__(self, key, value):
        assert key not in self.data, \
            f"Trying to set key={key} to '{value}' but key={key} is already set to '{self[key]}'."
        self.data[key] = value


def camel_to_snake_case(camel_case_name: str) -> str:
    """
    Converts a name with Capital first letters to lower case with '_' as separators.
    For example, CamelToSnakeCase -> camel_to_snake_case.
    """
    return (camel_case_name[0] + re.sub(r'([A-Z])', r'_\1', camel_case_name[1:])).lower()


def snake_to_camel_case(snake_case_name: str) -> str:
    """
    Converts the first letter to upper case (if possible) and all the '_l' to 'L'.
    For example snake_to_camel_case -> SnakeToCamelCase.
    """
    return re.subn(r'(^|_)([a-z])', lambda m: m.group(2).upper(), snake_case_name)[0]


async def cancel_futures(*futures: asyncio.Future):
    """
    Cancels given futures and awaits on them in order to reveal exceptions.
    Used in a process' teardown.
    """
    for future in futures:
        future.cancel()

    for future in futures:
        try:
            await future
        except asyncio.CancelledError:
            pass


def safe_zip(*iterables: Iterable[Any]) -> Iterable:
    """
    Zips iterables. Makes sure the lengths of all iterables are equal.
    """
    sentinel = object()
    for combo in itertools.zip_longest(*iterables, fillvalue=sentinel):
        assert sentinel not in combo, 'Iterables to safe_zip are not equal in length.'
        yield combo
