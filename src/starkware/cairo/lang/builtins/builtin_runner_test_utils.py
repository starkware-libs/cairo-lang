from typing import Union

from starkware.cairo.lang.compiler.cairo_compile import compile_cairo
from starkware.cairo.lang.instances import CairoLayout
from starkware.cairo.lang.vm.cairo_runner import CairoRunner
from starkware.cairo.lang.vm.security import verify_secure_runner

PRIME = 2**251 + 17 * 2**192 + 1


def compile_and_run(
    code: str, layout: Union[str, CairoLayout] = "small", secure_run: bool = False
) -> CairoRunner:
    """
    Compiles the given code and runs it in the VM.
    """
    program = compile_cairo(code, PRIME)
    runner = CairoRunner(program, layout=layout, proof_mode=False)
    runner.initialize_segments()
    end = runner.initialize_main_entrypoint()
    runner.initialize_zero_segment()
    runner.initialize_vm({})
    runner.run_until_pc(end)
    runner.end_run()
    if secure_run:
        runner.read_return_values()
        verify_secure_runner(runner)
        pie = runner.get_cairo_pie()
        pie.run_validity_checks()

    return runner
