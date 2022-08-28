import pytest

from starkware.cairo.lang.compiler.cairo_compile import Program, compile_cairo
from starkware.cairo.lang.tracer.tracer_data import InputCodeFile, TracerData, WatchEvaluator
from starkware.cairo.lang.vm.cairo_runner import CairoRunner

PRIME = 2**251 + 17 * 2**192 + 1


def test_input_code_file():
    input_file = InputCodeFile("aTestLine")
    input_file.mark_text(1, 2, 1, 6, classes=["test"])  # Mark "test"
    input_file.mark_text(1, 2, 1, 10, classes=["test_line"])  # Mark "test line"
    input_file.mark_text(1, 6, 1, 10, classes=["line"])  # Mark "line"
    input_file.mark_text(1, 1, 1, 2, classes=["a"])  # Mark "a"
    assert (
        input_file.to_html()
        == '<span class="a">a</span><span class="test_line"><span class="test">Test'
        '</span><span class="line">Line</span></span>'
    )


def test_tracer_data():
    code = """
%builtins output

func main(output_ptr: felt*) -> (output_ptr: felt*) {
    [ap] = 1000, ap++;
    let x = 2000;
    [ap] = x, ap++;
    let x = 5000;
    let y = [ap];
    [ap] = [ap - 2] + [ap - 1], ap++;
    assert [output_ptr] = 1234;
    assert [output_ptr + 1] = 4321;
    ret;
}
"""
    program: Program = compile_cairo(code=code, prime=PRIME, debug_info=True)
    runner = CairoRunner(program, layout="small")
    runner.initialize_segments()
    runner.initialize_main_entrypoint()
    runner.initialize_vm(hint_locals={})
    runner.run_until_steps(steps=6)
    runner.end_run()
    runner.relocate()
    memory = runner.relocated_memory
    trace = runner.relocated_trace

    tracer_data = TracerData(
        program=program,
        memory=memory,
        trace=trace,
        program_base=runner.relocate_value(runner.program_base),
    )

    # Test watch evaluator.
    watch_evaluator = WatchEvaluator(tracer_data=tracer_data, entry=tracer_data.trace[0])
    with pytest.raises(TypeError, match="NoneType"):
        watch_evaluator.eval(None)
    assert watch_evaluator.eval_suppress_errors("x") == "FlowTrackingError: Invalid reference 'x'."
    watch_evaluator = WatchEvaluator(tracer_data=tracer_data, entry=tracer_data.trace[1])
    assert watch_evaluator.eval("x") == "2000"
    watch_evaluator = WatchEvaluator(tracer_data=tracer_data, entry=tracer_data.trace[2])
    assert watch_evaluator.eval("[ap]") == "3000"
    assert watch_evaluator.eval("[ap-1]") == "2000"
    assert watch_evaluator.eval("[ap-2]") == "1000"
    assert watch_evaluator.eval("[fp]") == "1000"
    assert watch_evaluator.eval("x") == "5000"

    # Test memory_accesses.
    assert memory[tracer_data.memory_accesses[0]["op1"]] == 1000
    assert memory[tracer_data.memory_accesses[1]["op1"]] == 2000
    assert tracer_data.memory_accesses[2]["dst"] == trace[2].ap
    assert tracer_data.memory_accesses[2]["op0"] == trace[2].ap - 2
    assert tracer_data.memory_accesses[2]["op1"] == trace[2].ap - 1

    # Test current identifier values.
    assert tracer_data.get_current_identifier_values(trace[0]) == {"output_ptr": "21"}
    assert tracer_data.get_current_identifier_values(trace[1]) == {"output_ptr": "21", "x": "2000"}
    assert tracer_data.get_current_identifier_values(trace[2]) == {
        "output_ptr": "21",
        "x": "5000",
        "y": "3000",
    }
    assert tracer_data.get_current_identifier_values(trace[3]) == {
        "output_ptr": "21",
        "x": "5000",
        "y": "3000",
    }
    assert tracer_data.get_current_identifier_values(trace[4]) == {
        "output_ptr": "21",
        "x": "5000",
        "y": "3000",
        "__temp0": "1234",
    }
    assert tracer_data.get_current_identifier_values(trace[5]) == {
        "output_ptr": "21",
        "x": "5000",
        "y": "3000",
        "__temp0": "1234",
    }
