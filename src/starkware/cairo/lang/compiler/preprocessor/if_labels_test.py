from starkware.cairo.lang.compiler.preprocessor.preprocessor_test_utils import PRIME, preprocess_str


def test_if_labels_are_set():
    program = preprocess_str(
        code="""
namespace B {
    func foo(x, y) -> (res: felt) {
        if (x == 0) {
            if (y == 0) {
                return (res=0);
            } else {
                return (res=1);
            }
        } else {
            if (y == 0) {
                return (res=2);
            } else {
                return (res=3);
            }
        }
    }
}
func main() {
    B.foo(1, 2);
    ret;
}
""",
        prime=PRIME,
    )
    assert (
        program.format()
        == """\
jmp rel 10 if [fp + (-4)] != 0;
jmp rel 5 if [fp + (-3)] != 0;
[ap] = 0, ap++;
ret;
[ap] = 1, ap++;
ret;
jmp rel 5 if [fp + (-3)] != 0;
[ap] = 2, ap++;
ret;
[ap] = 3, ap++;
ret;
[ap] = 1, ap++;
[ap] = 2, ap++;
call rel -22;
ret;
"""
    )
