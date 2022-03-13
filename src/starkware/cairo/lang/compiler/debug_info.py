import dataclasses
from dataclasses import field
from typing import Dict, List, Optional

import marshmallow.fields as mfields
import marshmallow_dataclass

from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.preprocessor.flow import FlowTrackingDataActual
from starkware.cairo.lang.compiler.scoped_name import ScopedName, ScopedNameAsStr
from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass


@dataclasses.dataclass
class HintLocation:
    location: Location
    # The number of new lines following the "%{" symbol.
    n_prefix_newlines: int


@dataclasses.dataclass
class InstructionLocation:
    inst: Location
    hints: List[Optional[HintLocation]]
    accessible_scopes: List[ScopedName] = field(
        metadata=dict(marshmallow_field=mfields.List(ScopedNameAsStr))
    )

    flow_tracking_data: FlowTrackingDataActual

    def get_all_locations(self) -> List[Location]:
        all_locations = [self.inst] + self.inst.get_parent_locations()
        for hint_location in self.hints:
            if hint_location is None:
                continue

            all_locations.append(hint_location.location)
            all_locations.extend(hint_location.location.get_parent_locations())

        return all_locations


@marshmallow_dataclass.dataclass(frozen=True)
class DebugInfo(ValidatedMarshmallowDataclass):
    # A map from (relative) PC to the location of the instruction.
    instruction_locations: Dict[int, InstructionLocation]
    # A partial map from file name to its content. Files that are not in the map, are assumed to
    # exist in the file system.
    file_contents: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()

        # Load InputFile.content from file_contents where it exists.
        for instruction_location in self.instruction_locations.values():
            for loc in instruction_location.get_all_locations():
                input_file = loc.input_file
                if input_file.filename in self.file_contents and input_file.content is None:
                    input_file.content = self.file_contents[input_file.filename]

    def add_autogen_file_contents(self):
        """
        Updates file_contents with the contents of the auto-generated files.
        """
        for instruction_location in self.instruction_locations.values():
            for loc in instruction_location.get_all_locations():
                input_file = loc.input_file
                is_autogen = (
                    input_file.filename is not None
                    and input_file.filename.startswith("autogen/")
                    and input_file.content is not None
                )
                if not is_autogen:
                    continue

                # The following asserts are for mypy.
                assert input_file.filename is not None
                assert input_file.content is not None

                if input_file.filename in self.file_contents:
                    assert self.file_contents[input_file.filename] == input_file.content, (
                        f'Found two versions of auto-generated file "{input_file.filename}":\n'
                        f"{input_file.content}\n\n\n{self.file_contents[input_file.filename]}"
                    )
                else:
                    self.file_contents[input_file.filename] = input_file.content
