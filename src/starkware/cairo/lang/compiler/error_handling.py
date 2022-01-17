import dataclasses
from dataclasses import field
from typing import List, Optional, Tuple

from marshmallow import post_dump


@dataclasses.dataclass
class InputFile:
    filename: Optional[str]
    content: Optional[str] = field(metadata=dict(load_only=True))

    def get_content(self) -> str:
        """
        Returns the file's content.
        If the content member is not set, it will be updated.
        """
        if self.content is None:
            assert self.filename is not None, "Content must be set if filename is None."
            self.content = open(self.filename, "r").read()

        return self.content


ParentLocation = Tuple["Location", str]


@dataclasses.dataclass(frozen=True)
class Location:
    start_line: int
    start_col: int
    end_line: int
    end_col: int
    input_file: InputFile
    # When the current location points to a reference definition due to reference expansion,
    # parent_location contains the location of the reference usage, and a message indicating the
    # expansion type, such as "While expanding the reference 'x'...".
    parent_location: Optional[ParentLocation] = None

    def with_parent_location(self, new_parent_location: "Location", message: str):
        if self.parent_location is None:
            return dataclasses.replace(self, parent_location=(new_parent_location, message))
        else:
            old_self_parent_location, self_parent_location_message = self.parent_location
            new_self_parent_location = old_self_parent_location.with_parent_location(
                new_parent_location, message
            )
            return dataclasses.replace(
                self, parent_location=(new_self_parent_location, self_parent_location_message)
            )

    def topmost_location(self):
        """
        Returns the location of the topmost parent.
        """
        location = self
        while location.parent_location is not None:
            location = location.parent_location[0]
        return location

    @post_dump
    def remove_none_values(self, data, many=False):
        return {key: value for key, value in data.items() if value is not None}

    def to_string(self, message: str = ""):
        """
        Prints the location with the passed message.
        """
        input_file = self.input_file
        line = self.start_line
        col = self.start_col
        filename = "" if input_file.filename is None else input_file.filename
        message_prefix = ": " if len(message) > 0 else ""
        return f"{filename}:{line}:{col}{message_prefix}{message}"

    def to_string_with_content(self, message: str = ""):
        """
        Prints the location with the passed message, including the content of the line and the
        location marks.
        """
        first_line = self.to_string(message=message)
        try:
            content = self.input_file.get_content()
        except FileNotFoundError:
            return first_line
        return first_line + "\n" + get_location_marks(content, self)

    def __repr__(self):
        return self.to_string()

    def get_parent_locations(self):
        parent_locations = []
        parent_location = self.parent_location
        while parent_location is not None:
            parent_locations.append(parent_location[0])
            parent_location = parent_location[0].parent_location

        return parent_locations


def get_location_marks(content: str, location: Location):
    lines = content.splitlines()

    if not (0 <= location.start_line - 1 < len(lines)):
        # The location does not refer to a valid location in the source file. This may happen when
        # the file is changed after compilation.
        # Don't return location marks in this case.
        return ""

    start_line = lines[location.start_line - 1]
    start_col = location.start_col
    res = start_line + "\n"
    end_col = location.end_col if location.start_line == location.end_line else len(start_line) + 1
    if end_col > start_col + 1:
        res += " " * (start_col - 1) + "^" + "*" * (end_col - start_col - 2) + "^"
    else:
        res += " " * (start_col - 1) + "^"
    return res


class LocationError(Exception):
    """
    Represents an error which refers to a specific location (line, column) in a file.
    """

    def __init__(
        self,
        message,
        location: Optional[Location] = None,
        error_attr_value: Optional[str] = None,
        traceback: Optional[str] = None,
        notes: Optional[List[str]] = None,
    ):
        """
        Constructs an exception with (an optional) location information.

        error_attr_value - an optional error attribute value. If given, it must end with a newline.
        """
        super().__init__(message, location)
        self.message = message
        self.error_attr_value = error_attr_value
        self.location = location
        self.traceback = traceback
        self.notes: List[str] = [] if notes is None else notes

    def __str__(self):
        res = ""

        # Add error message.
        if self.error_attr_value is not None:
            res += self.error_attr_value

        # Add location.
        if self.location is None:
            res += self.message + "\n"
        else:
            location_str = ""
            location, message = self.location, self.message
            while True:
                location_str = location.to_string_with_content(message) + "\n" + location_str
                if location.parent_location is None:
                    break
                location, message = location.parent_location
            res += location_str

        # Add traceback.
        if self.traceback is not None:
            res += self.traceback + "\n"

        # Add notes.
        for note in self.notes:
            res += note + "\n"

        return res.rstrip()
