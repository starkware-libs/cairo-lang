from starkware.cairo.lang.vm.cairo_runner import CairoRunner
from starkware.cairo.lang.vm.relocatable import RelocatableValue
from starkware.cairo.lang.vm.vm_exceptions import SecurityError


def verify_secure_runner(runner: CairoRunner, verify_builtins=True):
    """
    Verifies the complete run in runner is safe to relocate and run by another Cairo program.
    Checks that:
    * No access to pure addresses (The entire run must be relocatable).
    * All segment offsets are non negative.
    * No access to builtin segments beyond the allowed region. This region is defined
      by the start ptr (0), and the ptr returned in final stack.
    * No access to program segment beyond program data.
    Note: The continuity of builtin segments is checked in builtin specific checks.
    """

    builtin_segments = runner.get_builtin_segments_info() if verify_builtins else {}
    builtin_segment_names = {seg.index: name for name, seg in builtin_segments.items()}
    builtin_segment_sizes = {seg.index: seg.size for seg in builtin_segments.values()}
    for addr, value in runner.vm_memory.items():
        # Check pure addresses.
        if not isinstance(addr, RelocatableValue):
            raise SecurityError(f"Accessed address {addr} is not relocatable.")
        # Check non negative offset.
        if addr.offset < 0:
            raise SecurityError(f"Accessed address {addr} has negative offset.")
        # Check builtin segment out of bounds.
        if addr.segment_index in builtin_segment_sizes:
            if not addr.offset < builtin_segment_sizes[addr.segment_index]:
                raise SecurityError(
                    "Out of bounds access to builtin segment "
                    f"{builtin_segment_names[addr.segment_index]} at {addr}."
                )

        # Check out of bounds for program segment.
        if addr.segment_index == runner.program_base.segment_index:
            if not addr.offset < len(runner.program.data):
                raise SecurityError(f"Out of bounds access to program segment at {addr}.")

        # Check memory value, to be consistent with the CairoPie validation done by SHARP.
        if not runner.segments.is_valid_memory_value(value=value):
            raise SecurityError(f"Invalid memory value at address {addr}: {value}.")

    # Builtin specific checks.
    try:
        for builtin_runner in runner.builtin_runners.values():
            builtin_runner.run_security_checks(runner)
    except Exception as exc:
        raise SecurityError(str(exc))
