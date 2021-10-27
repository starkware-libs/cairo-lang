import functools
import itertools
import sys
import types
from collections import namedtuple
from typing import Any, Callable, Dict, Iterator, List, Tuple, Union

from typeguard import check_type

from starkware.cairo.lang.compiler.ast.cairo_types import (
    CairoType,
    TypeFelt,
    TypePointer,
    TypeStruct,
    TypeTuple,
)
from starkware.cairo.lang.compiler.parser import parse_type
from starkware.cairo.lang.compiler.type_system import mark_type_resolved
from starkware.python.utils import safe_zip
from starkware.starknet.public.abi_structs import struct_definition_from_abi_entry
from starkware.starknet.testing.contract_utils import flatten, parse_arguments
from starkware.starknet.testing.objects import StarknetTransactionExecutionInfo
from starkware.starknet.testing.state import CastableToAddress, StarknetState

# Type annotation for a function that reconstructs the retdata - from a flat list to its Cairo-like
# structure; gets a list of values and returns a named tuple representing the retdata of a StarkNet
# function, filled with those values.
RetdataReconstructFunc = Callable[[List[int]], Tuple]

# Represents Python types, in particular those that are parallel to the cairo ones:
# int, tuple and list (matching the cairo types TypeFelt, TypeTuple/TypeStruct and TypePointer).
PythonType = Any


class StarknetContract:
    """
    A high level interface to a StarkNet contract used for testing. Allows invoking functions.
    Example:
      contract_definition = compile_starknet_files(...)
      state = await StarknetState.empty()
      contract_address = await state.deploy(contract_definition=contract_definition)
      contract = StarknetContract(
          state=state, abi=contract_definition.abi, contract_address=contract_address)

      await contract.foo(a=1, b=[2, 3]).invoke()
    """

    def __init__(self, state: StarknetState, abi: List[Any], contract_address: CastableToAddress):
        self.state = state

        self._abi_function_mapping = {
            abi_entry["name"]: abi_entry for abi_entry in abi if abi_entry["type"] == "function"
        }
        self._struct_definition_mapping = {
            abi_entry["name"]: struct_definition_from_abi_entry(abi_entry=abi_entry)
            for abi_entry in abi
            if abi_entry["type"] == "struct"
        }

        # Cached contract functions and structs.
        self._contract_functions: Dict[str, Callable] = {}
        self._contract_structs: Dict[str, type] = {}

        if isinstance(contract_address, str):
            contract_address = int(contract_address, 16)
        assert isinstance(contract_address, int)
        self.contract_address = contract_address

    def __dir__(self):
        return object.__dir__(self) + list(self._abi_function_mapping.keys())

    def __getattr__(self, name: str):
        if name in self._abi_function_mapping:
            if name not in self._contract_functions:
                # Cache contract function.
                self._contract_functions[name] = self._build_contract_function(
                    function_abi=self._abi_function_mapping[name]
                )

            return self._contract_functions[name]
        elif name in self._struct_definition_mapping:
            return self.get_contract_struct(name=name)
        else:
            raise AttributeError

    def get_contract_struct(self, name: str) -> type:
        """
        Returns a named tuple representing the Cairo struct whose name is given
        """
        assert name in self._struct_definition_mapping, f"Struct {name} is not defined."
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

    def _build_contract_function(self, function_abi: dict) -> Callable:
        """
        Builds a function object that acts as a proxy for a StarkNet contract function.
        """
        name = function_abi["name"]
        # Parse calldata and retdata arguments.
        arg_names, arg_types = parse_arguments(arguments_abi=function_abi["inputs"])
        retdata_arg_names, retdata_arg_types = parse_arguments(
            arguments_abi=function_abi["outputs"]
        )

        # Build Pythonic type annotations to those arguments, matching their Cairo types.
        # I.e., Cairo Array <> Python List; Cairo tuple/struct <> Python Tuple;
        # Cairo felt <> Python int.
        # This will be added to the contract function info, and be used to validate the structure
        # of the user's input.
        calldata_annotations: Dict[str, PythonType] = {
            name: self._get_annotation(arg_type=arg_type)
            for name, arg_type in safe_zip(arg_names, arg_types)
        }
        retdata_annotations: List[PythonType] = [
            self._get_annotation(arg_type=arg_type) for arg_type in retdata_arg_types
        ]

        def template():
            all_locals = locals()
            args = {arg_name: all_locals[arg_name] for arg_name in arg_names}
            return self._build_function_call(
                function_abi=function_abi,
                calldata_annotations=calldata_annotations,
                args=args,
                retdata_arg_names=retdata_arg_names,
                retdata_arg_types=retdata_arg_types,
            )

        # Create a function like template(), but with extra arguments.
        if sys.version_info.major != 3:
            raise Exception("Must be using Python3.")
        posonlyargcount = (0,) if sys.version_info.minor >= 8 else ()
        func_code = types.CodeType(  # type: ignore
            len(arg_names),  # Arg: argcount.
            *posonlyargcount,  # type: ignore
            0,  # Arg: kwonlyargcount.
            len(arg_names),  # Arg: nlocals.
            template.__code__.co_stacksize + len(arg_names),  # Arg: stacksize.
            template.__code__.co_flags,  # Arg: flags.
            template.__code__.co_code,  # Arg: codestring.
            template.__code__.co_consts,  # Arg: constants.
            template.__code__.co_names,  # Arg: names.
            tuple(arg_names),  # Arg: varnames.
            template.__code__.co_filename,  # Arg: filename.
            name,  # Arg: name.
            template.__code__.co_firstlineno,  # Arg: firstlineno.
            template.__code__.co_lnotab,  # Arg: lnotab.
            template.__code__.co_freevars,  # Arg: freevars.
            template.__code__.co_cellvars,  # Arg: cellvars.
        )

        closure = template.__closure__  # type: ignore
        func = types.FunctionType(code=func_code, globals=globals(), closure=closure)
        func.__annotations__ = {**calldata_annotations, "return": tuple(retdata_annotations)}

        return func

    def _get_annotation(self, arg_type: CairoType, is_nested: bool = False) -> PythonType:
        """
        Returns the Pythonic type annotation of the given Cairo type.
        """
        if isinstance(arg_type, TypeFelt):
            return int
        if isinstance(arg_type, TypePointer):
            assert not is_nested, "Arrays are not supported as members of another type."
            pointee_type = self._get_annotation(arg_type=arg_type.pointee, is_nested=True)
            return List[pointee_type]  # type: ignore
        if isinstance(arg_type, TypeTuple):
            return Tuple[
                tuple(
                    self._get_annotation(arg_type=member, is_nested=True)
                    for member in arg_type.members
                )
            ]
        if isinstance(arg_type, TypeStruct):
            struct_def = self._struct_definition_mapping[arg_type.scope.path[-1]]
            return Tuple[
                tuple(
                    self._get_annotation(arg_type=member.cairo_type, is_nested=True)
                    for member in struct_def.members.values()
                )
            ]

        raise NotImplementedError

    def _build_function_call(
        self,
        function_abi: dict,
        calldata_annotations: Dict[str, PythonType],
        args: dict,
        retdata_arg_names: List[str],
        retdata_arg_types: List[CairoType],
    ):
        """
        Builds a StarknetContractFunctionInvocation object, representing a call to a StarkNet
        contract with a particular state and set of inputs.
        """
        # Prepare calldata.
        calldata: List[int] = []
        for input_entry in function_abi["inputs"]:
            name = input_entry["name"]
            arg_cairo_type = mark_type_resolved(parse_type(code=input_entry["type"]))
            if name not in args:
                continue

            value = args[name]
            # Checks the full structure of the value.
            check_type(
                argname=f"argument {name}", value=value, expected_type=calldata_annotations[name]
            )
            value = flatten(name=name, value=value)
            if isinstance(arg_cairo_type, TypePointer):
                calldata.append(len(value))

            calldata.extend(value)

        # Prepare the retdata reconstruction function: a function that turns a flat list of return
        # values to a Pythonic version of its original Cairo structure.
        # We build it here to keep StarknetContractFunctionInvocation neat.
        function_name = function_abi["name"]
        retdata_reconstructor: RetdataReconstructFunc = functools.partial(
            self._build_retdata,
            retdata_tuple=namedtuple(f"{function_name}_return_type", retdata_arg_names),
            arg_types=retdata_arg_types,
        )

        return StarknetContractFunctionInvocation(
            state=self.state,
            contract_address=self.contract_address,
            function_abi=function_abi,
            calldata=calldata,
            retdata_reconstructor=retdata_reconstructor,
        )

    def _build_retdata(
        self, retdata: List[int], retdata_tuple: type, arg_types: List[CairoType]
    ) -> Tuple:
        """
        Reconstructs a Pythonic variant of the original Cairo structure of the retdata, deduced by
        the arguments Cairo types, and fills it with the given (flat list of) return values.
        """

        def build_retdata_arg(
            arg_type: CairoType, retdata: Iterator[int]
        ) -> Union[int, tuple, List[int]]:
            if isinstance(arg_type, TypeFelt):
                return next(retdata)
            if isinstance(arg_type, TypeTuple):
                return tuple(
                    build_retdata_arg(arg_type=member, retdata=retdata)
                    for member in arg_type.members
                )
            if isinstance(arg_type, TypeStruct):
                struct_name = arg_type.scope.path[-1]
                struct_def = self._struct_definition_mapping[struct_name]
                contract_struct = self.get_contract_struct(name=struct_name)
                return contract_struct(
                    *(
                        build_retdata_arg(arg_type=member.cairo_type, retdata=retdata)
                        for member in struct_def.members.values()
                    )
                )
            if isinstance(arg_type, TypePointer) and isinstance(arg_type.pointee, TypeFelt):
                arr_len = next(retdata)
                # Return the next arr_len elements from retdata.
                return list(itertools.islice(retdata, arr_len))

            raise NotImplementedError

        retdata_iterator = iter(retdata)
        res = [
            build_retdata_arg(arg_type=arg_type, retdata=retdata_iterator) for arg_type in arg_types
        ]
        # Make sure the iterator is empty.
        assert next(retdata_iterator, None) is None, "Too many return values."
        return retdata_tuple(*res)


class StarknetContractFunctionInvocation:
    """
    A call to a StarkNet contract with a particular state and set of inputs
    """

    def __init__(
        self,
        state: StarknetState,
        contract_address: CastableToAddress,
        function_abi: dict,
        calldata: List[int],
        retdata_reconstructor: RetdataReconstructFunc,
    ):
        self.state = state
        self.contract_address = contract_address
        self.function_abi = function_abi
        self.calldata = calldata
        self.retdata_reconstructor = retdata_reconstructor

    async def call(
        self, caller_address: int = 0, signature: List[int] = None
    ) -> StarknetTransactionExecutionInfo:
        """
        Executes the function call, without changing the state.
        """
        execution_info = await self.state.copy().invoke_raw(
            contract_address=self.contract_address,
            selector=self.function_abi["name"],
            calldata=self.calldata,
            caller_address=caller_address,
            signature=signature,
        )
        return StarknetTransactionExecutionInfo.from_internal(
            tx_execution_info=execution_info,
            result=self.retdata_reconstructor(execution_info.retdata),
        )

    async def invoke(
        self, caller_address: int = 0, signature: List[int] = None
    ) -> StarknetTransactionExecutionInfo:
        """
        Executes the function call, and apply changes on the state.
        """
        execution_info = await self.state.invoke_raw(
            contract_address=self.contract_address,
            selector=self.function_abi["name"],
            calldata=self.calldata,
            caller_address=caller_address,
            signature=signature,
        )
        return StarknetTransactionExecutionInfo.from_internal(
            tx_execution_info=execution_info,
            result=self.retdata_reconstructor(execution_info.retdata),
        )
