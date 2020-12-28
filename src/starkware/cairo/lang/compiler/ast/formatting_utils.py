"""
Contains utils that help with formatting of Cairo code.
"""

import dataclasses
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import field
from typing import List

from starkware.cairo.lang.compiler.error_handling import LocationError

INDENTATION = 4
LocationField = field(default=None, hash=False, compare=False)
max_line_length_ctx_var: ContextVar[int] = ContextVar('max_line_length', default=100)


def get_max_line_length():
    return max_line_length_ctx_var.get()


@contextmanager
def set_max_line_length(line_length: bool):
    """
    Context manager that sets max_line_length context variable.
    """
    previous = get_max_line_length()
    max_line_length_ctx_var.set(line_length)
    yield
    max_line_length_ctx_var.set(previous)


class FormattingError(LocationError):
    pass


@dataclasses.dataclass
class ParticleFormattingConfig:
    # The maximal line length.
    allowed_line_length: int
    # The indentation, starting from the second line.
    line_indent: int
    # The prefix of the first line.
    first_line_prefix: str = ''
    # At most one item per line.
    one_per_line: bool = False


class ParticleLineBuilder:
    """
    Builds particle lines, wrapping line lengths as needed.
    """

    def __init__(self, config: ParticleFormattingConfig):
        self.lines: List[str] = []
        self.line = config.first_line_prefix
        self.line_is_new = True

        self.config = config

    def newline(self):
        """
        Opens a new line.
        """
        if self.line_is_new:
            return
        self.lines.append(self.line)
        self.line_is_new = True
        self.line = ' ' * self.config.line_indent

    def add_to_line(self, string):
        """
        Adds to current line, opening a new one if needed.
        """
        if len(self.line) + len(string) > self.config.allowed_line_length and not self.line_is_new:
            self.newline()
        self.line += string
        self.line_is_new = False

    def finalize(self):
        """
        Finalizes the particle lines and returns the result.
        """
        if self.line:
            self.lines.append(self.line)
        return '\n'.join(line.rstrip() for line in self.lines)


def create_particle_sublist(lst, end='', separator=', '):
    if not lst:
        # If the list is empty, return the single element 'end'.
        return end
    # Concatenate the 'separator' to all elements of the 'lst' and 'end' to the last one.
    return [elm + separator for elm in lst[:-1]] + [lst[-1] + end]


def particles_in_lines(particles, config: ParticleFormattingConfig):
    """
    Receives a list 'particles' that contains strings and particle sublists and generates lines
    according to the following rules:
        - The first line is not indented. All other lines start with 'line_indent' spaces.
        - A line containing more than one particle can be no longer than 'allowed_line_length'.
        - A sublist that cannot be fully concatenated to the current line opens a new line.

    Example:
    particles_in_lines(
        ['func f(',
         create_particle_sublist(['x', 'y', 'z'], ') -> ('),
         create_particle_sublist(['a', 'b', 'c'], '):')],
         12, 4)
    returns '''\
    func f(
        x, y,
        z) -> (
        a, b,
        c):\
    '''
    With a longer line length we will get the lists on the same line:
    particles_in_lines(
        ['func f(',
         create_particle_sublist(['x', 'y', 'z'], ') -> ('),
         create_particle_sublist([], '):')],
         19, 4)
    returns '''\
    func f(
        x, y, z) -> ():\
    '''
    """

    builder = ParticleLineBuilder(config=config)

    for particle in particles:
        if isinstance(particle, str):
            builder.add_to_line(particle)

        if isinstance(particle, list):
            # If the entire sublist fits in a single line, add it.
            if sum(map(len, particle), config.line_indent) < config.allowed_line_length:
                builder.add_to_line(''.join(particle))
                continue
            builder.newline()
            for member in particle:
                if config.one_per_line:
                    builder.newline()
                builder.add_to_line(member)

    return builder.finalize()
