from starkware.cairo.lang.compiler.ast.types import TypedIdentifier
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError


def assert_no_modifier(typed_identifier: TypedIdentifier):
    """
    Throws a PreprocessorError if typed_identifier has a modifier.
    """
    if typed_identifier.modifier is not None:
        raise PreprocessorError(
            f"Unexpected modifier '{typed_identifier.modifier.format()}'.",
            location=typed_identifier.modifier.location)
