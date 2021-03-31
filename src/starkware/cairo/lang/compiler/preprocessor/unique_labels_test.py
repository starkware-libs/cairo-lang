from starkware.cairo.lang.compiler.preprocessor.preprocessor_test_utils import PRIME, preprocess_str


def test_unique_label_creator():
    program = preprocess_str(code="""
namespace B:
    func foo(x, y) -> (res):
        if x == 0:
            if y == 0:
                return (res=0)
            else:
                return (res=1)
            end
        else:
            if y == 0:
                return (res=2)
            else:
                return (res=3)
            end
        end
    end
end
""", prime=PRIME)
    assert program.format() == """\
jmp rel 10 if [fp + (-4)] != 0
jmp rel 5 if [fp + (-3)] != 0
[ap] = 0; ap++
ret
[ap] = 1; ap++
ret
jmp rel 5 if [fp + (-3)] != 0
[ap] = 2; ap++
ret
[ap] = 3; ap++
ret
"""
