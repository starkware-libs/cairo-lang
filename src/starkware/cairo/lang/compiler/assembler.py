from typing import Dict, List

from starkware.cairo.lang.compiler.debug_info import DebugInfo, HintLocation, InstructionLocation
from starkware.cairo.lang.compiler.encode import encode_instruction
from starkware.cairo.lang.compiler.instruction_builder import build_instruction
from starkware.cairo.lang.compiler.preprocessor.preprocessor import PreprocessedProgram
from starkware.cairo.lang.compiler.program import CairoHint, Program
from starkware.cairo.lang.compiler.scoped_name import ScopedName


def assemble(
        preprocessed_program: PreprocessedProgram, main_scope: ScopedName = ScopedName(),
        add_debug_info: bool = False, file_contents_for_debug_info: Dict[str, str] = {}) -> Program:
    data: List[int] = []
    hints: Dict[int, CairoHint] = {}
    debug_info = DebugInfo(instruction_locations={}, file_contents=file_contents_for_debug_info) \
        if add_debug_info else None

    for inst in preprocessed_program.instructions:
        if inst.hint:
            hints[len(data)] = CairoHint(
                code=inst.hint.hint_code,
                accessible_scopes=inst.accessible_scopes,
                flow_tracking_data=inst.flow_tracking_data)
        if debug_info is not None and inst.instruction.location is not None:
            hint_location = None
            if inst.hint is not None and inst.hint.location is not None:
                hint_location = HintLocation(
                    location=inst.hint.location,
                    n_prefix_newlines=inst.hint.n_prefix_newlines,
                )
            debug_info.instruction_locations[len(data)] = \
                InstructionLocation(
                    inst=inst.instruction.location,
                    hint=hint_location,
                    accessible_scopes=inst.accessible_scopes,
                    flow_tracking_data=inst.flow_tracking_data)
        data += [word for word in encode_instruction(
            build_instruction(inst.instruction), prime=preprocessed_program.prime)]

    return Program(
        prime=preprocessed_program.prime,
        data=data,
        hints=hints,
        main_scope=main_scope,
        identifiers=preprocessed_program.identifiers,
        builtins=preprocessed_program.builtins,
        reference_manager=preprocessed_program.reference_manager,
        debug_info=debug_info)
