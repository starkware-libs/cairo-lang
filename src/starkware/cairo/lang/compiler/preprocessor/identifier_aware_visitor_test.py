import pytest

from starkware.cairo.lang.compiler.identifier_definition import ConstDefinition
from starkware.cairo.lang.compiler.preprocessor.identifier_aware_visitor import (
    IdentifierAwareVisitor,
)
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.scoped_name import ScopedName


def test_add_name_definition_no_future():
    visitor = IdentifierAwareVisitor()

    test_id = ScopedName.from_string("test_id")
    location = None

    visitor.add_name_definition(
        name=test_id,
        identifier_definition=ConstDefinition(value=1),
        location=location,
        require_future_definition=False,
    )

    with pytest.raises(PreprocessorError, match=f"Redefinition of 'test_id'."):
        visitor.add_name_definition(
            name=test_id,
            identifier_definition=ConstDefinition(value=1),
            location=location,
            require_future_definition=False,
        )
