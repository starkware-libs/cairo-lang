from compiler import encode, instruction
from vm import cairo_runner
import pprint as pp

def printdict():
    PRIME = 2 ** 251 + 17 * 2 ** 192 + 1
    code = """
func main():
    [ap] = 1; ap++
    [ap] = 1; ap++
    [ap] = [ap - 3] - 1
    ret
end
"""
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
