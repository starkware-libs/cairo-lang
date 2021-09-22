from typing import Optional

import pytest

from starkware.cairo.lang.compiler.debug_info import DebugInfo, InstructionLocation
from starkware.cairo.lang.compiler.error_handling import InputFile, Location
from starkware.cairo.lang.compiler.preprocessor.flow import FlowTrackingDataActual


def dummy_instruction_location(filename: str, content: Optional[str]) -> InstructionLocation:
    location = Location(
        start_line=1,
        start_col=2,
        end_line=3,
        end_col=4,
        input_file=InputFile(filename=filename, content=content),
    )
    return InstructionLocation(
        inst=location,
        hints=[],
        accessible_scopes=[],
        flow_tracking_data=FlowTrackingDataActual.new(lambda: 0),
    )


def test_autogen_files():
    inst_location0 = dummy_instruction_location("autogen/1", "content 1")
    inst_location1 = dummy_instruction_location("not/autogen/2", "content 2")
    inst_location2 = dummy_instruction_location("autogen/3", None)
    debug_info = DebugInfo(
        instruction_locations={0: inst_location0, 1: inst_location1, 2: inst_location2}
    )
    debug_info.add_autogen_file_contents()
    assert debug_info.file_contents == {"autogen/1": "content 1"}

    # Create a location to the same file name, with a different content.
    mismatch_location = dummy_instruction_location("autogen/1", "a different content")
    debug_info = DebugInfo(instruction_locations={0: inst_location0, 1: mismatch_location})
    with pytest.raises(
        AssertionError, match='Found two versions of auto-generated file "autogen/1"'
    ):
        debug_info.add_autogen_file_contents()
