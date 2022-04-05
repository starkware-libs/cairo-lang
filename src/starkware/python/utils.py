import asyncio
import contextlib
import itertools
import logging
import os
import random
import re
import subprocess
import time
from collections import UserDict
from typing import (
    Any,
    AsyncIterable,
    Awaitable,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    TypeVar,
)

import yaml

# All functions with stubs are imported from this module.
from starkware.python.utils_stub_module import *  # noqa

T = TypeVar("T")
NumType = TypeVar("NumType", int, float)
HASH_BYTES = 32


def get_package_path():
    """
    Returns ROOT_PATH s.t. $ROOT_PATH/starkware is the package folder.
    """
    import starkware.python

    return os.path.abspath(os.path.join(os.path.dirname(starkware.python.__file__), "../../"))


def get_build_dir_path(rel_path=""):
    """
    Returns a path to a file inside the build directory (or the docker).
    rel_path is the relative path of the file with respect to the build directory.
    """
    build_root = os.environ["BUILD_ROOT"]
    return os.path.join(build_root, rel_path)


def get_source_dir_path(rel_path=""):
    """
    Returns a path to a file inside the source directory. Does not work in docker.
    rel_path is the relative path of the file with respect to the source directory.
    """
    source_root = os.path.join(os.environ["BUILD_ROOT"], "../../")
    assert os.path.exists(os.path.join(source_root, "src"))
    return os.path.join(source_root, rel_path)


def assert_same_and_get(*args):
    """
    Verifies that all the arguments are the same, and returns this value.
    For example, assert_same_and_get(5, 5, 5) will return 5, and assert_same_and_get(0, 1) will
    raise an AssertionError.
    """
    assert len(set(args)) == 1, "Values are not the same (%s)" % (args,)
    return args[0]


def assert_exhausted(iterator: Iterator):
    """
    Verifies that given iterator is empty.
    """
    assert all(False for _ in iterator), "Iterator is not empty."


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


def add_counters(x: Mapping[T, NumType], y: Mapping[T, NumType]) -> Dict[T, NumType]:
    """
    Given two dicts x, y, returns a dict d s.t.
      d[k] = x[k] + y[k]
    """
    return {k: x.get(k, 0) + y.get(k, 0) for k in unique_ordered_union(x.keys(), y.keys())}


def sub_counters(x: Mapping[T, NumType], y: Mapping[T, NumType]) -> Dict[T, NumType]:
    """
    Given two dicts x, y, returns a dict d s.t.
      d[k] = x[k] - y[k]
    """
    return {k: x.get(k, 0) - y.get(k, 0) for k in unique_ordered_union(x.keys(), y.keys())}


def multiply_counter_by_scalar(scalar: NumType, counter: Mapping[T, NumType]) -> Dict[T, NumType]:
    """
    Given a non-negative scalar and a counter, returns a dict d s.t.
      d[k] = scalar * counter[k]
    """
    return {k: scalar * v for k, v in counter.items()}


def indent(code, indentation):
    """
    Indent code by 'indentation' spaces.
    For example, indent('hello\nworld\n', 2) -> '  hello\n  world\n'.
    """
    if len(code) == 0:
        return code
    if isinstance(indentation, int):
        indentation = " " * indentation
    elif not isinstance(indentation, str):
        raise TypeError(f"Supports only int or str, got {type(indentation).__name__}")

    # Replace every occurrence of \n, with \n followed by indentation,
    # unless the \n is the last characther of the string or is followed by another \n.
    # We enforce the "not followed by ..." condition using negative lookahead (?!\n|$),
    # looking for end of string ($) or another \n.
    return indentation + re.sub(r"\n(?!\n|$)", "\n" + indentation, code)


def join_lines(lines: Iterable[str]) -> str:
    return "\n".join(lines)


def get_random_instance() -> random.Random:
    """
    Returns the Random instance in the random module level.
    """
    return random._inst  # type: ignore[attr-defined]


def initialize_random(
    random_object: Optional[random.Random] = None, seed: Optional[int] = None
) -> random.Random:
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
    subprocess.check_call(["cp" if fix else "diff", src, dst])


def remove_trailing_spaces(code):
    """
    Removes spaces from end of lines.
    For example, remove_trailing_spaces('hello \nworld   \n') -> 'hello\nworld\n'.
    """
    return re.sub(" +$", "", code, flags=re.MULTILINE)


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
        assert (
            key not in self.data
        ), f"Trying to set key={key} to '{value}' but key={key} is already set to '{self[key]}'."
        self.data[key] = value


def camel_to_snake_case(camel_case_name: str) -> str:
    """
    Converts a name with Capital first letters to lower case with '_' as separators.
    For example, CamelToSnakeCase -> camel_to_snake_case.
    """
    return (camel_case_name[0] + re.sub(r"([A-Z])", r"_\1", camel_case_name[1:])).lower()


def snake_to_camel_case(snake_case_name: str) -> str:
    """
    Converts the first letter to upper case (if possible) and all the '_l' to 'L'.
    For example snake_to_camel_case -> SnakeToCamelCase.
    """
    return re.subn(r"(^|_)([a-z])", lambda m: m.group(2).upper(), snake_case_name)[0]


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


def composite(*funcs):
    """
    Returns the composition of all the given functions, which is a function that runs the last
    function with the input args, and then runs the function before that with the return value of
    the last function and so on. Finally, the composition function will return the return value of
    the first function.

    Every function beside the last function should receive one argument.

    For example:
      f = composite(lambda x: x * 5, lambda x, y: x + y)
      assert f(2, 3) == (2 + 3) * 5
    """
    assert len(funcs) > 0

    def composition_function(*args, **kwargs):
        return_value: Any = funcs[-1](*args, **kwargs)
        for func in reversed(funcs[:-1]):
            return_value = func(return_value)
        return return_value

    return composition_function


def to_bytes(
    value: int,
    length: Optional[int] = None,
    byte_order: Optional[str] = None,
    signed: Optional[bool] = None,
) -> bytes:
    """
    Converts the given integer to a bytes object of given length and byte order.
    The default values are 32B width (which is the hash result width) and 'big', respectively.
    """
    if length is None:
        length = HASH_BYTES

    if byte_order is None:
        byte_order = "big"

    if signed is None:
        signed = False

    return int.to_bytes(value, length=length, byteorder=byte_order, signed=signed)


def from_bytes(
    value: bytes, byte_order: Optional[str] = None, signed: Optional[bool] = None
) -> int:
    """
    Converts the given bytes object (parsed according to the given byte order) to an integer.
    Default byte order is 'big'.
    """
    if byte_order is None:
        byte_order = "big"

    if signed is None:
        signed = False

    return int.from_bytes(value, byteorder=byte_order, signed=signed)


def blockify(data, chunk_size: int) -> Iterable:
    """
    Returns the given data partitioned to chunks of chunks_size (last chunk might be smaller).
    """
    assert chunk_size > 0, f"chunk_size must be greater than 0. Got: {chunk_size}."
    return (data[i : i + chunk_size] for i in range(0, len(data), chunk_size))


def iter_blockify(data: Iterable[T], chunk_size: int) -> Iterable[List[T]]:
    """
    Returns the given data partitioned to tuple-chunks of chunks_size (last chunk might be smaller).
    """
    assert chunk_size > 0, f"chunk_size must be greater than 0. Got: {chunk_size}."

    iterator = iter(data)
    while True:
        chunk = list(itertools.islice(iterator, chunk_size))
        if len(chunk) == 0:
            break

        yield chunk


async def gather_in_chunks(
    awaitables: Iterable[Awaitable[T]], chunk_size: Optional[int] = None
) -> List[T]:
    """
    Awaits on the given awaitables using asyncio.gather in chunks of chunk_size;
    Returns a list containing the results.
    """
    return [
        element
        async for element in gen_gather_in_chunks(awaitables=awaitables, chunk_size=chunk_size)
    ]


async def gen_gather_in_chunks(
    awaitables: Iterable[Awaitable[T]], chunk_size: Optional[int] = None
) -> AsyncIterable[T]:
    """
    Awaits on the given awaitables using asyncio.gather in chunks of chunk_size;
    Yields the results.
    """
    chunk_size = 100 if chunk_size is None else chunk_size
    for awaitable_chunk in iter_blockify(data=awaitables, chunk_size=chunk_size):
        chunk = await asyncio.gather(*awaitable_chunk)

        for element in chunk:
            yield element


def all_subclasses(cls: type) -> List[type]:
    """
    Recursively finds all subclasses of a given class.
    """
    return list(set(_all_subclasses(cls)))


def _all_subclasses(cls: type) -> List[type]:
    return [cls] + list(
        itertools.chain(*[_all_subclasses(subclass) for subclass in cls.__subclasses__()])
    )


def get_exception_repr(exception: Exception) -> str:
    return f"{type(exception).__name__}({exception})"


@contextlib.contextmanager
def log_time(logger: logging.Logger, name: str):
    """
    Logs the elapsed time in seconds.

    Example:
        with log_time(logger=logger, name="Foo"):
            sleep(1)
    """
    start = time.time()
    try:
        yield
    finally:
        logger.info(f"Ran '{name}'. Elapsed: {time.time() - start}.")


def to_ascii_string(value: str) -> str:
    """
    Converts the given string to an ascii-encodeable one by replacing non-ascii characters with '?'.
    """
    return value.encode("ascii", "replace").decode("ascii")


def update_yaml_file(file_path: str, data: Dict[str, Any]):
    """
    Updates yaml file in given path with given data.
    """
    with open(file_path, "w") as fp:
        fp.write(yaml.dump(data=data, default_flow_style=False, width=400))
        fp.flush()
