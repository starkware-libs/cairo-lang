from typing import Any, Iterable, List, Tuple, Union

from starkware.cairo.lang.compiler.ast.cairo_types import CairoType, TypeFelt, TypePointer
from starkware.cairo.lang.compiler.parser import parse_type
from starkware.cairo.lang.compiler.type_system import mark_type_resolved


def parse_arguments(arguments_abi: dict) -> Tuple[List[str], List[CairoType]]:
    """
    Given the input or output field of a StarkNet contract function ABI,
    computes the arguments that the python proxy function should accept.
    In particular, an array input that has two inputs in the
    original ABI (foo_len: felt, foo: felt*) will be converted to a single argument foo.

    Returns the argument names and their Cairo types in two separate lists.
    """
    arg_names: List[str] = []
    arg_types: List[CairoType] = []
    for arg_entry in arguments_abi:
        name = arg_entry["name"]
        arg_type = mark_type_resolved(parse_type(code=arg_entry["type"]))
        if isinstance(arg_type, TypePointer):
            size_arg_actual_name = arg_names.pop()
            actual_type = arg_types.pop()
            # Make sure the last argument was {name}_len, and remove it.
            size_arg_name = f"{name}_len"
            assert (
                size_arg_actual_name == size_arg_name
            ), f"Array size argument {size_arg_name} must appear right before {name}."

            assert isinstance(actual_type, TypeFelt), (
                f"Array size entry {size_arg_name} expected to be type felt. Got: "
                f"{actual_type.format()}."
            )

        arg_names.append(name)
        arg_types.append(arg_type)

    return arg_names, arg_types


def flatten(name: str, value: Union[Any, Iterable], max_depth: int = 30) -> List[Any]:
    # Use max_depth to avoid, for example, a list that points to itself.
    assert max_depth > 0, f"Exceeded maximun depth while parsing argument {name}."
    if not isinstance(value, Iterable):
        return [value]

    res = []
    for elm in value:
        res.extend(flatten(name=name, value=elm, max_depth=max_depth - 1))

    return res
