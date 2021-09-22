import sys
import types
from collections import namedtuple
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from starkware.starknet.testing.state import StarknetState


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

    def __init__(self, state: StarknetState, abi: List[Any], contract_address: Union[int, str]):
        self.state = state

        self._abi_function_mapping = {
            abi_entry["name"]: abi_entry for abi_entry in abi if abi_entry["type"] == "function"
        }

        if isinstance(contract_address, str):
            contract_address = int(contract_address, 16)
        assert isinstance(contract_address, int)
        self.contract_address = contract_address

    def __dir__(self):
        return object.__dir__(self) + list(self._abi_function_mapping.keys())

    def __getattr__(self, name: str):
        if name not in self._abi_function_mapping:
            raise AttributeError
        return self._build_contract_function(function_abi=self._abi_function_mapping[name])

    def _build_contract_function(self, function_abi: dict):
        """
        Builds a function object that acts as a proxy for a StarkNet contract function.
        """
        name = function_abi["name"]
        args, type_annotations = self._get_function_args(function_abi=function_abi)
        arg_names = tuple(args.keys())
        ret_tuple = self._generate_return_named_tuple(function_abi)

        def template():
            all_locals = locals()
            args = {arg_name: all_locals[arg_name] for arg_name in arg_names}
            return self._build_function_call(
                function_abi=function_abi, args=args, ret_tuple=ret_tuple
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
            arg_names,  # Arg: varnames.
            template.__code__.co_filename,  # Arg: filename.
            name,  # Arg: name.
            template.__code__.co_firstlineno,  # Arg: firstlineno.
            template.__code__.co_lnotab,  # Arg: lnotab.
            template.__code__.co_freevars,  # Arg: freevars.
            template.__code__.co_cellvars,  # Arg: cellvars.
        )

        closure = template.__closure__  # type: ignore
        func = types.FunctionType(code=func_code, globals=globals(), closure=closure)
        func.__annotations__ = {**type_annotations, "return": ret_tuple}
        return func

    def _generate_return_named_tuple(self, function_abi: dict) -> Type:
        output_arg_names = []
        for output_entry in function_abi["outputs"]:
            name = output_entry["name"]
            output_arg_names.append(name)
            if output_entry["type"] != "felt":
                raise TypeError(
                    f"Return argument {name} expected to be of type felt. "
                    f"Got: {output_entry['type']}."
                )
        function_name = function_abi["name"]
        return namedtuple(f"{function_name}_return_type", output_arg_names)

    def _get_function_args(self, function_abi: dict) -> Tuple[Dict[str, dict], Dict[str, Type]]:
        """
        Given a StarkNet contract function abi, computes the arguments that the python proxy
        function should accept. In particular, an array input that has two inputs in the
        original abi (foo_len: felt, foo: felt*) will be converted to a single argument foo.

        Returns an ordered mapping from the argument name to the input abi.
        """
        args: Dict[str, dict] = {}
        type_annotations: Dict[str, Type] = {}
        last_name: Optional[str] = None
        for input_entry in function_abi["inputs"]:
            name = input_entry["name"]
            if input_entry["type"] == "felt*":
                # Make sure the last argument was {name}_len, and remove it.
                size_arg_name = f"{name}_len"
                assert (
                    last_name == size_arg_name
                ), f"Array size argument {size_arg_name} must appear right before {name}."
                size_arg = args.pop(size_arg_name)
                type_annotations.pop(size_arg_name)

                actual_type = size_arg["type"]
                assert (
                    actual_type == "felt"
                ), f"Array size entry {size_arg_name} expected to be type felt. Got: {actual_type}."

                type_annotations[name] = List[int]
            elif input_entry["type"] == "felt":
                type_annotations[name] = int
            else:
                raise NotImplementedError
            args[name] = input_entry
            last_name = name
        return args, type_annotations

    def _check_value_type(self, name: str, cairo_type: str, value):
        """
        Checks that a given python value has the right type, with respect to a Cairo type given
        in the ABI.
        """
        if cairo_type == "felt":
            if not isinstance(value, int):
                raise TypeError(f"Argument {name} expected to be of type int. Got: {type(value)}.")
        elif cairo_type == "felt*":
            if not isinstance(value, (list, tuple)):
                raise TypeError(
                    f"Argument {name} expected to be of type list or tuple. Got: {type(value)}."
                )
            for i, element in enumerate(value):
                if not isinstance(element, int):
                    raise TypeError(
                        f"Element {i} of argument {name} expected to be of type int. "
                        f"Got: {type(element)}."
                    )
        else:
            raise NotImplementedError

    def _build_function_call(self, function_abi: dict, args: dict, ret_tuple: Type):
        """
        Builds a StarknetContractFunctionInvocation object, representing a call to a StarkNet
        contract with a particular state and set of inputs.
        """
        calldata: List[int] = []
        for input_entry in function_abi["inputs"]:
            name = input_entry["name"]
            if name not in args:
                continue
            value = args[name]

            self._check_value_type(name=name, cairo_type=input_entry["type"], value=value)
            if input_entry["type"] == "felt":
                calldata.append(value)
            elif input_entry["type"] == "felt*":
                calldata.append(len(value))
                calldata.extend(value)
            else:
                raise NotImplementedError

        return StarknetContractFunctionInvocation(
            state=self.state,
            contract_address=self.contract_address,
            function_abi=function_abi,
            calldata=calldata,
            ret_tuple=ret_tuple,
        )


class StarknetContractFunctionInvocation:
    """
    A call to a StarkNet contract with a particular state and set of inputs
    """

    def __init__(
        self,
        state: StarknetState,
        contract_address: Union[int, str],
        function_abi: dict,
        calldata: List[int],
        ret_tuple: Type,
    ):
        self.state = state
        self.contract_address = contract_address
        self.function_abi = function_abi
        self.calldata = calldata
        self.ret_tuple = ret_tuple

    async def call(self) -> List[int]:
        """
        Executes the function call, without changing the state.
        """
        execution_info = await self.state.copy().invoke_raw(
            contract_address=self.contract_address,
            selector=self.function_abi["name"],
            calldata=self.calldata,
        )
        return self.ret_tuple(*execution_info.retdata)

    async def invoke(self) -> List[int]:
        """
        Executes the function call, and apply changes on the state.
        """
        execution_info = await self.state.invoke_raw(
            contract_address=self.contract_address,
            selector=self.function_abi["name"],
            calldata=self.calldata,
        )
        return self.ret_tuple(*execution_info.retdata)
