from typing import Optional, Sequence

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.starknet.core.os.contract_class.compiled_class_hash import (
    BytecodeAccessOracle,
    create_bytecode_segment_structure,
)
from starkware.starknet.core.os.contract_class.compiled_class_hash_cairo_hints import (
    get_compiled_class_struct,
    load_compiled_class_cairo_program,
)
from starkware.starknet.services.api.contract_class.contract_class import CompiledClass


def run_compiled_class_hash(
    compiled_class: CompiledClass, visited_pcs: Optional[Sequence[int]] = None
) -> CairoFunctionRunner:
    program = load_compiled_class_cairo_program()
    runner = CairoFunctionRunner(program=program)

    bytecode_segment_structure = create_bytecode_segment_structure(
        bytecode=compiled_class.bytecode,
        bytecode_segment_lengths=compiled_class.bytecode_segment_lengths,
    )

    compiled_class_struct = get_compiled_class_struct(
        identifiers=program.identifiers,
        compiled_class=compiled_class,
        bytecode=compiled_class.bytecode,
    )
    visited_pcs_set = (
        set(visited_pcs) if visited_pcs is not None else set(range(len(compiled_class.bytecode)))
    )
    bytecode_segment_access_oracle = BytecodeAccessOracle(
        is_pc_accessed_callback=lambda pc: pc.offset in visited_pcs_set
    )
    runner.run(
        "starkware.starknet.core.os.contract_class.compiled_class.compiled_class_hash",
        range_check_ptr=runner.range_check_builtin.base,
        poseidon_ptr=runner.poseidon_builtin.base,
        compiled_class=compiled_class_struct,
        use_full_name=True,
        verify_secure=False,
        hint_locals={
            "bytecode_segment_structure": bytecode_segment_structure,
            "is_segment_used_callback": bytecode_segment_access_oracle.is_segment_used,
        },
    )
    return runner
