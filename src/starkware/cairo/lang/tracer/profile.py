"""
Generates a profile output file that can be read by pprof: https://github.com/google/pprof.
The .proto file is taken from there. If this changes, build the proto file using
protoc --proto_path src/starkware/cairo/lang/tracer/third_party/
       --python_out=src/starkware/cairo/lang/tracer/third_party/
        src/starkware/cairo/lang/tracer/third_party/profile.proto
"""

import gzip
import time

from starkware.cairo.lang.compiler.debug_info import InstructionLocation
from starkware.cairo.lang.compiler.identifier_definition import LabelDefinition
from starkware.cairo.lang.tracer.third_party.profile_pb2 import Profile
from starkware.cairo.lang.tracer.tracer_data import TracerData
from starkware.cairo.lang.vm.trace_entry import TraceEntry


class ProfileBuilder:
    """
    Builds a profile protobuf from trace samples of a specific run.
    The Profile protobuf uses ids to reference objects, so we maintain id dictionaries internally.
    For example: instead of writing string in objects, we always pass an id to the string table.
    See profile.proto for more information.

    initial_fp - First fp in the program.
    memory - memory object of the run.
    """

    def __init__(self, initial_fp, memory):
        self._profile = Profile()
        # A map from a string to its id in the string table.
        self._string_to_id = {}
        # First string in the table must be ''.
        self.string_id("")
        # A map from a filename to its id in the mapping table.
        self._filename_to_mapping_id = {}
        # A map from a function name to its id in the function table.
        # Current implementation uses the string id of the function name as a function id.
        self._func_name_to_id = {}
        # A map from a pc value to the location id at that pc.
        self._pc_to_location_id = {}

        self.initial_fp = initial_fp
        self.memory = memory

        # Global fields.
        sample_type = self._profile.sample_type.add()
        sample_type.type = self.string_id("running time")
        sample_type.unit = self.string_id("steps")
        self._profile.time_nanos = int(time.time() * 10 ** 9)

        # Main function.
        self._func_name_to_id["__main__"] = self.string_id("__main__")
        main_func = self._profile.function.add()
        main_func.id = self.string_id("__main__")
        main_func.system_name = main_func.name = self.string_id("<dummy>")
        main_func.filename = self.string_id("<dummy_filename>")
        main_func.start_line = 0

    def string_id(self, s: str) -> int:
        """
        Retrieves the id of a string in the string table. Adds to the table if not already present.
        """
        if s not in self._string_to_id:
            self._string_to_id[s] = len(self._string_to_id)
            self._profile.string_table.append(s)
        return self._string_to_id[s]

    def update_mapping_pc_range(self, filename: str, accessed_pc: int) -> int:
        """
        Retrieves the id of a mapping. Adds to the table if not already present.
        Updates the range of pcs of that mapping according to the accessed_pc.
        Each access to a pc in this mapping should call update_mapping_pc_range().
        A mapping represents a file-like source of instructions.
        """
        if filename not in self._filename_to_mapping_id:
            # Id 0 is reserved. Shift ids.
            mapping_id = self._filename_to_mapping_id[filename] = (
                len(self._filename_to_mapping_id) + 1
            )
            mapping = self._profile.mapping.add()
            mapping.id = mapping_id
            mapping.memory_start = accessed_pc
            mapping.memory_limit = accessed_pc + 1
            mapping.file_offset = 0
            mapping.filename = self.string_id(filename)
            mapping.build_id = 0
            mapping.has_functions = True
            mapping.has_filenames = True
            mapping.has_line_numbers = True
            mapping.has_inline_frames = True
            return mapping_id
        # Update memory range.
        mapping_id = self._filename_to_mapping_id[filename]
        mapping = self._profile.mapping[mapping_id - 1]
        mapping.memory_start = min(accessed_pc, mapping.memory_start)
        mapping.memory_limit = max(mapping.memory_limit, accessed_pc + 1)
        return mapping_id

    def function_id(self, name: str, inst_location: InstructionLocation) -> int:
        """
        Retrieves the id of a function. Adds to the table if not already present.
        """
        func_id = self.string_id(name)
        if name not in self._func_name_to_id:
            self._func_name_to_id[name] = func_id
            func = self._profile.function.add()
            func.id = func_id
            func.system_name = func.name = self.string_id(name)
            assert inst_location.inst.input_file.filename is not None
            func.filename = self.string_id(inst_location.inst.input_file.filename)
            func.start_line = inst_location.inst.start_line
        return func_id

    def location_id(self, pc, inst_location: InstructionLocation) -> int:
        """
        Retrieves the id of a location. Adds to the table if not already present.
        """
        if pc not in self._pc_to_location_id:
            self._pc_to_location_id[pc] = pc + 1
            location = self._profile.location.add()
            location.id = pc + 1
            location.address = pc
            location.is_folded = False

            sublocation = inst_location.inst
            line = location.line.add()
            line.function_id = self._func_name_to_id[str(inst_location.accessible_scopes[-1])]
            line.line = sublocation.start_line
            assert sublocation.input_file.filename is not None
            location.mapping_id = self.update_mapping_pc_range(sublocation.input_file.filename, pc)
        return self._pc_to_location_id[pc]

    def get_call_stack(self, fp, pc):
        """
        Retrieves the call stack pc values given current fp and pc.
        """
        frame_pcs = [pc]
        while fp > self.initial_fp:
            fp, pc = self.memory[fp - 2], self.memory[fp - 1]
            frame_pcs.append(pc)
        return frame_pcs

    def add_sample(self, trace_entry: TraceEntry):
        """
        Adds a sample to the profile.
        """
        frame_pcs = self.get_call_stack(fp=trace_entry.fp, pc=trace_entry.pc)
        sample = self._profile.sample.add()
        for pc in frame_pcs:
            sample.location_id.append(self._pc_to_location_id[pc])
        sample.value.append(1)  # 1 step.

    def dump(self) -> bytes:
        """
        Dumps the current profile. Returns the serialized bytes.
        """
        data = self._profile.SerializeToString()
        return gzip.compress(data)


def profile_from_tracer_data(tracer_data: TracerData):
    """
    Computes the profile file data given a TracerData instance.
    Can be read by pprof.
    """
    builder = ProfileBuilder(initial_fp=tracer_data.trace[0].fp, memory=tracer_data.memory)

    # Functions.
    identifiers_dict = tracer_data.program.identifiers.as_dict()
    assert tracer_data.program.debug_info is not None
    for name, ident in identifiers_dict.items():
        if not isinstance(ident, LabelDefinition):
            continue
        builder.function_id(
            name=str(name),
            inst_location=tracer_data.program.debug_info.instruction_locations[ident.pc],
        )

    # Locations.
    for pc_offset, inst_location in tracer_data.program.debug_info.instruction_locations.items():
        builder.location_id(
            pc=tracer_data.get_pc_from_offset(pc_offset), inst_location=inst_location
        )

    # Samples.
    for trace_entry in tracer_data.trace:
        builder.add_sample(trace_entry)

    return builder.dump()
