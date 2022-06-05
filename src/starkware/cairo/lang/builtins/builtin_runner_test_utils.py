from starkware.cairo.lang.compiler.cairo_compile import compile_cairo
from starkware.cairo.lang.vm.cairo_runner import CairoRunner

PRIME = 2**251 + 17 * 2**192 + 1


def compile_and_run(code: str, layout: str = "small"):
    """
    Compiles the given code and runs it in the VM.
    """
    program = compile_cairo(code, PRIME)
    runner = CairoRunner(program, layout=layout, proof_mode=False)
    runner.initialize_segments()
    end = runner.initialize_main_entrypoint()
    runner.initialize_vm({})
    runner.run_until_pc(end)
    runner.end_run()
