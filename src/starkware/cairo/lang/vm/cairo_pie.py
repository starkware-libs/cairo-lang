"""
A CairoPie represents a position independent execution of a Cairo program.
"""

import dataclasses
import io
import json
import math
import zipfile
from typing import Any, ClassVar, Dict, List, Type

import marshmallow
import marshmallow_dataclass

from starkware.cairo.lang.compiler.program import StrippedProgram
from starkware.cairo.lang.vm.memory_dict import MemoryDict


@dataclasses.dataclass
class SegmentInfo:
    """
    Segment index and size.
    """

    index: int
    size: int


@marshmallow_dataclass.dataclass
class CairoPieMetadata:
    """
    Metadata of a PIE output.
    """

    program: StrippedProgram
    program_segment: SegmentInfo
    execution_segment: SegmentInfo
    ret_fp_segment: SegmentInfo
    ret_pc_segment: SegmentInfo
    builtin_segments: Dict[str, SegmentInfo]
    extra_segments: List[SegmentInfo]
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema

    @property
    def field_bytes(self) -> int:
        return math.ceil(self.program.prime.bit_length() / 8)

    def validate_segment_order(self):
        assert self.program_segment.index == 0, 'Invalid segment index for program_segment.'
        assert self.execution_segment.index == 1, 'Invalid segment index for execution_segment.'
        for expected_segment, (name, builtin_segment) in enumerate(
                self.builtin_segments.items(), 2):
            assert builtin_segment.index == expected_segment, f'Invalid segment index for {name}.'
        n_builtins = len(self.builtin_segments)
        assert self.ret_fp_segment.index == n_builtins + 2, \
            f'Invalid segment index for ret_fp_segment. {self.ret_fp_segment.index}'
        assert self.ret_pc_segment.index == n_builtins + 3, \
            'Invalid segment index for ret_pc_segment.'
        for expected_segment, segment in enumerate(
                self.extra_segments, n_builtins + 4):
            assert segment.index == expected_segment, 'Invalid segment indices for extra_segments.'


@marshmallow_dataclass.dataclass
class ExecutionResources:
    """
    Indicates how many steps the program should run and how many memory cells are used from each
    builtin.
    """
    n_steps: int
    builtin_cell_counter: Dict[str, int]
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema


@dataclasses.dataclass
class CairoPie:
    """
    A CairoPie is a serializable object containing information about a run of a cairo program.
    Using the information, one can 'relocate' segments of the run, to make another valid cairo run.
    For example, this may be used to join a few cairo runs into one, by concatenating respective
    segments.
    """
    metadata: CairoPieMetadata
    memory: MemoryDict
    additional_data: Dict[str, Any]
    execution_resources: ExecutionResources

    METADATA_FILENAME = 'metadata.json'
    MEMORY_FILENAME = 'memory.bin'
    ADDITIONAL_DATA_FILENAME = 'additional_data.json'
    EXECUTION_RESOURCES_FILENAME = 'execution_resources.json'

    @classmethod
    def from_file(cls, file) -> 'CairoPie':
        """
        Loads an instance of CairoPie from a file.
        file can be a path or a file object.
        """
        with zipfile.ZipFile(file) as zf:
            with zf.open(cls.METADATA_FILENAME, 'r') as fp:
                metadata = CairoPieMetadata.Schema().load(
                    json.loads(fp.read().decode('ascii')))
            with zf.open(cls.MEMORY_FILENAME, 'r') as fp:
                memory = MemoryDict.deserialize(
                    data=fp.read(),
                    field_bytes=metadata.field_bytes,
                )
            with zf.open(cls.ADDITIONAL_DATA_FILENAME, 'r') as fp:
                additional_data = json.loads(fp.read().decode('ascii'))
            with zf.open(cls.EXECUTION_RESOURCES_FILENAME, 'r') as fp:
                execution_resources = ExecutionResources.Schema().load(
                    json.loads(fp.read().decode('ascii')))
        return CairoPie(metadata, memory, additional_data, execution_resources)

    def to_file(self, file):
        with zipfile.ZipFile(file, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            with zf.open(self.METADATA_FILENAME, 'w') as fp:
                fp.write(json.dumps(
                    CairoPieMetadata.Schema().dump(self.metadata)).encode('ascii'))
            with zf.open(self.MEMORY_FILENAME, 'w') as fp:
                fp.write(self.memory.serialize(self.metadata.field_bytes))
            with zf.open(self.ADDITIONAL_DATA_FILENAME, 'w') as fp:
                fp.write(json.dumps(self.additional_data).encode('ascii'))
            with zf.open(self.EXECUTION_RESOURCES_FILENAME, 'w') as fp:
                fp.write(json.dumps(
                    ExecutionResources.Schema().dump(self.execution_resources)).encode('ascii'))

    @classmethod
    def deserialize(cls, bytes) -> 'CairoPie':
        cairo_pie_file = io.BytesIO()
        cairo_pie_file.write(bytes)
        return CairoPie.from_file(file=cairo_pie_file)

    def serialize(self) -> bytes:
        cairo_pie_file = io.BytesIO()
        self.to_file(file=cairo_pie_file)
        return cairo_pie_file.getvalue()

    @property
    def program(self) -> StrippedProgram:
        return self.metadata.program
