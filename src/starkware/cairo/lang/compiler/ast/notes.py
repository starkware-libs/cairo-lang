import dataclasses
from dataclasses import field
from typing import List, Optional

from starkware.cairo.lang.compiler.ast.formatting_utils import FormattingError, LocationField
from starkware.cairo.lang.compiler.error_handling import Location

NotesField = field(default_factory=lambda: Notes(), hash=False, compare=False)
NoteListField = field(default_factory=list, hash=False, compare=False)


@dataclasses.dataclass
class Notes:
    """
    Represents new-lines and comments that appear inside an expression or other code element.
    For example, in the following code the first comment is represented by a note and the
    second is represented in the CommentedCodeElement:

      assert a = b +  # Hello.
          c + d  # World.
    """
    # The comments of the note. If empty, the value of starts_new_line is ignored.
    comments: List[str] = field(default_factory=list)
    # Whether the note starts on its own line.
    starts_new_line: bool = False
    location: Optional[Location] = LocationField

    @property
    def empty(self):
        return len(self.comments) == 0 and not self.starts_new_line

    def assert_no_comments(self):
        if len(self.comments) == 0:
            return
        raise FormattingError(
            'Comments inside expressions are not supported by the auto-formatter.',
            location=self.location)

    def __add__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        if self.empty:
            return other
        return Notes(
            comments=self.comments + other.comments,
            starts_new_line=self.starts_new_line,
            location=self.location)

    def format(self):
        code = ''
        if self.starts_new_line:
            code += '\n'
        elif len(self.comments) > 0:
            code += '  '
        for comment in self.comments:
            assert comment.startswith('#')
            comment_body = comment[1:].strip()
            if comment_body != '':
                comment_body = ' ' + comment_body
            code += f'#{comment_body}\n'
        return code
