import pprint as pp
import sys
# TODO See if its worth it to add __init__.py files to create a package
sys.path.insert(1, './src/starkware/cairo/lang')

from compiler import encode, instruction
from vm import cairo_runner

PRIME = 2 ** 251 + 17 * 2 ** 192 + 1
code = """
func main():
    [ap] = 25; ap++
    %{
        import math
        memory[ap] = int(math.sqrt(memory[ap - 1]))
    %}
    [ap - 1] = [ap] * [ap]; ap++
    ret
end
"""

def printdict():
    runner=cairo_runner.get_runner_from_code(code, layout='plain', prime=PRIME)
    mem = dict(runner.memory)
    print(code)
    pp.pprint({k:(hex(v) if type(v) == type(int()) else v) for k,v in mem.items()})

    print("{")
    it = iter(mem.items())
    for keyval in it:
        print(keyval[0], '-> ', end='')
        if type(keyval[1]) != type(int()):
            print('[', keyval[1], ']')
        elif keyval[0].segment_index == 1:
            print(hex(keyval[1]))
        elif type(keyval[1]) == type(int()):
            try:
                pp.pprint(vars(encode.decode_instruction(keyval[1], None)))
            except AssertionError:
                pp.pprint(vars(encode.decode_instruction(keyval[1], next(it)[1])))

printdict()
