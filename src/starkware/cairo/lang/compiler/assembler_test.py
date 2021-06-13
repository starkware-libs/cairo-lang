import pytest

from starkware.cairo.lang.compiler.identifier_definition import ConstDefinition, LabelDefinition
from starkware.cairo.lang.compiler.identifier_manager import (
    IdentifierManager, MissingIdentifierError)
from starkware.cairo.lang.compiler.preprocessor.flow import ReferenceManager
from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.lang.compiler.scoped_name import ScopedName


def test_main_scope():
    identifiers = IdentifierManager.from_dict({
        ScopedName.from_string('a.b'): ConstDefinition(value=1),
        ScopedName.from_string('x.y.z'): ConstDefinition(value=2),
    })
    reference_manager = ReferenceManager()

    program = Program(
        prime=0, data=[], hints={}, builtins=[], main_scope=ScopedName.from_string('a'),
        identifiers=identifiers, reference_manager=reference_manager)

    # Check accessible identifiers.
    assert program.get_identifier('b', ConstDefinition).value == 1

    # Ensure inaccessible identifiers.
    with pytest.raises(MissingIdentifierError, match="Unknown identifier 'a'."):
        program.get_identifier('a.b', ConstDefinition)

    with pytest.raises(MissingIdentifierError, match="Unknown identifier 'x'."):
        program.get_identifier('x.y', ConstDefinition)

    with pytest.raises(MissingIdentifierError, match="Unknown identifier 'y'."):
        program.get_identifier('y', ConstDefinition)

    # Full name lookup.
    assert program.get_identifier('a.b', ConstDefinition, full_name_lookup=True).value == 1
    assert program.get_identifier('x.y.z', ConstDefinition, full_name_lookup=True).value == 2


def test_program_start_property():
    identifiers = IdentifierManager.from_dict({
        ScopedName.from_string('some.main.__start__'): LabelDefinition(3),
    })
    reference_manager = ReferenceManager()
    main_scope = ScopedName.from_string('some.main')

    # The label __start__ is in identifiers.
    program = Program(
        prime=0, data=[], hints={}, builtins=[], main_scope=main_scope, identifiers=identifiers,
        reference_manager=reference_manager)
    assert program.start == 3

    # The label __start__ is not in identifiers.
    program = Program(
        prime=0, data=[], hints={}, builtins=[], main_scope=main_scope,
        identifiers=IdentifierManager(), reference_manager=reference_manager)
    assert program.start == 0
