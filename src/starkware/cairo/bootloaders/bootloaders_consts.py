import functools
import os

from starkware.cairo.lang.compiler.program import Program

APPLICATIVE_BOOTLOADER_COMPILED_PATH = os.path.join(
    os.path.dirname(__file__), "applicative_bootloader", "applicative_bootloader_compiled.json"
)
SIMPLE_BOOTLOADER_COMPILED_PATH = os.path.join(
    os.path.dirname(__file__), "simple_bootloader", "simple_bootloader_compiled.json"
)
NO_BUILTIN_SIMULATION_SIMPLE_BOOTLOADER_COMPILED_PATH = os.path.join(
    os.path.dirname(__file__),
    "simple_bootloader",
    "no_builtin_simulation_simple_bootloader_compiled.json",
)


@functools.lru_cache(None)
def get_applicative_bootloader_program() -> Program:
    with open(APPLICATIVE_BOOTLOADER_COMPILED_PATH, "r") as file:
        return Program.Schema().loads(file.read())


def get_simple_bootloader_program() -> Program:
    with open(SIMPLE_BOOTLOADER_COMPILED_PATH, "r") as file:
        return Program.Schema().loads(file.read())


def get_no_builtin_simulation_simple_bootloader_program() -> Program:
    with open(NO_BUILTIN_SIMULATION_SIMPLE_BOOTLOADER_COMPILED_PATH, "r") as file:
        return Program.Schema().loads(file.read())
