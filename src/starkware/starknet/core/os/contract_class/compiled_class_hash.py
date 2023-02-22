import itertools
import json
import os
from functools import lru_cache
from typing import List

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.common.structs import CairoStructFactory, CairoStructProxy
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo_files
from starkware.cairo.lang.compiler.identifier_definition import ConstDefinition
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.python.utils import as_non_optional, from_bytes
from starkware.starknet.core.os.contract_class.class_hash import (
    ClassHashType,
    class_hash_cache_ctx_var,
)
from starkware.starknet.public.abi import starknet_keccak
from starkware.starknet.services.api.contract_class.contract_class import (
    CompiledClass,
    EntryPointType,
)

CAIRO_FILE = os.path.join(os.path.dirname(__file__), "compiled_class.cairo")


@lru_cache()
def load_program() -> Program:
    return compile_cairo_files(
        [CAIRO_FILE],
        prime=DEFAULT_PRIME,
        main_scope=ScopedName.from_string(
            "starkware.starknet.core.os.contract_class.compiled_class"
        ),
    )


def compute_compiled_class_hash(compiled_class: CompiledClass) -> int:
    """
    Computes the compiled class hash.
    """
    cache = class_hash_cache_ctx_var.get()
    if cache is None:
        return _compute_compiled_class_hash_inner(compiled_class=compiled_class)

    compiled_class_bytes = compiled_class.dumps(sort_keys=True).encode()
    key = (ClassHashType.COMPILED_CLASS, starknet_keccak(data=compiled_class_bytes))

    if key not in cache:
        cache[key] = _compute_compiled_class_hash_inner(compiled_class=compiled_class)

    return cache[key]


def _compute_compiled_class_hash_inner(compiled_class: CompiledClass) -> int:
    program = load_program()
    compiled_class_struct = get_compiled_class_struct(
        identifiers=program.identifiers, compiled_class=compiled_class
    )
    runner = CairoFunctionRunner(program=program)

    runner.run(
        "starkware.starknet.core.os.contract_class.compiled_class.compiled_class_hash",
        poseidon_ptr=runner.poseidon_builtin.base,
        compiled_class=compiled_class_struct,
        use_full_name=True,
        verify_secure=False,
    )
    _, class_hash = runner.get_return_values(2)
    return class_hash


def _compute_hinted_compiled_class_hash(compiled_class: CompiledClass) -> int:
    """
    Computes the hash of the compiled class, including hints.
    """
    input_to_hash = dict(program=compiled_class.program.dump())
    return starknet_keccak(data=json.dumps(input_to_hash, sort_keys=True).encode())


def _get_contract_entry_points(
    structs: CairoStructProxy,
    compiled_class: CompiledClass,
    entry_point_type: EntryPointType,
) -> List[CairoStructProxy]:
    # Check validity of entry points.
    program_length = len(compiled_class.program.data)
    entry_points = compiled_class.entry_points_by_type[entry_point_type]
    for entry_point in entry_points:
        assert (
            0 <= entry_point.offset < program_length
        ), f"Invalid entry point offset {entry_point.offset}, len(program_data)={program_length}."

    return [
        structs.CompiledClassEntryPoint(
            selector=entry_point.selector,
            offset=entry_point.offset,
            n_builtins=len(as_non_optional(entry_point.builtins)),
            builtin_list=[
                from_bytes(builtin.encode("ascii"))
                for builtin in as_non_optional(entry_point.builtins)
            ],
        )
        for entry_point in entry_points
    ]


def get_compiled_class_struct(
    identifiers: IdentifierManager, compiled_class: CompiledClass
) -> CairoStructProxy:
    """
    Returns the serialization of a compiled class as a list of field elements.
    """
    structs = CairoStructFactory(
        identifiers=identifiers,
        additional_imports=[
            "starkware.starknet.core.os.contract_class.compiled_class.CompiledClass",
            "starkware.starknet.core.os.contract_class.compiled_class.CompiledClassEntryPoint",
        ],
    ).structs

    COMPILED_CLASS_VERSION_IDENT = identifiers.get_by_full_name(
        ScopedName.from_string(
            "starkware.starknet.core.os.contract_class.compiled_class.COMPILED_CLASS_VERSION"
        )
    )
    assert isinstance(COMPILED_CLASS_VERSION_IDENT, ConstDefinition)

    external_functions, l1_handlers, constructors = (
        _get_contract_entry_points(
            structs=structs,
            compiled_class=compiled_class,
            entry_point_type=entry_point_type,
        )
        for entry_point_type in (
            EntryPointType.EXTERNAL,
            EntryPointType.L1_HANDLER,
            EntryPointType.CONSTRUCTOR,
        )
    )
    flat_external_functions, flat_l1_handlers, flat_constructors = (
        list(itertools.chain.from_iterable(entry_points))
        for entry_points in (external_functions, l1_handlers, constructors)
    )

    return structs.CompiledClass(
        compiled_class_version=COMPILED_CLASS_VERSION_IDENT.value,
        n_external_functions=len(external_functions),
        external_functions=flat_external_functions,
        n_l1_handlers=len(l1_handlers),
        l1_handlers=flat_l1_handlers,
        n_constructors=len(constructors),
        constructors=flat_constructors,
        hinted_compiled_class_hash=_compute_hinted_compiled_class_hash(
            compiled_class=compiled_class
        ),
        bytecode_length=len(compiled_class.program.data),
        bytecode_ptr=compiled_class.program.data,
    )
