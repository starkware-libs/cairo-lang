from collections.abc import Iterable
from typing import Any, Dict, Optional, Union, cast

from starkware.cairo.common.structs import CairoStructFactory
from starkware.cairo.lang.builtins.bitwise.bitwise_builtin_runner import BitwiseBuiltinRunner
from starkware.cairo.lang.builtins.bitwise.instance_def import BitwiseInstanceDef
from starkware.cairo.lang.builtins.ec.ec_op_builtin_runner import EcOpBuiltinRunner
from starkware.cairo.lang.builtins.ec.instance_def import EcOpInstanceDef
from starkware.cairo.lang.builtins.hash.hash_builtin_runner import HashBuiltinRunner
from starkware.cairo.lang.builtins.range_check.range_check_builtin_runner import (
    RangeCheckBuiltinRunner,
)
from starkware.cairo.lang.builtins.signature.signature_builtin_runner import SignatureBuiltinRunner
from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.tracer.tracer import trace_runner
from starkware.cairo.lang.vm.cairo_runner import CairoRunner, process_ecdsa, verify_ecdsa_sig
from starkware.cairo.lang.vm.crypto import pedersen_hash
from starkware.cairo.lang.vm.output_builtin_runner import OutputBuiltinRunner
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.cairo.lang.vm.security import verify_secure_runner
from starkware.cairo.lang.vm.utils import RunResources
from starkware.cairo.lang.vm.vm_exceptions import SecurityError, VmException


class CairoFunctionRunner(CairoRunner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        pedersen_builtin = HashBuiltinRunner(
            name="pedersen", included=True, ratio=32, hash_func=pedersen_hash
        )
        self.builtin_runners["pedersen_builtin"] = pedersen_builtin
        range_check_builtin = RangeCheckBuiltinRunner(
            included=True, ratio=1, inner_rc_bound=2 ** 16, n_parts=8
        )
        self.builtin_runners["range_check_builtin"] = range_check_builtin
        output_builtin = OutputBuiltinRunner(included=True)
        self.builtin_runners["output_builtin"] = output_builtin
        signature_builtin = SignatureBuiltinRunner(
            name="ecdsa",
            included=True,
            ratio=1,
            process_signature=process_ecdsa,
            verify_signature=verify_ecdsa_sig,
        )
        self.builtin_runners["ecdsa_builtin"] = signature_builtin
        bitwise_builtin = BitwiseBuiltinRunner(
            included=True, bitwise_builtin=BitwiseInstanceDef(ratio=1, total_n_bits=251)
        )
        self.builtin_runners["bitwise_builtin"] = bitwise_builtin
        ec_op_builtin = EcOpBuiltinRunner(
            included=True,
            ec_op_builtin=EcOpInstanceDef(
                ratio=1,
                scalar_height=256,
                scalar_bits=252,
                scalar_limit=None,
            ),
        )
        self.builtin_runners["ec_op_builtin"] = ec_op_builtin

        self.initialize_segments()

    @property
    def pedersen_builtin(self) -> HashBuiltinRunner:
        return cast(HashBuiltinRunner, self.builtin_runners["pedersen_builtin"])

    @property
    def range_check_builtin(self) -> RangeCheckBuiltinRunner:
        return cast(RangeCheckBuiltinRunner, self.builtin_runners["range_check_builtin"])

    @property
    def output_builtin(self) -> OutputBuiltinRunner:
        return cast(OutputBuiltinRunner, self.builtin_runners["output_builtin"])

    @property
    def ecdsa_builtin(self) -> SignatureBuiltinRunner:
        return cast(SignatureBuiltinRunner, self.builtin_runners["ecdsa_builtin"])

    @property
    def bitwise_builtin(self) -> BitwiseBuiltinRunner:
        return cast(BitwiseBuiltinRunner, self.builtin_runners["bitwise_builtin"])

    @property
    def ec_op_builtin(self) -> EcOpBuiltinRunner:
        return cast(EcOpBuiltinRunner, self.builtin_runners["ec_op_builtin"])

    def assert_eq(self, arg: MaybeRelocatable, expected_value, apply_modulo: bool = True):
        """
        Asserts that arg is the Cairo representation of expected_value.
        If expected_value is Iterable then arg is interpreted as a pointer to a list
        and assert_eq is called recursively on all the items in expected_value.
        If apply_modulo=True, all the integers are taken modulo the program's prime.
        """
        assert isinstance(arg, (int, RelocatableValue)), f"Expecting MaybeRelocatable got {arg}"

        if isinstance(expected_value, Iterable):
            for idx, value in enumerate(expected_value):
                self.assert_eq(self.vm_memory[arg + idx], value, apply_modulo=apply_modulo)
            return

        if apply_modulo and isinstance(arg, int):
            expected_value = expected_value % self.program.prime

        assert arg == expected_value, f"{arg} does not equal expected value {expected_value}."

    def run(
        self,
        func_name: str,
        *args,
        hint_locals: Optional[Dict[str, Any]] = None,
        static_locals: Optional[Dict[str, Any]] = None,
        verify_secure: Optional[bool] = None,
        trace_on_failure: bool = False,
        apply_modulo_to_args: Optional[bool] = None,
        use_full_name: bool = False,
        **kwargs,
    ):
        """
        Runs func_name(*args).
        args are converted to Cairo-friendly ones using gen_arg.

        Additional params:
        verify_secure - Run verify_secure_runner to do extra verifications.
        trace_on_failure - Run the tracer in case of failure to help debugging.
        apply_modulo_to_args - Apply modulo operation on integer arguments.
        use_full_name - Treat 'func_name' as a fully qualified identifier name, rather than a
         relative one.
        """
        assert isinstance(self.program, Program)
        entrypoint = self.program.get_label(func_name, full_name_lookup=use_full_name)

        structs_factory = CairoStructFactory.from_program(program=self.program)
        full_args_struct = structs_factory.build_func_args(
            func=ScopedName.from_string(scope=func_name)
        )
        all_args = full_args_struct(*args, **kwargs)

        try:
            self.run_from_entrypoint(
                entrypoint,
                all_args,
                typed_args=True,
                hint_locals=hint_locals,
                static_locals=static_locals,
                verify_secure=verify_secure,
                apply_modulo_to_args=apply_modulo_to_args,
            )
        except (VmException, SecurityError, AssertionError) as ex:
            if trace_on_failure:
                print(
                    f"""\
Got {type(ex).__name__} exception during the execution of {func_name}:
{str(ex)}
"""
                )
                trace_runner(runner=self)
            raise

    def run_from_entrypoint(
        self,
        entrypoint: Union[str, int],
        *args,
        typed_args: Optional[bool] = False,
        hint_locals: Optional[Dict[str, Any]] = None,
        static_locals: Optional[Dict[str, Any]] = None,
        run_resources: Optional[RunResources] = None,
        verify_secure: Optional[bool] = None,
        apply_modulo_to_args: Optional[bool] = None,
    ):
        """
        Runs the program from the given entrypoint.

        Additional params:
        typed_args - If true, the arguments are given as Cairo typed NamedTuple generated
          with CairoStructFactory.
        verify_secure - Run verify_secure_runner to do extra verifications.
        apply_modulo_to_args - Apply modulo operation on integer arguments.
        """
        if hint_locals is None:
            hint_locals = {}

        if verify_secure is None:
            verify_secure = True

        if apply_modulo_to_args is None:
            apply_modulo_to_args = True

        if typed_args:
            assert len(args) == 1, "len(args) must be 1 when using typed args."
            real_args = self.segments.gen_typed_args(args=args[0])
        else:
            real_args = [
                self.gen_arg(arg=x, apply_modulo_to_args=apply_modulo_to_args) for x in args
            ]
        end = self.initialize_function_entrypoint(entrypoint=entrypoint, args=real_args)
        self.initialize_vm(hint_locals=hint_locals, static_locals=static_locals)

        self.run_until_pc(addr=end, run_resources=run_resources)
        self.end_run()

        if verify_secure:
            verify_secure_runner(runner=self, verify_builtins=False)

    def get_return_values(self, n_ret: int):
        return self.vm_memory.get_range(addr=self.vm.run_context.ap - n_ret, size=n_ret)
