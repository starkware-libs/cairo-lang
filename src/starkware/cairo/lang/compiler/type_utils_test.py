from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.parser import parse_type
from starkware.cairo.lang.compiler.preprocessor.preprocessor_test_utils import preprocess_str
from starkware.cairo.lang.compiler.type_system import mark_type_resolved
from starkware.cairo.lang.compiler.type_utils import check_felts_only_type


def test_check_felts_only_type():
    program = preprocess_str(
        """
struct A {
    x: felt,
}

struct B {
}

struct C {
    x: felt,
    y: (felt, A, B),
    z: A,
}

struct D {
    x: felt*,
}

struct E {
    x: D,
}
""",
        prime=DEFAULT_PRIME,
    )

    for (typ, expected_res) in [
        # Positive cases.
        ("test_scope.A", 1),
        ("test_scope.B", 0),
        ("test_scope.C", 4),
        ("(felt, felt)", 2),
        ("(felt, (felt, test_scope.C))", 6),
        # Negative cases.
        ("test_scope.D", None),
        ("test_scope.E", None),
        ("(felt, test_scope.D)", None),
    ]:
        assert (
            check_felts_only_type(
                cairo_type=mark_type_resolved(parse_type(typ)),
                identifier_manager=program.identifiers,
            )
            == expected_res
        )
