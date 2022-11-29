import pytest

from starkware.cairo.lang.compiler.ast.formatting_utils import set_one_item_per_line
from starkware.cairo.lang.compiler.ast.particle import (
    Particle,
    ParticleFormattingConfig,
    ParticleList,
    SeparatedParticleList,
    particles_in_lines,
)


def run_test_particles_in_lines(
    particles: Particle,
    config: ParticleFormattingConfig,
    expected: str,
    expected_one_per_line: str,
):
    with set_one_item_per_line(False):
        assert (
            particles_in_lines(
                particles=particles,
                config=config,
            )
            == expected
        )
    with set_one_item_per_line(True):
        assert (
            particles_in_lines(
                particles=particles,
                config=config,
            )
            == expected_one_per_line
        )


@pytest.mark.parametrize("trailing_separator", [True, False])
def test_particles_in_lines(trailing_separator: bool):
    maybe_comma = "," if trailing_separator else ""
    particles = ParticleList(
        elements=[
            "start ",
            "+++ ",
            "ba( ",
            SeparatedParticleList(
                elements=["a", "b", "c", "dddd", "e", "f"],
                end=")",
                trailing_separator=trailing_separator,
            ),
            " + df",
        ]
    )
    expected = f"""\
start +++
    ba(
    a, b, c,
    dddd, e,
    f{maybe_comma}) + df\
"""
    expected_one_per_line = """\
start +++
    ba(
        a,
        b,
        c,
        dddd,
        e,
        f,
    ) + df\
"""
    run_test_particles_in_lines(
        particles=particles,
        config=ParticleFormattingConfig(allowed_line_length=12, line_indent=4),
        expected=expected,
        expected_one_per_line=expected_one_per_line,
    )

    # Formatting of SeparatedParticleList with non-trivial starts.

    particles = ParticleList(
        elements=[
            "let x = ",
            "a ",
            "- ",
            SeparatedParticleList(
                elements=["b + ", "c"],
                separator="",
                start="(",
                end=")",
                trailing_separator=trailing_separator,
            ),
        ]
    )

    expected = """\
let x = a -
    (b + c)\
"""

    expected_one_per_line = """\
let x = a - (
    b + c
)\
"""

    run_test_particles_in_lines(
        particles=particles,
        config=ParticleFormattingConfig(allowed_line_length=15, line_indent=4),
        expected=expected,
        expected_one_per_line=expected_one_per_line,
    )

    particles = ParticleList(
        elements=[
            "let uvwxyz = ",
            SeparatedParticleList(
                elements=["a", "b"],
                separator=", ",
                start="foobar(",
                end=")",
                trailing_separator=trailing_separator,
            ),
        ]
    )

    expected = expected_one_per_line = f"""\
let uvwxyz =
    foobar(a, b{maybe_comma})\
"""

    run_test_particles_in_lines(
        particles=particles,
        config=ParticleFormattingConfig(allowed_line_length=18, line_indent=4),
        expected=expected,
        expected_one_per_line=expected_one_per_line,
    )

    # Same particles, shorter line length.

    expected = f"""\
let uvwxyz =
    foobar(a,
        b{maybe_comma})\
"""

    expected_one_per_line = f"""\
let uvwxyz =
    foobar(
        a, b{maybe_comma}
    )\
"""

    run_test_particles_in_lines(
        particles=particles,
        config=ParticleFormattingConfig(allowed_line_length=15, line_indent=4),
        expected=expected,
        expected_one_per_line=expected_one_per_line,
    )

    particles = ParticleList(
        elements=[
            "func f(",
            SeparatedParticleList(
                elements=["x", "y", "z"],
                end=") -> (",
                trailing_separator=trailing_separator,
            ),
            SeparatedParticleList(
                elements=["a", "b", "c"],
                end="):",
                trailing_separator=trailing_separator,
            ),
        ]
    )
    expected = f"""\
func f(
    x, y,
    z{maybe_comma}) -> (
    a, b,
    c{maybe_comma}):\
"""
    expected_one_per_line = f"""\
func f(
    x, y, z{maybe_comma}
) -> (
    a, b, c{maybe_comma}
):\
"""
    run_test_particles_in_lines(
        particles=particles,
        config=ParticleFormattingConfig(allowed_line_length=12, line_indent=4),
        expected=expected,
        expected_one_per_line=expected_one_per_line,
    )

    # Same particles, using one_per_line=True.
    expected = f"""\
func f(
    x,
    y,
    z{maybe_comma}) -> (
    a,
    b,
    c{maybe_comma}):\
"""
    with set_one_item_per_line(False):
        assert (
            particles_in_lines(
                particles=particles,
                config=ParticleFormattingConfig(
                    allowed_line_length=12, line_indent=4, one_per_line=True
                ),
            )
            == expected
        )

    # Same particles, using one_per_line=True, longer lines.
    expected = f"""\
func f(
    x, y, z{maybe_comma}) -> (
    a, b, c{maybe_comma}):\
"""
    with set_one_item_per_line(False):
        assert (
            particles_in_lines(
                particles=particles,
                config=ParticleFormattingConfig(
                    allowed_line_length=19, line_indent=4, one_per_line=True
                ),
            )
            == expected
        )

    particles = ParticleList(
        elements=[
            "func f(",
            SeparatedParticleList(
                elements=["x", "y", "z"],
                end=") -> (",
                trailing_separator=trailing_separator,
            ),
            SeparatedParticleList(
                elements=[],
                end="):",
                trailing_separator=trailing_separator,
            ),
        ]
    )

    maybe_comma_on_a_new_line = "\n    ," if trailing_separator else ""
    expected = f"""\
func f(
    x, y, z{maybe_comma}) -> ({maybe_comma_on_a_new_line}):\
"""
    with set_one_item_per_line(False):
        assert (
            particles_in_lines(
                particles=particles,
                config=ParticleFormattingConfig(allowed_line_length=19, line_indent=4),
            )
            == expected
        )


def test_linebreak_on_particle_space():
    """
    Tests line breaking when the line length is exceeded by the space in the ', ' seperator at the
    end of a particle.
    """
    particles = ParticleList(
        elements=[
            "func f(",
            SeparatedParticleList(elements=["x", "y", "z"], end=") -> ("),
            SeparatedParticleList(elements=[], end="):"),
        ]
    )
    expected = """\
func f(
    x, y,
    z) -> (
    ):\
"""
    expected_one_per_line = """\
func f(
    x,
    y,
    z,
) -> ():\
"""
    run_test_particles_in_lines(
        particles=particles,
        config=ParticleFormattingConfig(allowed_line_length=9, line_indent=4),
        expected=expected,
        expected_one_per_line=expected_one_per_line,
    )

    run_test_particles_in_lines(
        particles=particles,
        config=ParticleFormattingConfig(allowed_line_length=10, line_indent=4),
        expected=expected,
        expected_one_per_line=expected_one_per_line,
    )

    expected = """\
func f(
    x,
    y,
    z) -> (
    ):\
"""
    run_test_particles_in_lines(
        particles=particles,
        config=ParticleFormattingConfig(allowed_line_length=8, line_indent=4),
        expected=expected,
        expected_one_per_line=expected_one_per_line,
    )


def test_nested_particle_lists():
    return_val_d = SeparatedParticleList(
        elements=[
            "felt",
            SeparatedParticleList(elements=["felt, felt"], start="(", end=")"),
        ],
        start="d: (",
        end=")",
    )
    return_val_e = SeparatedParticleList(
        elements=["f: felt", "g: felt"],
        start="e: (",
        end=")",
    )
    return_val_h = SeparatedParticleList(
        elements=["felt", "felt", "felt", "felt"],
        start="h: (",
        end=")",
    )
    return_val_b = SeparatedParticleList(
        elements=[
            "c: felt",
            return_val_d,
            return_val_e,
            return_val_h,
        ],
        start="b: (",
        end=")",
    )
    particles = ParticleList(
        elements=[
            "func f(",
            SeparatedParticleList(elements=["x", "y", "z"], end=") -> ("),
            SeparatedParticleList(
                elements=[
                    "a: felt",
                    return_val_b,
                ],
                end="):",
            ),
        ]
    )
    expected = """\
func f(x, y, z) -> (
    a: felt,
    b: (c: felt,
        d: (felt, (felt, felt)),
        e: (f: felt, g: felt),
        h: (felt, felt, felt,
            felt))):\
"""
    expected_one_per_line = """\
func f(x, y, z) -> (
    a: felt,
    b: (
        c: felt,
        d: (felt, (felt, felt)),
        e: (f: felt, g: felt),
        h: (
            felt, felt, felt, felt
        ),
    ),
):\
"""
    run_test_particles_in_lines(
        particles=particles,
        config=ParticleFormattingConfig(allowed_line_length=35, line_indent=4),
        expected=expected,
        expected_one_per_line=expected_one_per_line,
    )
