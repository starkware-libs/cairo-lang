import itertools
import os
from functools import lru_cache
from typing import Callable

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.common.structs import CairoStructFactory, CairoStructProxy
from starkware.cairo.lang.builtins.hash.hash_builtin_runner import HashBuiltinRunner
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo_files
from starkware.cairo.lang.compiler.identifier_definition import ConstDefinition
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.vm.crypto import pedersen_hash
from starkware.starknet.core.os.contract_class.deprecated_class_hash import (
    compute_deprecated_hinted_class_hash,
    get_builtins_as_integers,
    get_contract_entry_points,
)
from starkware.starknet.core.os.contract_class.utils import ClassHashType, class_hash_cache_ctx_var
from starkware.starknet.public.abi import starknet_keccak
from starkware.starknet.services.api.contract_class.contract_class import (
    DeprecatedCompiledClass,
    EntryPointType,
)

CAIRO_FILE = os.path.join(os.path.dirname(__file__), "deprecated_compiled_class.cairo")


@lru_cache()
def load_program() -> Program:
    return compile_cairo_files(
        [CAIRO_FILE],
        prime=DEFAULT_PRIME,
        main_scope=ScopedName.from_string(
            "starkware.starknet.core.os.contract_class.deprecated_compiled_class"
        ),
    )


def get_deprecated_contract_class_struct(
    identifiers: IdentifierManager, contract_class: DeprecatedCompiledClass
) -> CairoStructProxy:
    """
    Returns the serialization of a contract as a list of field elements.
    """
    path = "starkware.starknet.core.os.contract_class.deprecated_compiled_class"
    structs = CairoStructFactory(
        identifiers=identifiers,
        additional_imports=[
            f"{path}.DeprecatedCompiledClass",
            f"{path}.DeprecatedContractEntryPoint",
        ],
    ).structs

    DEPRECATED_COMPILED_CLASS_VERSION_IDENT = identifiers.get_by_full_name(
        ScopedName.from_string(f"{path}.DEPRECATED_COMPILED_CLASS_VERSION")
    )
    assert isinstance(DEPRECATED_COMPILED_CLASS_VERSION_IDENT, ConstDefinition)

    external_functions, l1_handlers, constructors = (
        get_contract_entry_points(
            structs=structs,
            contract_class=contract_class,
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

    builtin_list = get_builtins_as_integers(contract_class=contract_class)
    return structs.DeprecatedCompiledClass(
        compiled_class_version=DEPRECATED_COMPILED_CLASS_VERSION_IDENT.value,
        n_external_functions=len(external_functions),
        external_functions=flat_external_functions,
        n_l1_handlers=len(l1_handlers),
        l1_handlers=flat_l1_handlers,
        n_constructors=len(constructors),
        constructors=flat_constructors,
        n_builtins=len(builtin_list),
        builtin_list=builtin_list,
        hinted_class_hash=compute_deprecated_hinted_class_hash(contract_class=contract_class),
        bytecode_length=len(contract_class.program.data),
        bytecode_ptr=contract_class.program.data,
    )


def cairo_compute_deprecated_class_hash(
    contract_class: DeprecatedCompiledClass, hash_func: Callable[[int, int], int] = pedersen_hash
) -> int:
    cache = class_hash_cache_ctx_var.get()
    if cache is None:
        return cairo_compute_deprecated_class_hash_inner(
            contract_class=contract_class, hash_func=hash_func
        )

    contract_class_bytes = contract_class.dumps(sort_keys=True).encode()
    key = (
        ClassHashType.DEPRECATED_COMPILED_CLASS,
        (starknet_keccak(data=contract_class_bytes), hash_func),
    )

    if key not in cache:
        cache[key] = cairo_compute_deprecated_class_hash_inner(
            contract_class=contract_class, hash_func=hash_func
        )

    return cache[key]


def cairo_compute_deprecated_class_hash_inner(
    contract_class: DeprecatedCompiledClass, hash_func: Callable[[int, int], int]
) -> int:
    program = load_program()
    compiled_class_struct = get_deprecated_contract_class_struct(
        identifiers=program.identifiers, contract_class=contract_class
    )
    runner = CairoFunctionRunner(program)

    hash_builtin = HashBuiltinRunner(
        name="custom_hasher", included=True, ratio=32, hash_func=hash_func
    )
    runner.builtin_runners["hash_builtin"] = hash_builtin
    hash_builtin.initialize_segments(runner)

    runner.run(
        "starkware.starknet.core.os.contract_class.deprecated_compiled_class."
        + "deprecated_compiled_class_hash",
        hash_ptr=hash_builtin.base,
        compiled_class=compiled_class_struct,
        use_full_name=True,
        verify_secure=False,
    )
    _, class_hash = runner.get_return_values(2)
    return class_hash
