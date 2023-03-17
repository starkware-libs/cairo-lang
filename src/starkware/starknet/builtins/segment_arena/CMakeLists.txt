python_lib(segment_arena_builtin_lib
    PREFIX starkware/starknet/builtins/segment_arena

    FILES
    segment_arena_builtin_runner.py

    LIBS
    cairo_vm_lib
)

full_python_test(segment_arena_test
    PREFIX starkware/starknet/builtins/segment_arena
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/starknet/builtins/segment_arena

    FILES
    segment_arena.cairo
    segment_arena_test.cairo
    segment_arena_test.py

    LIBS
    cairo_common_lib
    cairo_function_runner_lib
    cairo_constants_lib
    cairo_compile_lib
    pip_pytest
)
