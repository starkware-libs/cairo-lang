import copy
import itertools

from starkware.cairo.lang.compiler.ast.code_elements import (
    CodeElementReference,
    CodeElementTemporaryVariable,
)
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo
from starkware.cairo.lang.compiler.filter_unused_identifiers import filter_unused_identifiers
from starkware.cairo.lang.compiler.identifier_definition import (
    ConstDefinition,
    FunctionDefinition,
    ReferenceDefinition,
    StructDefinition,
    TypeDefinition,
)
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.vm.test_utils import run_program_in_vm

PRIME = 2**64 + 13


def test_filter_unused_identifiers():
    program = compile_cairo(
        code="""
func main() {
    alloc_locals;
    local a;
    local b;

    local x;
    tempvar x;
    %{ ids.x = 5 %}
    tempvar y;

    with_attr error_message("Error. b={b}") {
        [ap] = 1;
    }
    return ();
}
""",
        prime=PRIME,
    )

    original_program_copy = copy.deepcopy(program)
    filtered_program = filter_unused_identifiers(program)

    # Make sure the function did not modify the original program.
    assert program == original_program_copy

    # Compare hint's references before and after the filtering.
    (hint,) = itertools.chain.from_iterable(program.hints.values())
    assert hint.flow_tracking_data.reference_ids == {
        ScopedName.from_string("__main__.main.a"): 0,
        ScopedName.from_string("__main__.main.b"): 1,
        ScopedName.from_string("__main__.main.x"): 3,
    }
    (hint,) = itertools.chain.from_iterable(filtered_program.hints.values())
    assert hint.flow_tracking_data.reference_ids == {ScopedName.from_string("__main__.main.x"): 1}

    # Compare attribute's references before and after the filtering.
    (attribute,) = program.attributes
    assert attribute.flow_tracking_data is not None
    assert attribute.flow_tracking_data.reference_ids == {
        ScopedName.from_string("__main__.main.a"): 0,
        ScopedName.from_string("__main__.main.b"): 1,
        ScopedName.from_string("__main__.main.x"): 3,
        ScopedName.from_string("__main__.main.y"): 4,
    }
    (attribute,) = filtered_program.attributes
    assert attribute.flow_tracking_data is not None
    assert attribute.flow_tracking_data.reference_ids == {
        ScopedName.from_string("__main__.main.b"): 0
    }

    program_identifiers = {
        (str(name), type(identifier_def))
        for name, identifier_def in filtered_program.identifiers.as_dict().items()
    }
    assert program_identifiers == {
        ("__main__.main.x", ReferenceDefinition),
        ("__main__.main.b", ReferenceDefinition),
        ("__main__.main", FunctionDefinition),
        ("__main__.main.Args", StructDefinition),
        ("__main__.main.ImplicitArgs", StructDefinition),
        ("__main__.main.Return", TypeDefinition),
        ("__main__.main.SIZEOF_LOCALS", ConstDefinition),
    }

    program_references = []
    for reference in filtered_program.reference_manager.references:
        assert isinstance(
            reference.definition_code_element, (CodeElementReference, CodeElementTemporaryVariable)
        )
        program_references.append(
            (reference.pc, reference.definition_code_element.typed_identifier.identifier.name)
        )
    assert program_references == [(2, "b"), (4, "x")]

    # Run both program and filtered_program and compare.
    vm_before = run_program_in_vm(program=program, steps=4, pc=0, ap=100, fp=100, prime=PRIME)
    vm_after = run_program_in_vm(
        program=filtered_program, steps=4, pc=0, ap=100, fp=100, prime=PRIME
    )
    assert vm_before.run_context == vm_after.run_context
