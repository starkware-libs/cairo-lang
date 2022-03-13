from typing import Dict, List, Optional

from starkware.cairo.lang.compiler.debug_info import DebugInfo, HintLocation, InstructionLocation
from starkware.cairo.lang.compiler.encode import encode_instruction
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.instruction_builder import build_instruction
from starkware.cairo.lang.compiler.preprocessor.preprocessor import PreprocessedProgram
from starkware.cairo.lang.compiler.preprocessor.unique_labels import is_anonymous_label
from starkware.cairo.lang.compiler.program import CairoHint, Program
from starkware.cairo.lang.compiler.scoped_name import ScopedName


def assemble(
    preprocessed_program: PreprocessedProgram,
    main_scope: ScopedName = ScopedName(),
    add_debug_info: bool = False,
    file_contents_for_debug_info: Dict[str, str] = {},
) -> Program:
    data: List[int] = []
    hints: Dict[int, List[CairoHint]] = {}
    debug_info = (
        DebugInfo(instruction_locations={}, file_contents=file_contents_for_debug_info)
        if add_debug_info
        else None
    )

    for inst in preprocessed_program.instructions:
        for hint, hint_flow_tracking_data in inst.hints:
            hints.setdefault(len(data), []).append(
                CairoHint(
                    code=hint.hint_code,
                    accessible_scopes=inst.accessible_scopes,
                    flow_tracking_data=hint_flow_tracking_data,
                )
            )
        if debug_info is not None and inst.instruction.location is not None:
            hint_locations: List[Optional[HintLocation]] = []
            for hint, _ in inst.hints:
                if hint.location is None:
                    hint_locations.append(None)
                else:
                    hint_locations.append(
                        HintLocation(
                            location=hint.location,
                            n_prefix_newlines=hint.hint.n_prefix_newlines,
                        )
                    )
            debug_info.instruction_locations[len(data)] = InstructionLocation(
                inst=inst.instruction.location,
                hints=hint_locations,
                accessible_scopes=inst.accessible_scopes,
                flow_tracking_data=inst.flow_tracking_data,
            )
        data += [
            word
            for word in encode_instruction(
                build_instruction(inst.instruction), prime=preprocessed_program.prime
            )
        ]

    if debug_info is not None:
        debug_info.add_autogen_file_contents()

    # Filter anonymous labels.
    identifiers = IdentifierManager.from_dict(
        {
            name: identifier_definition
            for name, identifier_definition in preprocessed_program.identifiers.as_dict().items()
            if not is_anonymous_label(name.path[-1])
        }
    )

    return Program(
        prime=preprocessed_program.prime,
        data=data,
        hints=hints,
        main_scope=main_scope,
        identifiers=identifiers,
        attributes=preprocessed_program.attributes,
        builtins=preprocessed_program.builtins,
        reference_manager=preprocessed_program.reference_manager,
        debug_info=debug_info,
    )
