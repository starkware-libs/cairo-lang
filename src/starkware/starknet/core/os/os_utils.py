from typing import List

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.starknet.core.os import segment_utils, syscall_utils
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.public.abi import SYSCALL_PTR_OFFSET
from starkware.starkware_utils.error_handling import wrap_with_stark_exception


def update_builtin_pointers(
    memory: MemoryDict,
    n_builtins: int,
    builtins_encoding_addr: RelocatableValue,
    n_selected_builtins: int,
    selected_builtins_encoding_addr: RelocatableValue,
    orig_builtins_ptrs_addr: RelocatableValue,
    selected_builtins_ptrs_addr: RelocatableValue,
):
    """
    Update subsets of the pointer at 'orig_builtins_ptrs_addr' with the pointers at
    'selected_builtins_ptrs_addr' according the location specified by
    'selected_builtins_encoding_addr'.

    Assumption: selected_builtins_encoding is an ordered subset of builtins_encoding_addr
    """
    all_builtins = [memory[builtins_encoding_addr + i] for i in range(n_builtins)]
    selected_builtins = [
        memory[selected_builtins_encoding_addr + i] for i in range(n_selected_builtins)
    ]

    return_builtins = []

    selected_builtin_offset = 0
    for index, builtin in enumerate(all_builtins):
        if builtin in selected_builtins:
            return_builtins.append(memory[selected_builtins_ptrs_addr + selected_builtin_offset])
            selected_builtin_offset += 1
        else:
            # The builtin is unselected, hence its value is the same as before calling the program.
            return_builtins.append(memory[orig_builtins_ptrs_addr + index])

    return return_builtins


def prepare_os_context(runner: CairoFunctionRunner) -> List[MaybeRelocatable]:
    syscall_segment = runner.segments.add()
    os_context: List[MaybeRelocatable] = [syscall_segment]

    for builtin in runner.program.builtins:
        builtin_runner = runner.builtin_runners[f"{builtin}_builtin"]
        os_context.extend(builtin_runner.initial_stack())

    return os_context


def validate_and_process_os_context(
    runner: CairoFunctionRunner,
    syscall_handler: syscall_utils.BusinessLogicSysCallHandler,
    initial_os_context: List[MaybeRelocatable],
):
    """
    Validates and processes an OS context that was returned by a transaction.
    Returns the syscall processor object containing the accumulated syscall information.
    """
    # The returned values are os_context, retdata_size, retdata_ptr.
    os_context_end = runner.vm.run_context.ap - 2
    stack_ptr = os_context_end
    for builtin in runner.program.builtins[::-1]:
        builtin_runner = runner.builtin_runners[f"{builtin}_builtin"]

        with wrap_with_stark_exception(code=StarknetErrorCode.SECURITY_ERROR):
            stack_ptr = builtin_runner.final_stack(runner=runner, pointer=stack_ptr)

    final_os_context_ptr = stack_ptr - 1
    assert final_os_context_ptr + len(initial_os_context) == os_context_end

    # Validate system calls.
    syscall_base_ptr, syscall_stop_ptr = segment_utils.get_os_segment_ptr_range(
        runner=runner, ptr_offset=SYSCALL_PTR_OFFSET, os_context=initial_os_context
    )

    segment_utils.validate_segment_pointers(
        segments=runner.segments,
        segment_base_ptr=syscall_base_ptr,
        segment_stop_ptr=syscall_stop_ptr,
    )
    syscall_handler.post_run(runner=runner, syscall_stop_ptr=syscall_stop_ptr)
