from starkware.cairo.lang.vm.builtin_runner import SimpleBuiltinRunner
from starkware.cairo.lang.vm.relocatable import RelocatableValue


def validate_builtin_usage(builtin_runner: SimpleBuiltinRunner, end_ptr: RelocatableValue):
    assert builtin_runner.base is not None
    usage = end_ptr - builtin_runner.base
    assert usage % builtin_runner.cells_per_instance == 0, (
        f"usage = {usage} is not a multiple of cells_per_instance = "
        f"{builtin_runner.cells_per_instance}."
    )
