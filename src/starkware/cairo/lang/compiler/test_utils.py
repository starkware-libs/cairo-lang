from starkware.cairo.lang.compiler.parser_transformer import DEFAULT_SHORT_STRING_MAX_LENGTH
from starkware.python.utils import to_ascii_string


def read_file_from_dict(dct):
    """
    Given a dictionary from a package name (a.b.c) to a file content returns a function that can be
    passed to collect_imports.
    """
    return lambda x: (dct[x], x)


def short_string_to_felt(short_string: str) -> int:
    """
    Returns a felt representation of the given short string.
    """
    if len(short_string) > DEFAULT_SHORT_STRING_MAX_LENGTH:
        raise ValueError(
            f"Short string (e.g., 'abc') length must be at most {DEFAULT_SHORT_STRING_MAX_LENGTH}."
        )
    try:
        text_bytes = short_string.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError(f"Expected an ascii string. Found: {to_ascii_string(short_string)}.")

    return int.from_bytes(text_bytes, "big")
