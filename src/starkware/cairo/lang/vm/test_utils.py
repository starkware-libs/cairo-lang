from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.relocatable import MaybeRelocatableDict, RelocatableValue
from starkware.cairo.lang.vm.vm import RunContext, VirtualMachine

PRIME = 2**64 + 13


def run_program_in_vm(
    program: Program,
    steps: int,
    *,
    pc=RelocatableValue(0, 10),
    ap=100,
    fp=100,
    extra_mem={},
    prime=PRIME,
):
    # Set memory[fp - 1] to an arbitrary value, since [fp - 1] is assumed to be set.
    memory: MaybeRelocatableDict = {
        **{pc + i: v for i, v in enumerate(program.data)},
        fp - 1: 1234,
        **extra_mem,
    }
    context = RunContext(
        pc=pc,
        ap=ap,
        fp=fp,
        memory=MemoryDict(memory),
        prime=prime,
    )

    vm = VirtualMachine(program, context, {})
    for _ in range(steps):
        vm.step()
    return vm
