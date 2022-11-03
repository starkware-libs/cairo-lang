from collections import namedtuple
from dataclasses import make_dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from starkware.cairo.lang.compiler.ast.cairo_types import CairoType, TypeFelt, TypePointer
from starkware.cairo.lang.compiler.identifier_definition import StructDefinition
from starkware.cairo.lang.compiler.parser import parse_type
from starkware.cairo.lang.compiler.type_system import mark_type_resolved
from starkware.starknet.compiler.compile import compile_starknet_files
from starkware.starknet.public.abi import AbiType, get_selector_from_name
from starkware.starknet.public.abi_structs import struct_definition_from_abi_entry
from starkware.starknet.services.api.contract_class import ContractClass
from starkware.starknet.testing.objects import Dataclass

EventIdentifier = Union[str, int]
RAW_OUTPUT_ARG_LIST = ["retdata_size", "retdata"]


class StructManager:
    def __init__(self, abi: AbiType):
        self._struct_definition_mapping = {
            abi_entry["name"]: struct_definition_from_abi_entry(abi_entry=abi_entry)
            for abi_entry in abi
            if abi_entry["type"] == "struct"
        }

        # Cached contract structs.
        self._contract_structs: Dict[str, type] = {}

    def __contains__(self, key: str) -> bool:
        return key in self._struct_definition_mapping

    def get_struct_definition(self, name: str) -> StructDefinition:
        return self._struct_definition_mapping[name]

    def get_contract_struct(self, name: str) -> type:
        """
        Returns a named tuple representing the Cairo struct whose name is given.
        """
        if name not in self._contract_structs:
            # Cache contract struct.
            self._contract_structs[name] = self._build_contract_struct(name=name)

        return self._contract_structs[name]

    def _build_contract_struct(self, name: str) -> type:
        """
        Builds and returns a named tuple representing the Cairo struct whose name is given.
        """
        struct_def = self._struct_definition_mapping[name]
        return namedtuple(typename=name, field_names=struct_def.members.keys())


class EventManager:
    def __init__(self, abi: AbiType):
        self._abi_event_mapping = {
            abi_entry["name"]: abi_entry for abi_entry in abi if abi_entry["type"] == "event"
        }

        # A mapping from event selector to event name.
        self._selector_to_name: Dict[int, str] = {
            get_selector_from_name(name): name for name in self._abi_event_mapping.keys()
        }

        # Cached contract events and argument types.
        self._contract_events: Dict[str, Dataclass] = {}
        self._event_name_to_argument_types: Dict[str, List[CairoType]] = {}

    def __contains__(self, identifier: EventIdentifier) -> bool:
        if isinstance(identifier, str):
            return identifier in self._abi_event_mapping

        return identifier in self._selector_to_name

    def get_contract_event(self, identifier: EventIdentifier) -> Dataclass:
        """
        Returns a named tuple representing the event whose name is given.
        """
        name = self._get_event_name(identifier=identifier)
        if name not in self._contract_events:
            # Cache event.
            self._process_event(name=name)

        return self._contract_events[name]

    def get_event_argument_types(self, identifier: EventIdentifier) -> List[CairoType]:
        """
        Returns the argument Cairo types of the given event.
        """
        name = self._get_event_name(identifier=identifier)
        if name not in self._event_name_to_argument_types:
            # Cache argument types.
            self._process_event(name=name)

        return self._event_name_to_argument_types[name]

    def _process_event(self, name: str):
        """
        Processes the given event and caches its argument types and its representative named tuple.
        """
        event_abi = self._abi_event_mapping[name]
        names, types = parse_arguments(arguments_abi=event_abi["keys"] + event_abi["data"])

        self._event_name_to_argument_types[name] = types
        self._contract_events[name] = make_dataclass(cls_name=name, fields=names)

    def _get_event_name(self, identifier: EventIdentifier) -> str:
        return identifier if isinstance(identifier, str) else self._selector_to_name[identifier]


def parse_arguments(arguments_abi: List) -> Tuple[List[str], List[CairoType]]:
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
            # Remove last argument.
            size_arg_actual_name = arg_names.pop()
            actual_type = arg_types.pop()
            # Allow _size suffix (instead of _len) for @raw_output functions.
            if size_arg_actual_name == f"{name}_size":
                assert name != "calldata", "Direct raw_input function calls are not supported."
                assert [size_arg_actual_name, name] == RAW_OUTPUT_ARG_LIST
                assert len(arguments_abi) == 2
                # In case of @raw_output keep retdata_size argument.
                arg_names.append(size_arg_actual_name)
                arg_types.append(actual_type)
            else:
                # Make sure the removed last argument was {name}_len.
                size_arg_expected_name = f"{name}_len"
                assert (
                    size_arg_actual_name == size_arg_expected_name
                ), f"Array size argument {size_arg_expected_name} must appear right before {name}."

            assert isinstance(actual_type, TypeFelt), (
                f"Array size entry {size_arg_actual_name} expected to be type felt. Got: "
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


def get_abi(contract_class: ContractClass) -> AbiType:
    assert contract_class.abi is not None, "Missing ABI."
    return contract_class.abi


def get_contract_class(
    source: Optional[str] = None,
    contract_class: Optional[ContractClass] = None,
    cairo_path: Optional[List[str]] = None,
    disable_hint_validation: bool = False,
) -> ContractClass:
    """
    Given either a ContractClass instance or a source file path, returns the respective
    ContractClass instance.
    """
    assert (source is None) != (
        contract_class is None
    ), "Exactly one of source, contract_class should be supplied."
    if contract_class is None:
        contract_class = compile_starknet_files(
            files=[source],
            debug_info=True,
            cairo_path=cairo_path,
            disable_hint_validation=disable_hint_validation,
        )
        source = None
        cairo_path = None
    assert cairo_path is None, "The cairo_path argument can only be used with the source argument."
    assert contract_class is not None
    return contract_class
