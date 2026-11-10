import functools
import os

from starkware.cairo.lang.compiler.program import Program

CIRCUIT_APPLICATIVE_BOOTLOADER_COMPILED_PATH = os.path.join(
    os.path.dirname(__file__),
    "circuit_applicative_bootloader",
    "circuit_applicative_bootloader_compiled.json",
)
SIMPLE_BOOTLOADER_COMPILED_PATH = os.path.join(
    os.path.dirname(__file__), "simple_bootloader", "simple_bootloader_compiled.json"
)
NO_BUILTIN_SIMULATION_SIMPLE_BOOTLOADER_COMPILED_PATH = os.path.join(
    os.path.dirname(__file__),
    "simple_bootloader",
    "no_builtin_simulation_simple_bootloader_compiled.json",
)
LEAF_SIMPLE_BOOTLOADER_COMPILED_PATH = os.path.join(
    os.path.dirname(__file__), "simple_bootloader", "leaf_simple_bootloader_compiled.json"
)


@functools.lru_cache(None)
def get_circuit_applicative_bootloader_program() -> Program:
    with open(CIRCUIT_APPLICATIVE_BOOTLOADER_COMPILED_PATH, "r") as file:
        return Program.Schema().loads(file.read())


def get_simple_bootloader_program() -> Program:
    with open(SIMPLE_BOOTLOADER_COMPILED_PATH, "r") as file:
        return Program.Schema().loads(file.read())


def get_no_builtin_simulation_simple_bootloader_program() -> Program:
    with open(NO_BUILTIN_SIMULATION_SIMPLE_BOOTLOADER_COMPILED_PATH, "r") as file:
        return Program.Schema().loads(file.read())
