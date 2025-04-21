"""
A CairoPie represents a position independent execution of a Cairo program.
"""

import contextlib
import copy
import dataclasses
import functools
import io
import json
import math
import zipfile
from abc import ABC
from dataclasses import field
from typing import Any, ClassVar, Dict, List, Mapping, Optional, Tuple, Type

import marshmallow
import marshmallow.fields as mfields
import marshmallow_dataclass
from marshmallow_oneofschema.one_of_schema import OneOfSchema

from starkware.cairo.lang.builtins.all_builtins import (
    ALL_BUILTINS,
    BUILTIN_NAME_SUFFIX,
    remove_builtin_suffix,
)
from starkware.cairo.lang.compiler.program import (
    StrippedProgram,
    is_valid_builtin_name,
    is_valid_opcode_name,
)
from starkware.cairo.lang.vm.memory_dict import MemoryDict, RelocateValueFunc
from starkware.cairo.lang.vm.memory_segments import is_valid_memory_addr, is_valid_memory_value
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue, relocate_value
from starkware.python.utils import add_counters, multiply_counter_by_scalar, sub_counters
from starkware.starkware_utils.marshmallow_dataclass_fields import additional_metadata
from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass

DEFAULT_CAIRO_PIE_VERSION = "1.0"
CURRENT_CAIRO_PIE_VERSION = "1.1"

MAX_N_STEPS = 2**30


@dataclasses.dataclass
class SegmentInfo:
    """
    Segment index and size.
    """

    index: int
    size: int

    def run_validity_checks(self):
        assert isinstance(self.index, int) and 0 <= self.index < 2**30, "Invalid segment index."
        assert isinstance(self.size, int) and 0 <= self.size < 2**30, "Invalid segment size."


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
        assert self.program_segment.index == 0, "Invalid segment index for program_segment."
        assert self.execution_segment.index == 1, "Invalid segment index for execution_segment."
        for expected_segment, (name, builtin_segment) in enumerate(
            self.builtin_segments.items(), 2
        ):
            assert builtin_segment.index == expected_segment, f"Invalid segment index for {name}."
        n_builtins = len(self.builtin_segments)
        assert (
            self.ret_fp_segment.index == n_builtins + 2
        ), f"Invalid segment index for ret_fp_segment. {self.ret_fp_segment.index}"
        assert (
            self.ret_pc_segment.index == n_builtins + 3
        ), "Invalid segment index for ret_pc_segment."
        for expected_segment, segment in enumerate(self.extra_segments, n_builtins + 4):
            assert segment.index == expected_segment, "Invalid segment indices for extra_segments."

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
            is_valid_builtin_name(name) for name in self.builtin_segments.keys()
        ), "Invalid builtin_segments."
        assert isinstance(self.extra_segments, list), "Invalid type for extra_segments."

        for segment_info in self.all_segments():
            assert isinstance(segment_info, SegmentInfo), "Invalid type for segment_info."
            segment_info.run_validity_checks()

        assert self.program_segment.size == len(
            self.program.data
        ), "Program length does not match the program segment size."
        assert self.program.builtins == list(self.builtin_segments.keys()), (
            f"Builtin list mismatch in builtin_segments. Builtins: {self.program.builtins}, "
            f"segment keys: {list(self.builtin_segments.keys())}."
        )
        assert self.ret_fp_segment.size == 0, "Invalid segment size for ret_fp. Must be 0."
        assert self.ret_pc_segment.size == 0, "Invalid segment size for ret_pc. Must be 0."

        self.validate_segment_order()


@marshmallow_dataclass.dataclass
class ExecutionResources(ValidatedMarshmallowDataclass, ABC):
    """
    Base class for Execution resources class.
    Indicates how many steps the program should run, how many memory cells are used from each
    builtin, and how many holes there are in the memory address space.
    """

    builtin_instance_counter: Dict[str, int]
    n_memory_holes: int = field(
        metadata=additional_metadata(marshmallow_field=mfields.Integer(load_default=0))
    )

    def run_validity_checks(self):
        assert isinstance(self.builtin_instance_counter, dict) and all(
            is_valid_builtin_name(name) and isinstance(size, int) and 0 <= size < 2**30
            for name, size in self.builtin_instance_counter.items()
        ), "Invalid builtin_instance_counter."
        assert (
            isinstance(self.n_memory_holes, int) and 0 <= self.n_memory_holes < 2**30
        ), f"Invalid n_memory_holes: {self.n_memory_holes}."

    def __add__(self, other: "ExecutionResources") -> "ExecutionResources":
        raise NotImplementedError(f"Should not be called from {self.__class__.__name__} class.")

    def __sub__(self, other: "ExecutionResources") -> "ExecutionResources":
        raise NotImplementedError(f"Should not be called from {self.__class__.__name__} class.")

    def __mul__(self, other: int) -> "ExecutionResources":
        raise NotImplementedError(f"Should not be called from {self.__class__.__name__} class.")

    def __rmul__(self, other: int) -> "ExecutionResources":
        raise NotImplementedError(f"Should not be called from {self.__class__.__name__} class.")

    def filter_unused_builtins(self) -> "ExecutionResources":
        """
        Returns a copy of the execution resources where all the builtins with a usage counter
        of 0 are omitted.
        """
        return dataclasses.replace(
            self,
            builtin_instance_counter={
                name: counter
                for name, counter in self.builtin_instance_counter.items()
                if counter > 0
            },
        )


@marshmallow_dataclass.dataclass
class ExecutionResourcesStone(ExecutionResources):
    """
    ExecutionResources class for Stone.
    """

    n_steps: int
    def run_validity_checks(self):
        super().run_validity_checks()
        assert (
            isinstance(self.n_steps, int) and 1 <= self.n_steps < MAX_N_STEPS
        ), f"Invalid n_steps: {self.n_steps}."

    def convert_to_stwo(self) -> "ExecutionResourcesStwo":
        """
        Returns a ExecutionResourcesStwo version of self.
        """
        return ExecutionResourcesStwo(
            builtin_instance_counter=self.builtin_instance_counter,
            n_memory_holes=self.n_memory_holes,
            opcodes_instance_counter={
                "generic_opcode": self.n_steps,
            },
            memory_tables_sizes={},
            n_verify_instructions=0,
        )

    def __add__(self, other: ExecutionResources) -> "ExecutionResourcesStone":
        assert isinstance(other, ExecutionResourcesStone), "Invalid type for other."
        total_builtin_instance_counter = add_counters(
            self.builtin_instance_counter, other.builtin_instance_counter
        )

        return ExecutionResourcesStone(
            n_steps=self.n_steps + other.n_steps,
            builtin_instance_counter=total_builtin_instance_counter,
            n_memory_holes=self.n_memory_holes + other.n_memory_holes,
        )

    def __sub__(self, other: ExecutionResources) -> "ExecutionResourcesStone":
        assert isinstance(other, ExecutionResourcesStone), "Invalid type for other."
        diff_builtin_instance_counter = sub_counters(
            self.builtin_instance_counter, other.builtin_instance_counter
        )
        return ExecutionResourcesStone(
            n_steps=self.n_steps - other.n_steps,
            builtin_instance_counter=diff_builtin_instance_counter,
            n_memory_holes=self.n_memory_holes - other.n_memory_holes,
        )

    def __mul__(self, other: int) -> "ExecutionResourcesStone":
        if not isinstance(other, int):
            return NotImplemented

        total_builtin_instance_counter = multiply_counter_by_scalar(
            scalar=other, counter=self.builtin_instance_counter
        )

        return ExecutionResourcesStone(
            n_steps=other * self.n_steps,
            builtin_instance_counter=total_builtin_instance_counter,
            n_memory_holes=other * self.n_memory_holes,
        )

    def __rmul__(self, other: int) -> "ExecutionResourcesStone":
        return self * other

    @classmethod
    def empty(cls):
        return cls(n_steps=0, builtin_instance_counter={}, n_memory_holes=0)

    def copy(self) -> "ExecutionResourcesStone":
        return copy.deepcopy(self)

    def to_dict(self) -> Dict[str, int]:
        return dict(
            **self.builtin_instance_counter,
            n_steps=self.n_steps + self.n_memory_holes,
        )

    def filter_unused_builtins(self) -> "ExecutionResourcesStone":
        filtered = super().filter_unused_builtins()
        assert isinstance(filtered, ExecutionResourcesStone)
        return filtered


@marshmallow_dataclass.dataclass
class ExecutionResourcesStwo(ExecutionResources):
    """
    ExecutionResources class for Stwo.
    """

    opcodes_instance_counter: Dict[str, int]
    memory_tables_sizes: Dict[str, int]
    n_verify_instructions: int = field(
        metadata=additional_metadata(marshmallow_field=mfields.Integer(load_default=0))
    )

    def __post_init__(self):
        """
        Validates items in builtin_instance_counter.
        """
        for builtin_name in self.builtin_instance_counter.keys():
            assert builtin_name.endswith(
                BUILTIN_NAME_SUFFIX
            ), f"Invalid builtin name: {builtin_name}."
            assert remove_builtin_suffix(builtin_name=builtin_name) in ALL_BUILTINS, (
                f"Invalid builtin name: {builtin_name}. " f"Expected one of: {ALL_BUILTINS}."
            )

    @property
    def n_steps(self) -> int:
        """
        Returns the number of steps, such that each opcode is counted as one step.
        """
        return sum(self.opcodes_instance_counter.values())

    def convert_to_stone(self) -> ExecutionResourcesStone:
        """
        Returns a ExecutionResourcesStone version of self.
        """
        return ExecutionResourcesStone(
            n_steps=self.n_steps,
            builtin_instance_counter=self.builtin_instance_counter,
            n_memory_holes=self.n_memory_holes,
        )

    def run_validity_checks(self):
        super().run_validity_checks()
        assert isinstance(self.opcodes_instance_counter, dict) and all(
            is_valid_opcode_name(name) and isinstance(size, int) and 0 <= size < 2**30
            for name, size in self.opcodes_instance_counter.items()
        ), "Invalid opcodes_instance_counter."
        assert isinstance(self.memory_tables_sizes, dict) and all(
            isinstance(size, int) and size >= 0 for size in self.memory_tables_sizes.values()
        ), "Invalid memory_tables_sizes."

    def __add__(self, other: ExecutionResources) -> "ExecutionResourcesStwo":
        assert isinstance(other, ExecutionResourcesStwo), "Invalid type for other."
        total_builtin_instance_counter = add_counters(
            self.builtin_instance_counter, other.builtin_instance_counter
        )

        total_opcodes_instance_counter = add_counters(
            self.opcodes_instance_counter, other.opcodes_instance_counter
        )

        total_memory_tables_sizes = add_counters(
            self.memory_tables_sizes, other.memory_tables_sizes
        )

        return ExecutionResourcesStwo(
            builtin_instance_counter=total_builtin_instance_counter,
            opcodes_instance_counter=total_opcodes_instance_counter,
            memory_tables_sizes=total_memory_tables_sizes,
            n_memory_holes=self.n_memory_holes + other.n_memory_holes,
            n_verify_instructions=self.n_verify_instructions + other.n_verify_instructions,
        )

    def __sub__(self, other: ExecutionResources) -> "ExecutionResourcesStwo":
        assert isinstance(other, ExecutionResourcesStwo), "Invalid type for other."
        diff_builtin_instance_counter = sub_counters(
            self.builtin_instance_counter, other.builtin_instance_counter
        )

        diff_opcodes_instance_counter = sub_counters(
            self.opcodes_instance_counter, other.opcodes_instance_counter
        )

        diff_memory_tables_sizes = sub_counters(self.memory_tables_sizes, other.memory_tables_sizes)

        return ExecutionResourcesStwo(
            builtin_instance_counter=diff_builtin_instance_counter,
            opcodes_instance_counter=diff_opcodes_instance_counter,
            memory_tables_sizes=diff_memory_tables_sizes,
            n_memory_holes=self.n_memory_holes - other.n_memory_holes,
            n_verify_instructions=self.n_verify_instructions - other.n_verify_instructions,
        )

    def __mul__(self, other: int) -> "ExecutionResourcesStwo":
        if not isinstance(other, int):
            return NotImplemented

        total_builtin_instance_counter = multiply_counter_by_scalar(
            scalar=other, counter=self.builtin_instance_counter
        )

        total_opcodes_instance_counter = multiply_counter_by_scalar(
            scalar=other, counter=self.opcodes_instance_counter
        )

        total_memory_tables_sizes = multiply_counter_by_scalar(
            scalar=other, counter=self.memory_tables_sizes
        )

        return ExecutionResourcesStwo(
            builtin_instance_counter=total_builtin_instance_counter,
            opcodes_instance_counter=total_opcodes_instance_counter,
            memory_tables_sizes=total_memory_tables_sizes,
            n_memory_holes=other * self.n_memory_holes,
            n_verify_instructions=other * self.n_verify_instructions,
        )

    def __rmul__(self, other: int) -> "ExecutionResourcesStwo":
        if not isinstance(other, int):
            return NotImplemented

        return self * other

    @classmethod
    def empty(cls):
        return cls(
            opcodes_instance_counter={},
            builtin_instance_counter={},
            memory_tables_sizes={},
            n_verify_instructions=0,
            n_memory_holes=0,
        )

    def copy(self) -> "ExecutionResourcesStwo":
        return copy.deepcopy(self)

    def to_dict(self) -> Dict[str, int]:
        return dict(
            **self.builtin_instance_counter,
            **self.opcodes_instance_counter,
            **self.memory_tables_sizes,
            n_verify_instructions=self.n_verify_instructions,
            n_memory_holes=self.n_memory_holes,
        )


class ExecutionResourcesSchema(OneOfSchema):
    """
    Schema for ExecutionResources.
    OneOfSchema adds a "type" field.
    """

    type_schemas: Dict[str, Type[marshmallow.Schema]] = {
        ExecutionResourcesStone.__name__: ExecutionResourcesStone.Schema,
        ExecutionResourcesStwo.__name__: ExecutionResourcesStwo.Schema,
    }

    def load(self, data, *args, **kwargs):
        """
        Sets the type field to ExecutionResourcesStone if it is missing.
        Used for backward compatibility.
        """
        if self.type_field not in data:
            data[self.type_field] = ExecutionResourcesStone.__name__
        return super().load(data, *args, **kwargs)


ExecutionResources.Schema = ExecutionResourcesSchema


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
    execution_resources: ExecutionResourcesStone
    version: Dict[str, str] = field(
        default_factory=lambda: {"cairo_pie": CURRENT_CAIRO_PIE_VERSION}
    )

    METADATA_FILENAME = "metadata.json"
    MEMORY_FILENAME = "memory.bin"
    ADDITIONAL_DATA_FILENAME = "additional_data.json"
    EXECUTION_RESOURCES_FILENAME = "execution_resources.json"
    VERSION_FILENAME = "version.json"
    OPTIONAL_FILES = [VERSION_FILENAME]
    ALL_FILES = [
        METADATA_FILENAME,
        MEMORY_FILENAME,
        ADDITIONAL_DATA_FILENAME,
        EXECUTION_RESOURCES_FILENAME,
    ] + OPTIONAL_FILES
    MAX_SIZE = 5 * 1024**3

    @classmethod
    def from_file(cls, fileobj) -> "CairoPie":
        """
        Loads an instance of CairoPie from a file.
        `fileobj` can be a path or a file object.
        """

        if isinstance(fileobj, str):
            fileobj = open(fileobj, "rb")

        verify_zip_file_prefix(fileobj=fileobj)

        with zipfile.ZipFile(fileobj) as zf:
            cls.verify_zip_format(zf)

            with zf.open(cls.METADATA_FILENAME, "r") as fp:
                metadata = CairoPieMetadata.Schema().load(
                    json.loads(fp.read(cls.MAX_SIZE).decode("ascii"))
                )
            with zf.open(cls.MEMORY_FILENAME, "r") as fp:
                memory = MemoryDict.deserialize(
                    data=fp.read(cls.MAX_SIZE),
                    field_bytes=metadata.field_bytes,
                )
            with zf.open(cls.ADDITIONAL_DATA_FILENAME, "r") as fp:
                additional_data = json.loads(fp.read(cls.MAX_SIZE).decode("ascii"))
            with zf.open(cls.EXECUTION_RESOURCES_FILENAME, "r") as fp:
                execution_resources = ExecutionResourcesStone.Schema().load(
                    json.loads(fp.read(cls.MAX_SIZE).decode("ascii"))
                )
            version = {"cairo_pie": DEFAULT_CAIRO_PIE_VERSION}
            if cls.VERSION_FILENAME in zf.namelist():
                with zf.open(cls.VERSION_FILENAME, "r") as fp:
                    version = json.loads(fp.read(cls.MAX_SIZE).decode("ascii"))

        return cls(metadata, memory, additional_data, execution_resources, version)

    def merge_extra_segments(self) -> Tuple[List[SegmentInfo], Dict[int, RelocatableValue]]:
        """
        Merges extra_segments to one segment.
        Returns a tuple of the new extra_segments (which contains a single merged segment) and a
        dictionary from old segment index to its offset in the new segment.
        """
        assert len(self.metadata.extra_segments) > 0

        # Take the index of the segment from the first merged segment.
        new_segment_index = self.metadata.extra_segments[0].index
        segment_offsets = {}
        segments_accumulated_size = 0
        for segment in self.metadata.extra_segments:
            segment_offsets[segment.index] = RelocatableValue(
                new_segment_index, segments_accumulated_size
            )
            segments_accumulated_size += segment.size
        return (
            [SegmentInfo(index=new_segment_index, size=segments_accumulated_size)],
            segment_offsets,
        )

    def get_relocate_value_func(
        self, segment_offsets: Optional[Mapping[int, MaybeRelocatable]]
    ) -> Optional[RelocateValueFunc]:
        """
        Returns a relocate_value function that relocates values according to the given segment
        offsets.
        """
        if segment_offsets is None:
            return None

        return functools.partial(
            relocate_value,
            segment_offsets=segment_offsets,
            prime=self.program.prime,
            # The known segments (such as builtins) are missing since we do not want to relocate
            # them.
            allow_missing_segments=True,
        )

    def to_file(self, file, merge_extra_segments: bool = False):
        extra_segments, segment_offsets = (
            self.merge_extra_segments()
            if merge_extra_segments and len(self.metadata.extra_segments) > 0
            else (None, None)
        )
        metadata = self.metadata
        if extra_segments is not None:
            metadata = dataclasses.replace(metadata, extra_segments=extra_segments)
        with zipfile.ZipFile(file, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            with zf.open(self.METADATA_FILENAME, "w") as fp:
                fp.write(json.dumps(CairoPieMetadata.Schema().dump(metadata)).encode("ascii"))
            with zf.open(self.MEMORY_FILENAME, "w", force_zip64=True) as fp:
                fp.write(
                    self.memory.serialize(
                        field_bytes=self.metadata.field_bytes,
                        relocate_value=self.get_relocate_value_func(
                            segment_offsets=segment_offsets
                        ),
                    )
                )
            with zf.open(self.ADDITIONAL_DATA_FILENAME, "w") as fp:
                fp.write(json.dumps(self.additional_data).encode("ascii"))
            with zf.open(self.EXECUTION_RESOURCES_FILENAME, "w") as fp:
                fp.write(
                    json.dumps(
                        ExecutionResourcesStone.Schema().dump(self.execution_resources)
                    ).encode("ascii")
                )
            with zf.open(self.VERSION_FILENAME, "w") as fp:
                fp.write(json.dumps(self.version).encode("ascii"))

    @classmethod
    def deserialize(cls, cairo_pie_bytes: bytes) -> "CairoPie":
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

        assert isinstance(self.memory, MemoryDict), "Invalid type for memory."
        self.run_memory_validity_checks()

        assert sorted(f"{name}_builtin" for name in self.metadata.program.builtins) == sorted(
            self.execution_resources.builtin_instance_counter.keys()
        ), "Builtin list mismatch in execution_resources."

        assert isinstance(self.additional_data, dict) and all(
            isinstance(name, str) and len(name) < 1000 for name in self.additional_data
        ), "Invalid additional_data."

    def run_memory_validity_checks(self):
        segment_sizes = self.metadata.segment_sizes()
        for addr, value in self.memory.items():
            assert is_valid_memory_addr(
                addr=addr, segment_sizes=segment_sizes
            ), "Invalid memory cell address."
            assert is_valid_memory_value(
                value=value, segment_sizes=segment_sizes
            ), "Invalid memory cell value."

    @classmethod
    def verify_zip_format(cls, zf: zipfile.ZipFile):
        """
        Checks that the given zip file contains the expected inner files, that the compression
        type is ZIP_DEFLATED and that their size is not too big.
        """
        # Check the compression algorithm.
        assert all(
            zip_info.compress_type == zipfile.ZIP_DEFLATED for zip_info in zf.filelist
        ), "Invalid compress type."

        # Check that orig_filename == filename.
        # Use "type: ignore" since mypy doesn't recognize ZipInfo.orig_filename.
        assert all(
            zip_info.orig_filename == zip_info.filename for zip_info in zf.filelist  # type: ignore
        ), "File name mismatch."

        # Make sure we have exactly the files we expect.
        inner_files = {zip_info.filename: zip_info for zip_info in zf.filelist}
        assert sorted(inner_files.keys() | cls.OPTIONAL_FILES) == sorted(
            cls.ALL_FILES
        ), "Invalid list of inner files in the CairoPIE zip."

        # Make sure the file sizes are reasonable.
        for name, limit in (
            (cls.METADATA_FILENAME, cls.MAX_SIZE),
            (cls.MEMORY_FILENAME, cls.MAX_SIZE),
            (cls.ADDITIONAL_DATA_FILENAME, cls.MAX_SIZE),
            (cls.EXECUTION_RESOURCES_FILENAME, 10000),
            (cls.VERSION_FILENAME, 10000),
        ):
            size = inner_files[name].file_size if name in inner_files else 0
            assert size < limit, f"Invalid file size {size} for {name}; limit is {limit}."

    def get_segment(self, segment_info: SegmentInfo):
        return self.memory.get_range(
            RelocatableValue(segment_index=segment_info.index, offset=0), size=segment_info.size
        )

    def is_compatible_with(self, other: "CairoPie") -> bool:
        """
        Checks equality between two CairoPies. Ignores .additional_data["pedersen_builtin"]
        to avoid an issue where a stricter run checks more Pedersen addresses and results
        in a different address list.
        """
        with ignore_pedersen_data(self):
            with ignore_pedersen_data(other):
                return self == other

    def diff(self, other: "CairoPie") -> str:
        """
        Returns a short description of the diff between two CairoPies.
        """
        res = ["CairoPie diff:"]
        if self.metadata != other.metadata:
            res.append(f" * metadata mismatch.")
        if self.memory != other.memory:
            res.append(f" * memory mismatch.")
        if self.additional_data != other.additional_data:
            res.append(f" * additional_data mismatch:")
            for key in sorted(self.additional_data.keys() | other.additional_data.keys()):
                if self.additional_data.get(key) != other.additional_data.get(key):
                    res.append(f"   * {key} mismatch.")
        if self.execution_resources != other.execution_resources:
            res.append(
                " * execution_resources mismatch: "
                f"{self.execution_resources} != {other.execution_resources}."
            )
        if self.version != other.version:
            res.append(f" * version mismatch: {self.version} != {other.version}.")
        return "\n".join(res)


def verify_zip_file_prefix(fileobj):
    """
    Verifies that the file starts with the zip file prefix.
    """
    fileobj.seek(0)
    # Make sure this is a zip file.
    assert fileobj.read(2) in ["PK", b"PK"], "Invalid prefix for zip file."


@contextlib.contextmanager
def ignore_pedersen_data(pie: CairoPie):
    """
    Context manager under which pie.additional_data["pedersen_builtin"] is set to None and
    reverted to its original value (or removed if it didn't exist before) when the context
    terminates.
    """
    should_pop = "pedersen_builtin" not in pie.additional_data
    original_pedersen_data, pie.additional_data["pedersen_builtin"] = (
        pie.additional_data.get("pedersen_builtin"),
        None,
    )
    try:
        yield
    finally:
        if should_pop:
            pie.additional_data.pop("pedersen_builtin")
        else:
            pie.additional_data["pedersen_builtin"] = original_pedersen_data
