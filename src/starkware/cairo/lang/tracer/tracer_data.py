import dataclasses
import json
import math
from typing import Dict, List, Optional

from starkware.cairo.lang.compiler.ast.cairo_types import TypeStruct
from starkware.cairo.lang.compiler.ast.expr import ExprConst, ExprIdentifier
from starkware.cairo.lang.compiler.debug_info import DebugInfo
from starkware.cairo.lang.compiler.encode import decode_instruction
from starkware.cairo.lang.compiler.expression_evaluator import ExpressionEvaluator
from starkware.cairo.lang.compiler.identifier_definition import ConstDefinition, ReferenceDefinition
from starkware.cairo.lang.compiler.offset_reference import OffsetReferenceDefinition
from starkware.cairo.lang.compiler.parser import parse_expr
from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.lang.compiler.references import (
    FlowTrackingError, SubstituteRegisterTransformer)
from starkware.cairo.lang.compiler.resolve_search_result import resolve_search_result
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.substitute_identifiers import substitute_identifiers
from starkware.cairo.lang.compiler.type_system_visitor import simplify_type_system
from starkware.cairo.lang.vm.air_public_input import PublicInput
from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.memory_segments import FIRST_MEMORY_ADDR as PROGRAM_BASE
from starkware.cairo.lang.vm.trace_entry import TraceEntry
from starkware.cairo.lang.vm.vm import RunContext


@dataclasses.dataclass
class TextMark:
    line_start: int
    col_start: int
    line_end: int
    col_end: int
    classes: List[str]


class InputCodeFile:
    """
    Represents an HTML-annotated Cairo assembly code file.
    Supports adding HTML tags to the content on given locations, so that adding a tag does not
    affect locations for the next tag.
    Usage example:
      > f = InputCodeFile('hello world!')
      > # Surround "world" with <span class="myclass">.
      > f.mark_text(1, 7, 1, 12, ['myclass'])
      > f.to_html()
      'hello&nbsp;<b>world</b>!'
    """

    def __init__(self, content):
        self.content = content
        self.lines = self.content.splitlines()
        self.marks: List[TextMark] = []
        # A list of tuples (offset, -size, tag) where offset is the position of the beginning of
        # the tag and size is the size of the content. size is negative to allow sorting the tags
        # correctly. As end tags (e.g., </span>) always appear before the start tags, their second
        # entry is set to -inf.
        self.tags = []

    def mark_text(
            self, line_start: int, col_start: int, line_end: int, col_end: int, classes: List[str]):
        """
        Surrounds the given part of the input text with a <span> tag with the given classes.
        """
        self.marks.append(TextMark(
            line_start=line_start, col_start=col_start, line_end=line_end, col_end=col_end,
            classes=classes))

        # Find the offset of (line_start, col_start) inside the file, by computing the sum of the
        # lengths of the previous lines and adding col_start. Note that '\n's are not counted in
        # the sum, so we add line_start to the result. We have to subtract 2 since both
        # line_start and col_start are 1-based rather than 0-based.
        offset_start = sum(map(len, self.lines[:line_start - 1])) + line_start + col_start - 2
        # Do the same for (line_end, col_end).
        offset_end = sum(map(len, self.lines[:line_end - 1])) + line_end + col_end - 2
        self.tags.append((offset_start, -offset_end, f'<span class="{" ".join(classes)}">'))
        self.tags.append((offset_end, -float('inf'), '</span>'))

    def to_html(self):
        """
        Returns the content of the file with the added HTML tags.
        Replaces spaces with '&nbsp;' and '\n' with '<br/>'.
        """
        res = self.content.replace(' ', '\0')
        for pos, size, tag_content in sorted(self.tags, reverse=True):
            res = res[:pos] + tag_content + res[pos:]
        return res.replace('\0', '&nbsp;').replace('\n', '<br/>\n')


class TracerData:
    def __init__(
            self, program: Program, memory: MemoryDict, trace: List[TraceEntry], program_base: int,
            air_public_input: Optional[PublicInput] = None,
            debug_info: Optional[DebugInfo] = None):
        """
        Constructs a TracerData object.
        program_base is the memory address where the program is loaded.
        """
        self.program = program
        self.memory = memory
        self.trace = trace
        self.program_base = program_base
        self.debug_info = debug_info if debug_info is not None else program.debug_info

        # Read AIR public input, if available and extract public memory addresses.
        if air_public_input is not None:
            self.public_memory: List[int] = [x.address for x in air_public_input.public_memory]
        else:
            self.public_memory = []

        self.input_files: Dict[str, InputCodeFile] = {}

        if self.debug_info is not None:
            # Process each instruction in the program and surround it by a <span> tag.
            for pc_offset, instruction_location in self.debug_info.instruction_locations.items():
                loc = instruction_location.inst
                filename = loc.input_file.filename
                assert filename is not None
                # If filename was not loaded yet, create a new InputCodeFile instance.
                if filename not in self.input_files:
                    self.input_files[filename] = InputCodeFile(loc.input_file.get_content())
                input_file = self.input_files[filename]

                # Surround the instruction code with a <span> tag.
                input_file.mark_text(
                    loc.start_line, loc.start_col, loc.end_line, loc.end_col,
                    [f'inst{pc_offset}', 'instruction'])

        # Find memory accesses for each step.
        self.memory_accesses = []
        for trace_entry in self.trace:
            run_context = RunContext(
                pc=trace_entry.pc, ap=trace_entry.ap, fp=trace_entry.fp, memory=self.memory,
                prime=self.program.prime)
            instruction_encoding, imm = run_context.get_instruction_encoding()
            instruction = decode_instruction(instruction_encoding, imm)

            dst_addr = run_context.compute_dst_addr(instruction)
            op0_addr = run_context.compute_op0_addr(instruction)
            op1_addr = run_context.compute_op1_addr(instruction, self.memory.get(op0_addr))
            self.memory_accesses.append({'dst': dst_addr, 'op0': op0_addr, 'op1': op1_addr})

    def get_pc_offset(self, pc: int) -> int:
        """
        Returns the offset of the instruction pointed by pc with respect to the program section.
        """
        return pc - self.program_base

    def get_pc_from_offset(self, offset: int) -> int:
        """
        Returns the pc given the offset of the instruction with respect to the program section.
        """
        return offset + self.program_base

    def get_current_identifier_values(self, entry: TraceEntry) -> Dict[str, str]:
        assert self.debug_info is not None
        pc_offset = self.get_pc_offset(entry.pc)
        scope_name = self.debug_info.instruction_locations[pc_offset].accessible_scopes[-1]
        scope_items = self.program.identifiers.get_scope(scope_name).identifiers

        result = {}
        watch_evaluator = WatchEvaluator(self, entry)
        for name, identifier_definition in scope_items.items():
            if isinstance(identifier_definition, ReferenceDefinition):
                try:
                    result[name] = watch_evaluator.eval(name)
                except Exception:
                    continue
        return result

    @classmethod
    def from_files(
            cls, program_path: str, memory_path: str, trace_path: str,
            air_public_input: Optional[str], debug_info_path: Optional[str] = None):
        """
        Factory method constructing TracerData from files.
        """
        program = Program.Schema().load(json.load(open(program_path)))
        field_bytes = math.ceil(program.prime.bit_length() / 8)
        memory = read_memory(memory_path, field_bytes)
        trace = read_trace(trace_path)
        program_base = PROGRAM_BASE

        # Read AIR public input, if available and extract public memory addresses.
        if air_public_input is not None:
            public_input = PublicInput.Schema().load(json.load(open(air_public_input)))
        else:
            public_input = None

        debug_info = DebugInfo.Schema().load(json.load(open(debug_info_path))) \
            if debug_info_path is not None else None

        # Construct the instance.
        return cls(
            program=program, memory=memory, trace=trace, program_base=program_base,
            air_public_input=public_input, debug_info=debug_info)


def read_memory(memory_path: str, field_bytes: int) -> MemoryDict:
    """
    Returns the memory (as a MemoryDict).
    """
    # Use MemoryDict to verify that memory cells are consistent.
    with open(memory_path, 'rb') as memory_file:
        return MemoryDict.deserialize(memory_file.read(), field_bytes)


def read_trace(trace_path: str) -> List[TraceEntry]:
    """
    Returns the trace (as a list of trace entries).
    """
    entries = []
    serialization_size = TraceEntry.serialization_size()
    with open(trace_path, 'rb') as trace_file:
        while True:
            entry_serialized = trace_file.read(serialization_size)
            if not entry_serialized:
                break
            assert len(entry_serialized) == serialization_size, 'Size of trace file is invalid.'
            entry = TraceEntry.deserialize(entry_serialized)
            entries.append(entry)

    return entries


def field_element_repr(val: int, prime: int) -> str:
    """
    Converts a field element (given as int) to a decimal/hex string according to its size.
    """
    # Shift val to the range (-prime // 2, prime // 2).
    shifted_val = (val + prime // 2) % prime - (prime // 2)
    # If shifted_val is small, use decimal representation.
    if abs(shifted_val) < 2**40:
        return str(shifted_val)
    # Otherwise, use hex representation (allowing a sign if the number is close to prime).
    if abs(shifted_val) < 2**100:
        return hex(shifted_val)
    return hex(val)


class WatchEvaluator(ExpressionEvaluator):
    def __init__(self, tracer_data: TracerData, entry: TraceEntry[int]):
        super().__init__(
            prime=tracer_data.program.prime, ap=entry.ap,
            fp=entry.fp, memory=tracer_data.memory)
        self.tracer_data = tracer_data
        self.pc = entry.pc
        self.ap = entry.ap
        self.fp = entry.fp

        self.accessible_scopes = []
        if tracer_data.debug_info is not None:
            pc_offset = self.tracer_data.get_pc_offset(self.pc)
            info = tracer_data.debug_info.instruction_locations.get(pc_offset)
            if info is not None:
                self.accessible_scopes = info.accessible_scopes

    def eval(self, expr):
        if expr == 'null':
            return ''
        expr, expr_type = simplify_type_system(
            substitute_identifiers(
                expr=parse_expr(expr),
                get_identifier_callback=self.get_variable),
            identifiers=self.tracer_data.program.identifiers)
        if isinstance(expr_type, TypeStruct):
            raise NotImplementedError('Structs are not supported.')
        res = self.visit(expr)
        if isinstance(res, ExprConst):
            return field_element_repr(res.val, self.tracer_data.program.prime)
        return res.format()

    def eval_suppress_errors(self, expr):
        try:
            return self.eval(expr)
        except Exception as exc:
            return f'{type(exc).__name__}: {exc}'

    def get_variable(self, var: ExprIdentifier):
        identifiers = self.tracer_data.program.identifiers
        identifier_definition = resolve_search_result(
            identifiers.search(
                accessible_scopes=self.accessible_scopes,
                name=ScopedName.from_string(var.name),
            ),
            identifiers=identifiers)
        if isinstance(identifier_definition, ConstDefinition):
            return identifier_definition.value

        if isinstance(identifier_definition, (ReferenceDefinition, OffsetReferenceDefinition)):
            return self.visit(self.eval_reference(identifier_definition, var.name))

        raise Exception(
            f'Unexpected identifier {var.name} of type {identifier_definition.TYPE}.')

    def eval_reference(self, identifier_definition, var_name: str):
        pc_offset = self.tracer_data.get_pc_offset(self.pc)
        assert self.tracer_data.program.debug_info is not None
        current_flow_tracking_data = \
            self.tracer_data.program.debug_info.instruction_locations[pc_offset].flow_tracking_data
        try:
            substitute_transformer = SubstituteRegisterTransformer(
                ap=lambda location: ExprConst(val=self.ap, location=location),
                fp=lambda location: ExprConst(val=self.fp, location=location))
            return self.visit(substitute_transformer.visit(
                identifier_definition.eval(
                    reference_manager=self.tracer_data.program.reference_manager,
                    flow_tracking_data=current_flow_tracking_data)))
        except FlowTrackingError:
            raise FlowTrackingError(f"Invalid reference '{var_name}'.")
