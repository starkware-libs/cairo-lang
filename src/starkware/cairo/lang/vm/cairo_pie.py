"""
A CairoPie represents a position independent execution of a Cairo program.
"""

import copy
import dataclasses
import io
import json
import math
import zipfile
from dataclasses import field
from typing import Any, ClassVar, Dict, List, Type

import marshmallow
import marshmallow.fields as mfields
import marshmallow_dataclass

from starkware.cairo.lang.compiler.program import StrippedProgram, is_valid_builtin_name
from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.relocatable import RelocatableValue
from starkware.python.utils import add_counters, sub_counters


@dataclasses.dataclass
class SegmentInfo:
    """
    Segment index and size.
    """

    index: int
    size: int

    def run_validity_checks(self):
        assert isinstance(self.index, int) and 0 <= self.index < 2 ** 30, 'Invalid segment index.'
        assert isinstance(self.size, int) and 0 <= self.size < 2 ** 30, 'Invalid segment size.'


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

    def all_segments(self) -> List[SegmentInfo]:
        """
        Returns a list of all the segments.
        """
        return [
            self.program_segment,
            self.execution_segment,
            self.ret_fp_segment,
            self.ret_pc_segment,
            *self.builtin_segments.values(),
            *self.extra_segments,
        ]

    def segment_sizes(self) -> Dict[int, int]:
        """
        Returns a map from segment index to its size.
        """
        return {segment.index: segment.size for segment in self.all_segments()}

    def run_validity_checks(self):
        self.program.run_validity_checks()
        assert isinstance(self.builtin_segments, dict) and all(
            is_valid_builtin_name(name) for name in self.builtin_segments.keys()), \
            'Invalid builtin_segments.'
        assert isinstance(self.extra_segments, list), 'Invalid type for extra_segments.'

        for segment_info in self.all_segments():
            assert isinstance(segment_info, SegmentInfo), 'Invalid type for segment_info.'
            segment_info.run_validity_checks()

        assert self.program_segment.size == len(self.program.data), \
            'Program length does not match the program segment size.'
        assert self.program.builtins == list(self.builtin_segments.keys()), \
            'Builtin list mismatch in builtin_segments.'
        assert self.ret_fp_segment.size == 0, 'Invalid segment size for ret_fp. Must be 0.'
        assert self.ret_pc_segment.size == 0, 'Invalid segment size for ret_pc. Must be 0.'

        self.validate_segment_order()


@marshmallow_dataclass.dataclass
class ExecutionResources:
    """
    Indicates how many steps the program should run, how many memory cells are used from each
    builtin, and how many holes there are in the memory address space.
    """
    n_steps: int
    builtin_instance_counter: Dict[str, int]
    n_memory_holes: int = field(
        metadata=dict(marshmallow_field=mfields.Integer(missing=0)))
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema

    def run_validity_checks(self):
        assert isinstance(self.n_steps, int) and 1 <= self.n_steps < 2 ** 30, \
            f'Invalid n_steps: {self.n_steps}.'
        assert isinstance(self.n_memory_holes, int) and 0 <= self.n_memory_holes < 2 ** 30, \
            f'Invalid n_memory_holes: {self.n_memory_holes}.'
        assert isinstance(self.builtin_instance_counter, dict) and all(
            is_valid_builtin_name(name) and isinstance(size, int) and 0 <= size < 2 ** 30
            for name, size in self.builtin_instance_counter.items()), \
            'Invalid builtin_instance_counter.'

    def __add__(self, other: 'ExecutionResources') -> 'ExecutionResources':
        total_builtin_instance_counter = add_counters(
            self.builtin_instance_counter, other.builtin_instance_counter)

        return ExecutionResources(
            n_steps=self.n_steps + other.n_steps,
            builtin_instance_counter=total_builtin_instance_counter,
            n_memory_holes=self.n_memory_holes + other.n_memory_holes)

    def __sub__(self, other: 'ExecutionResources') -> 'ExecutionResources':
        diff_builtin_instance_counter = sub_counters(
            self.builtin_instance_counter, other.builtin_instance_counter)
        diff_execution_resources = ExecutionResources(
            n_steps=self.n_steps - other.n_steps,
            builtin_instance_counter=diff_builtin_instance_counter,
            n_memory_holes=self.n_memory_holes - other.n_memory_holes)
        diff_execution_resources.run_validity_checks()

        return diff_execution_resources

    @classmethod
    def empty(cls):
        return cls(n_steps=0, builtin_instance_counter={}, n_memory_holes=0)

    def copy(self) -> 'ExecutionResources':
        return copy.deepcopy(self)


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
    ALL_FILES = [
        METADATA_FILENAME,
        MEMORY_FILENAME,
        ADDITIONAL_DATA_FILENAME,
        EXECUTION_RESOURCES_FILENAME,
    ]
    MAX_SIZE = 1024 ** 3

    @classmethod
    def from_file(cls, fileobj) -> 'CairoPie':
        """
        Loads an instance of CairoPie from a file.
        `fileobj` can be a path or a file object.
        """

        if isinstance(fileobj, str):
            fileobj = open(fileobj, 'rb')

        verify_zip_file_prefix(fileobj=fileobj)

        with zipfile.ZipFile(fileobj) as zf:
            cls.verify_zip_format(zf)

            with zf.open(cls.METADATA_FILENAME, 'r') as fp:
                metadata = CairoPieMetadata.Schema().load(
                    json.loads(fp.read(cls.MAX_SIZE).decode('ascii')))
            with zf.open(cls.MEMORY_FILENAME, 'r') as fp:
                memory = MemoryDict.deserialize(
                    data=fp.read(cls.MAX_SIZE),
                    field_bytes=metadata.field_bytes,
                )
            with zf.open(cls.ADDITIONAL_DATA_FILENAME, 'r') as fp:
                additional_data = json.loads(fp.read(cls.MAX_SIZE).decode('ascii'))
            with zf.open(cls.EXECUTION_RESOURCES_FILENAME, 'r') as fp:
                execution_resources = ExecutionResources.Schema().load(
                    json.loads(fp.read(cls.MAX_SIZE).decode('ascii')))
        return cls(metadata, memory, additional_data, execution_resources)

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
    def deserialize(cls, cairo_pie_bytes: bytes) -> 'CairoPie':
        cairo_pie_file = io.BytesIO()
        cairo_pie_file.write(cairo_pie_bytes)
        return CairoPie.from_file(fileobj=cairo_pie_file)

    def serialize(self) -> bytes:
        cairo_pie_file = io.BytesIO()
        self.to_file(file=cairo_pie_file)
        return cairo_pie_file.getvalue()

    @property
    def program(self) -> StrippedProgram:
        return self.metadata.program

    def run_validity_checks(self):
        self.metadata.run_validity_checks()
        self.execution_resources.run_validity_checks()

        assert isinstance(self.memory, MemoryDict), 'Invalid type for memory.'
        self.run_memory_validity_checks()

        assert sorted(f'{name}_builtin' for name in self.metadata.program.builtins) == sorted(
            self.execution_resources.builtin_instance_counter.keys()), \
            'Builtin list mismatch in execution_resources.'

        assert isinstance(self.additional_data, dict) and all(
            isinstance(name, str) and len(name) < 1000 for name in self.additional_data), \
            'Invalid additional_data.'

    def run_memory_validity_checks(self):
        segment_sizes = self.metadata.segment_sizes()

        def is_valid_memory_addr(addr, allow_end_of_segment: bool = False):
            """
            Returns True if addr is a relocatable value, such that its segment index appears in
            segment_sizes and its offset is in the valid range (if allow_end_of_segment=True, offset
            may refer to the next cell *after* the segment).
            """
            return isinstance(addr, RelocatableValue) and \
                isinstance(addr.segment_index, int) and \
                isinstance(addr.offset, int) and \
                addr.segment_index in segment_sizes and \
                0 <= addr.offset < segment_sizes[addr.segment_index] + (
                    1 if allow_end_of_segment else 0)

        def is_valid_memory_value(value):
            return isinstance(value, int) or is_valid_memory_addr(value, allow_end_of_segment=True)

        for addr, value in self.memory.items():
            assert is_valid_memory_addr(addr), 'Invalid memory cell address.'
            assert is_valid_memory_value(value), f'Invalid memory cell value.'

    @classmethod
    def verify_zip_format(cls, zf: zipfile.ZipFile):
        """
        Checks that the given zip file contains the expected inner files, that the compression
        type is ZIP_DEFLATED and that their size is not too big.
        """
        # Check the compression algorithm.
        assert all(zip_info.compress_type == zipfile.ZIP_DEFLATED for zip_info in zf.filelist), \
            'Invalid compress type.'

        # Check that orig_filename == filename.
        # Use "type: ignore" since mypy doesn't recognize ZipInfo.orig_filename.
        assert all(
            zip_info.orig_filename == zip_info.filename  # type: ignore
            for zip_info in zf.filelist), 'File name mismatch.'

        # Make sure we have exactly the files we expect, and that their size is reasonable.
        inner_files = {zip_info.filename: zip_info for zip_info in zf.filelist}
        assert sorted(inner_files.keys()) == sorted(cls.ALL_FILES), \
            'Invalid list of inner files in the CairoPIE zip.'
        assert inner_files[cls.METADATA_FILENAME].file_size < cls.MAX_SIZE, \
            f'Invalid file size for {cls.METADATA_FILENAME}.'
        assert inner_files[cls.MEMORY_FILENAME].file_size < cls.MAX_SIZE, \
            f'Invalid file size for {cls.MEMORY_FILENAME}.'
        assert inner_files[cls.ADDITIONAL_DATA_FILENAME].file_size < cls.MAX_SIZE, \
            f'Invalid file size for {cls.ADDITIONAL_DATA_FILENAME}.'
        assert inner_files[cls.EXECUTION_RESOURCES_FILENAME].file_size < 10000, \
            f'Invalid file size for {cls.EXECUTION_RESOURCES_FILENAME}.'

    def get_segment(self, segment_info: SegmentInfo):
        return self.memory.get_range(
            RelocatableValue(segment_index=segment_info.index, offset=0), size=segment_info.size)


def verify_zip_file_prefix(fileobj):
    """
    Verifies that the file starts with the zip file prefix.
    """
    fileobj.seek(0)
    # Make sure this is a zip file.
    assert fileobj.read(2) in ['PK', b'PK'], 'Invalid prefix for zip file.'
