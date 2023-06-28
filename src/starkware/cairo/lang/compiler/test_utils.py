from typing import Dict

from starkware.cairo.lang.compiler.identifier_definition import IdentifierDefinition
from starkware.cairo.lang.compiler.parser_transformer import DEFAULT_SHORT_STRING_MAX_LENGTH
from starkware.cairo.lang.compiler.preprocessor.preprocessor import Preprocessor
from starkware.cairo.lang.compiler.scoped_name import ScopedName
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


def create_testing_preprocessor(mocked_definitions: Dict[ScopedName, IdentifierDefinition]):
    """
    Creates a subclass of Preprocessor which allows overriding identifiers (such as constants).
    mocked_definitions is a map from identifier name to its overriding definition.
    """

    class TestingPreprocessor(Preprocessor):
        def __init__(self, *args, **kw):
            super().__init__(*args, **kw)

            for name in mocked_definitions:
                assert (
                    self.identifiers.get_by_full_name(name) is not None
                ), f"Can not override '{name}' as there is no such definition."

        def add_name_definition(
            self,
            name: ScopedName,
            identifier_definition: IdentifierDefinition,
            location,
            require_future_definition=True,
        ):
            mocked_definition = mocked_definitions.get(name)
            if mocked_definition is not None:
                # Definition is mocked, override the identifier_definition.
                identifier_definition = mocked_definition

            super().add_name_definition(
                name,
                identifier_definition,
                location,
                require_future_definition=require_future_definition,
            )

    return TestingPreprocessor
