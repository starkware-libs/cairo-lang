"""
Contains utils that help with formatting of Cairo code.
"""

import dataclasses
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import field
from typing import List, Union

import marshmallow

from starkware.cairo.lang.compiler.error_handling import LocationError

INDENTATION = 4
LocationField = field(
    default=None,
    hash=False,
    compare=False,
    metadata=dict(marshmallow_field=marshmallow.fields.Field(load_only=True, dump_only=True)),
)
max_line_length_ctx_var: ContextVar[int] = ContextVar("max_line_length", default=100)
one_item_per_line_ctx_var: ContextVar[bool] = ContextVar("one_item_per_line", default=False)


def get_max_line_length():
    return max_line_length_ctx_var.get()


@contextmanager
def set_max_line_length(line_length: int):
    """
    Context manager that sets max_line_length context variable.
    """
    token = max_line_length_ctx_var.set(line_length)
    try:
        yield
    finally:
        max_line_length_ctx_var.reset(token)


@contextmanager
def set_one_item_per_line(value: bool):
    """
    Context manager that sets one_item_per_line context variable.
    If true, each list item (e.g., function arguments) will be put in a separate line,
    if the list doesn't fit a single line.
    """
    token = one_item_per_line_ctx_var.set(value)
    try:
        yield
    finally:
        one_item_per_line_ctx_var.reset(token)


class FormattingError(LocationError):
    pass


@dataclasses.dataclass
class ParticleFormattingConfig:
    # The maximal line length.
    allowed_line_length: int
    # The indentation, starting from the second line.
    line_indent: int
    # The prefix of the first line.
    first_line_prefix: str = ""
    # At most one item per line.
    # Note: if the one_item_per_line ContextVar is True, this field is ignored (it has a slightly
    # different formatting).
    one_per_line: bool = False
    # If True, line_indent is doubled.
    # Note: if the one_item_per_line ContextVar is True, this field is ignored.
    double_indentation: bool = False


@dataclasses.dataclass(frozen=True)
class ParticleList:
    """
    A list of particles, which is a part of a larger list of particles that constructs one or
    more lines.
    """

    elements: List[str]
    separator: str = ", "
    end: str = ""

    def to_strings(self) -> List[str]:
        if len(self.elements) == 0:
            # If the list is empty, return the single element 'end'.
            return [self.end]
        # Concatenate the 'separator' to all elements and 'end' to the last one.
        return [elm + self.separator for elm in self.elements[:-1]] + [self.elements[-1] + self.end]

    def elements_to_string(self) -> str:
        """
        Returns a concatenation of the strings in self.elements, separated with self.separator.
        """
        return self.separator.join(self.elements)


class ParticleLineBuilder:
    """
    Builds particle lines, wrapping line lengths as needed.
    """

    def __init__(self, config: ParticleFormattingConfig):
        self.lines: List[str] = []
        self.line = config.first_line_prefix
        self.line_is_new = True

        self.config = config

    def newline(self, indent: bool = True):
        """
        Opens a new line.
        """
        if self.line_is_new:
            return
        self.lines.append(self.line)
        self.line_is_new = True
        self.line = (" " * self.config.line_indent) if indent else ""

    def add_to_line(self, string):
        """
        Adds to current line, opening a new one if needed.
        """
        expected_line_length = len(self.line) + len(string.rstrip())
        if expected_line_length > self.config.allowed_line_length and not self.line_is_new:
            self.newline()
        self.line += string
        self.line_is_new = False

    def can_fit_in_line(self, string: str) -> bool:
        """
        Returns True if the given string can fit in the current line.
        """
        return len(self.line) + len(string) <= self.config.allowed_line_length

    def finalize(self):
        """
        Finalizes the particle lines and returns the result.
        """
        if self.line:
            self.lines.append(self.line)
        return "\n".join(line.rstrip() for line in self.lines)


def add_list_new_format(builder: ParticleLineBuilder, particle_list: ParticleList):
    """
    Adds a particle list to the current line.
    If the list cannot be fully concatenated to the current line opens a new line, and puts each
    element of the list in a separate line, indented by 'INDENTATION' charactes.

    For example, using this function to format a list of arguments may result in the following
    formatting:
        func f(
            x,
            y,
            z,
        ) -> (
            a,
            b,
            c
        ):

    With a longer line length we will get the lists on the same line:
        func f(x, y, z) -> (a, b, c):
    """
    elements_string = particle_list.elements_to_string()

    # If the entire list fits in the current line, or the list is empty, add everything to the
    # current line.
    if (
        builder.can_fit_in_line(elements_string + particle_list.end)
        or len(particle_list.elements) == 0
    ):
        builder.add_to_line(elements_string + particle_list.end)
        return

    # If the entire list fits in a new line, add it.
    # Else, add each element of the list in a separate line.
    builder.newline()
    if builder.can_fit_in_line(elements_string):
        builder.add_to_line(elements_string)
    else:
        for elm in particle_list.elements:
            builder.newline()
            builder.add_to_line(elm + particle_list.separator)

    builder.newline(indent=False)
    builder.add_to_line(particle_list.end)


def add_list_old_format(
    builder: ParticleLineBuilder, particle_list: ParticleList, config: ParticleFormattingConfig
):
    """
    Adds a particle list to the current line.
    If the list cannot be fully concatenated to the current line opens a new line.

    For example, using this function to format a list of arguments may result in the following
    formatting:
        func f(
            x, y,
            z) -> (
            a, b,
            c):

    With a longer line length we will get the lists on the same line:
        func f(x, y, z) -> (a, b, c):
    """
    list_particles = particle_list.to_strings()

    # If the entire list fits in a single line, add it.
    if sum(map(len, list_particles), config.line_indent) < config.allowed_line_length:
        builder.add_to_line("".join(list_particles))
        return
    builder.newline()
    for member in list_particles:
        if config.one_per_line:
            builder.newline()
        builder.add_to_line(member)


def particles_in_lines(
    particles: List[Union[str, ParticleList]], config: ParticleFormattingConfig
) -> str:
    """
    Receives a list 'particles' that contains strings and particle sublists and generates lines
    according to the following rules:

    When one_item_per_line ContextVar is False:
        - The first line is not indented. All other lines start with 'line_indent' spaces.
        - A line containing more than one particle can be no longer than 'allowed_line_length'.
        - A sublist that cannot be fully concatenated to the current line opens a new line (see
        add_list_old_format).

    When one_item_per_line ContextVar is True:
        - The first line is not indented. Other lines start with 'line_indent' spaces. Lines
        that contruct sublists are indented as described in add_list_new_format.
        - A line containing more than one particle can be no longer than 'allowed_line_length'.
        - A sublist that cannot be fully concatenated to the current line opens a new line (see
        add_list_new_format).

    Usage example:
        particles_in_lines(
            ['func f(',
            ParticleList(elements=['x', 'y', 'z'], end=') -> ('),
            ParticleList(elements=['a', 'b', 'c'], end='):')],
            12, 4)
    """

    if config.double_indentation and not one_item_per_line_ctx_var.get():
        config = dataclasses.replace(
            config, line_indent=2 * config.line_indent, double_indentation=False
        )

    builder = ParticleLineBuilder(config=config)

    for particle in particles:
        if isinstance(particle, str):
            builder.add_to_line(particle)

        if isinstance(particle, ParticleList):
            if one_item_per_line_ctx_var.get():
                add_list_new_format(builder, particle)
            else:
                add_list_old_format(builder, particle, config)

    return builder.finalize()
