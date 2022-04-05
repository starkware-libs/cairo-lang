"""
Contains utils that help with formatting of Cairo code.
"""

import dataclasses
from abc import ABC, abstractmethod
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
one_item_per_line_ctx_var: ContextVar[bool] = ContextVar("one_item_per_line", default=True)


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
    # Force one item per line, even if the entire list fits into a single new line.
    # If the list fits into the current line, it will still be concatenated to it.
    # Note: if the one_item_per_line ContextVar is False, this field is ignored.
    force_one_per_line: bool = False
    # If True, line_indent is doubled.
    # Note: if the one_item_per_line ContextVar is True, this field is ignored.
    double_indentation: bool = False


class ParticleLineBuilder:
    """
    Builds particle lines, wrapping line lengths as needed.
    """

    def __init__(self, config: ParticleFormattingConfig):
        self.lines: List[str] = []
        self.line = config.first_line_prefix
        self.line_is_new = True
        self.line_indent_stack = [0]
        self.current_line_indent = 0

        self.config = config

    def push_indentation(self):
        """
        Saves the current line indentation into self.line_indent stack.
        New indented lines will be indented relatively to the current line indentation.
        """
        self.line_indent_stack.append(self.current_line_indent)

    def pop_indentation(self):
        """
        Pops the latest line indentation from self.line_indent_stack.
        New indented lines will be indented relatively to the previous line indentation in the
        stack.
        """
        assert len(self.line_indent_stack) > 1
        self.line_indent_stack.pop()

    def newline(self, indent: bool = True):
        """
        Opens a new line.
        """
        if self.line_is_new:
            return
        self.lines.append(self.line)
        self.line_is_new = True
        self.current_line_indent = self.line_indent_stack[-1] + (
            self.config.line_indent if indent else 0
        )
        self.line = " " * self.current_line_indent

    def add_to_line(self, string):
        """
        Adds to current line, opening a new one if needed.
        """
        if string == "":
            return
        if not self.can_fit_in_line(string) and not self.line_is_new:
            self.newline()
        self.line += string
        self.line_is_new = False

    def can_fit_in_line(self, string: str) -> bool:
        """
        Returns True if the given string can fit in the current line.
        """
        return len(self.line) + len(string.rstrip()) <= self.config.allowed_line_length

    def finalize(self):
        """
        Finalizes the particle lines and returns the result.
        """
        if self.line:
            self.lines.append(self.line)
        return "\n".join(line.rstrip() for line in self.lines)


class Particle(ABC):
    """
    An interface for particles.
    """

    @abstractmethod
    def __str__(self):
        pass

    @abstractmethod
    def is_splitable(self) -> bool:
        """
        Returns True if and only if the particle can be split into multiple lines.
        """

    @abstractmethod
    def add_to_builder(self, builder: ParticleLineBuilder, suffix: str = ""):
        """
        Adds the particle to a builder, according to the formatting configuration of the builder.
        suffix is concatanated to the end of the particle.
        """


@dataclasses.dataclass()
class SingleParticle(Particle):
    """
    A particle of a single expression, that cannot be split into multiple lines.
    """

    text: str

    def __str__(self):
        return self.text

    def is_splitable(self) -> bool:
        return False

    def add_to_builder(self, builder: ParticleLineBuilder, suffix: str = ""):
        builder.add_to_line(f"{self.text}{suffix}")


@dataclasses.dataclass()
class ParticleList(Particle):
    """
    A list of particles, that should be concatenated one after the other.
    """

    def __init__(
        self,
        elements: List[Union[Particle, str]],
    ):
        self.elements = []
        for elm in elements:
            self.elements.append(SingleParticle(text=elm) if isinstance(elm, str) else elm)

    def __str__(self):
        return "".join([str(elm) for elm in self.elements])

    def is_splitable(self) -> bool:
        return len(self.elements) > 0

    def add_to_builder(self, builder: ParticleLineBuilder, suffix: str = ""):
        for i, particle in enumerate(self.elements):
            particle.add_to_builder(
                builder=builder, suffix=suffix if i == len(self.elements) - 1 else ""
            )


@dataclasses.dataclass()
class SeparatedParticleList(Particle):
    """
    A list of particles, separated by separator (e.g. comma separated argument list).
    """

    def __init__(
        self,
        elements: List[Union[Particle, str]],
        separator: str = ", ",
        start: str = "",
        end: str = "",
    ):
        self.elements = []
        for elm in elements:
            self.elements.append(SingleParticle(text=elm) if isinstance(elm, str) else elm)
        self.separator = separator
        self.start = start
        self.end = end

    def __str__(self):
        return self.start + self.elements_to_string() + self.end

    def is_splitable(self) -> bool:
        return len(self.elements) > 0

    def to_strings(self) -> List[str]:
        if len(self.elements) == 0:
            # If the list is empty, return the single element 'end'.
            return [self.end]
        # Concatenate the 'separator' to all elements and 'end' to the last one.
        return [str(elm) + self.separator for elm in self.elements[:-1]] + [
            str(self.elements[-1]) + self.end
        ]

    def elements_to_string(self) -> str:
        """
        Returns a concatenation of the strings in self.elements, separated with self.separator.
        """
        return self.separator.join(str(elm) for elm in self.elements)

    def add_to_builder(self, builder: ParticleLineBuilder, suffix: str = ""):
        """
        Adds a particle list to the current line builder.
        If the list cannot be fully concatenated to the current line opens a new line, and puts the
        elements as described in self.add_elements_*().
        """

        # If the entire list fits in the current line, or the list is empty, add everything to the
        # current line.
        particle_list_str = f"{self}{suffix}"
        if builder.can_fit_in_line(particle_list_str) or len(self.elements) == 0:
            builder.add_to_line(particle_list_str)
            return

        builder.newline()
        builder.add_to_line(self.start)

        if one_item_per_line_ctx_var.get():
            self.add_elements_one_per_line(builder=builder, suffix=suffix)
        else:
            self.add_elements_indent_new_lines(
                builder=builder, suffix=suffix, one_per_line=builder.config.one_per_line
            )

    def add_elements_one_per_line(self, builder: ParticleLineBuilder, suffix: str):
        """
        Adds each element in a separate line, indented by 'INDENTATION' characters.

        For example, using this function to format a list of arguments may result in the following
        formatting:
            func f(
                x,
                y,
                z,
            ) -> (
                a,
                b,
                c,
            ):
        """
        # If the entire list fits in a new line, add it.
        # Else, add each element of the list in a separate line.
        builder.newline()
        elements_string = self.elements_to_string()
        if not builder.config.force_one_per_line and builder.can_fit_in_line(elements_string):
            builder.add_to_line(elements_string)
        else:
            for particle in self.elements:
                builder.newline()
                builder.push_indentation()
                particle.add_to_builder(builder=builder, suffix=self.separator)
                builder.pop_indentation()

        builder.newline(indent=False)
        builder.add_to_line(f"{self.end}{suffix}")

    def add_elements_indent_new_lines(
        self, builder: ParticleLineBuilder, suffix: str, one_per_line: bool
    ):
        """
        Adds each element to the current line if possible, otherwise opens a new line.
        If one_per_line is True put each element in a separate line, without trailing separator
        (unlike add_elements_one_per_line).

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
        # If the entire list fits in the current line, add it.
        elements_string = f"{self.elements_to_string()}{self.end}{suffix}"
        if len(elements_string) + len(builder.line) < builder.config.allowed_line_length:
            builder.add_to_line(elements_string)
            return

        for i, particle in enumerate(self.elements):
            if one_per_line:
                builder.newline()
            particle_suffix = (
                f"{self.end}{suffix}" if i == len(self.elements) - 1 else self.separator
            )
            start_new_line = particle.is_splitable() and not builder.can_fit_in_line(
                f"{particle}{particle_suffix}"
            )
            if start_new_line:
                builder.newline()
                builder.push_indentation()
            particle.add_to_builder(builder=builder, suffix=particle_suffix)
            if start_new_line:
                builder.pop_indentation()


def particles_in_lines(particles: Particle, config: ParticleFormattingConfig) -> str:
    """
    Receives a Particle and generates lines according to the following rules:

    When one_item_per_line ContextVar is False:
        - The first line is not indented. All other lines start with 'line_indent' spaces.
        - A line containing more than one particle can be no longer than 'allowed_line_length'.
        - A sublist that cannot be fully concatenated to the current line opens a new line (see
        add_list_old_format).

    When one_item_per_line ContextVar is True:
        - The first line is not indented. Other lines start with 'line_indent' spaces. Lines
        that construct sublists are indented as described in add_list_new_format.
        - A line containing more than one particle can be no longer than 'allowed_line_length'.
        - A sublist that cannot be fully concatenated to the current line opens a new line (see
        add_list_new_format).

    Usage example:
        particles_in_lines(
            ParticleList(elements=[
                'func f(',
                SeparatedParticleList(elements=['x', 'y', 'z'], end=') -> ('),
                SeparatedParticleList(elements=['a', 'b', 'c'], end='):')]),
            12, 4)
    """

    if config.double_indentation and not one_item_per_line_ctx_var.get():
        config = dataclasses.replace(
            config, line_indent=2 * config.line_indent, double_indentation=False
        )

    builder = ParticleLineBuilder(config=config)
    particles.add_to_builder(builder)
    return builder.finalize()
