from starkware.cairo.lang.compiler.ast.formatting_utils import (
    ParticleFormattingConfig, create_particle_sublist, particles_in_lines)


def test_particles_in_lines():
    particles = [
        'start ',
        'foo ',
        'bar ',
        create_particle_sublist(['a', 'b', 'c', 'dddd', 'e', 'f'], '*'),
        ' asdf',
    ]
    expected = """\
start foo
  bar
  a, b, c,
  dddd, e,
  f* asdf\
"""
    assert particles_in_lines(
        particles=particles,
        config=ParticleFormattingConfig(allowed_line_length=12, line_indent=2),
    ) == expected

    particles = [
        'func f(',
        create_particle_sublist(['x', 'y', 'z'], ') -> ('),
        create_particle_sublist(['a', 'b', 'c'], '):'),
    ]
    expected = """\
func f(
    x, y,
    z) -> (
    a, b,
    c):\
"""
    assert particles_in_lines(
        particles=particles,
        config=ParticleFormattingConfig(allowed_line_length=12, line_indent=4),
    ) == expected

    # Same particles, using one_per_line=True.
    expected = """\
func f(
    x,
    y,
    z) -> (
    a,
    b,
    c):\
"""
    assert particles_in_lines(
        particles=particles,
        config=ParticleFormattingConfig(
            allowed_line_length=12, line_indent=4, one_per_line=True),
    ) == expected

    # Same particles, using one_per_line=True, longer lines.
    expected = """\
func f(
    x, y, z) -> (
    a, b, c):\
"""
    assert particles_in_lines(
        particles=particles,
        config=ParticleFormattingConfig(
            allowed_line_length=19, line_indent=4, one_per_line=True),
    ) == expected

    particles = [
        'func f(',
        create_particle_sublist(['x', 'y', 'z'], ') -> ('),
        create_particle_sublist([], '):'),
    ]
    expected = """\
func f(
    x, y, z) -> ():\
"""
    assert particles_in_lines(
        particles=particles,
        config=ParticleFormattingConfig(allowed_line_length=19, line_indent=4),
    ) == expected
