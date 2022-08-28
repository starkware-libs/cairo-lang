from starkware.cairo.lang.compiler.ast.code_elements import (
    CodeBlock,
    CodeElementFunction,
    CodeElementIf,
    CodeElementScoped,
)
from starkware.cairo.lang.compiler.injector import inject_code_elements
from starkware.cairo.lang.compiler.parser import parse
from starkware.cairo.lang.compiler.scoped_name import ScopedName


def test_injector():
    block: CodeBlock = parse(
        filename="<file0>",
        code="""\
let (x, local y) = f();
let z = 1;
if (1 != 0) {
    tempvar z = 0;
}
local x = 1;
func foo() {
    tempvar y = 0;
}
""",
        code_type="code_block",
        expected_type=CodeBlock,
    )
    injected0 = parse(
        filename="<file1>",
        code="const a = 0;\n",
        code_type="code_block",
        expected_type=CodeBlock,
    ).code_elements[0]

    injected1 = parse(
        filename="<file2>",
        code="const b = 1;\n",
        code_type="code_block",
        expected_type=CodeBlock,
    ).code_elements[0]

    if_block = block.code_elements[2].code_elm
    assert isinstance(if_block, CodeElementIf)

    foo_func = block.code_elements[4].code_elm
    assert isinstance(foo_func, CodeElementFunction)

    injections = {
        id(block.code_elements[0].code_elm): [injected0, injected1],
        id(block.code_elements[1].code_elm): [],
        id(block.code_elements[2].code_elm): [injected0],
        id(if_block.main_code_block.code_elements[0].code_elm): [injected1],
        id(foo_func.code_block.code_elements[0].code_elm): [injected0],
    }
    # We pass wrong types below (e.g., CodeBlock instead of CodeElement) to simplify the test.
    scoped_elm = CodeElementScoped(
        scope=ScopedName.from_string("main"),
        code_elements=[block],  # type: ignore
    )
    block = inject_code_elements(  # type: ignore
        ast=scoped_elm,  # type: ignore
        injections=injections,
    ).code_elements[0]
    assert (
        block.format(allowed_line_length=100)
        == """\
let (x, local y) = f();
const a = 0;
const b = 1;
let z = 1;
if (1 != 0) {
    tempvar z = 0;
    const b = 1;
}
const a = 0;
local x = 1;
func foo() {
    tempvar y = 0;
    const a = 0;
}
"""
    )
