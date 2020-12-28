import dataclasses
from typing import List, Optional, Sequence

from starkware.cairo.lang.compiler.ast.formatting_utils import LocationField
from starkware.cairo.lang.compiler.ast.node import AstNode
from starkware.cairo.lang.compiler.ast.notes import NoteListField, Notes
from starkware.cairo.lang.compiler.ast.types import TypedIdentifier
from starkware.cairo.lang.compiler.error_handling import Location


@dataclasses.dataclass
class IdentifierList(AstNode):
    identifiers: List[TypedIdentifier]
    notes: List[Notes] = NoteListField  # type: ignore
    location: Optional[Location] = LocationField

    def get_particles(self):
        for note in self.notes:
            note.assert_no_comments()
        return [x.format() for x in self.identifiers]

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return self.identifiers
