import abc
import operator
from dataclasses import dataclass
from enum import Enum
from math import ceil
from typing import Any, Callable, Dict, List, Optional, Tuple, cast

from starkware.cairo.lang.builtins.modulo.instance_def import (
    AddModInstanceDef,
    ModInstanceDef,
    MulModInstanceDef,
)
from starkware.cairo.lang.vm.builtin_runner import SimpleBuiltinRunnerWithLowRatio
from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.python.math_utils import igcdex, safe_div

# The maximum n value that the function fill_memory accepts.
MAX_N = 100000

INPUT_NAMES = [
    "p0",
    "p1",
    "p2",
    "p3",
    "values_ptr",
    "offsets_ptr",
    "n",
]

MEMORY_VAR_NAMES = [
    "a_offset",
    "b_offset",
    "c_offset",
    "a0",
    "a1",
    "a2",
    "a3",
    "b0",
    "b1",
    "b2",
    "b3",
    "c0",
    "c1",
    "c2",
    "c3",
]

INPUT_CELLS = len(INPUT_NAMES)
ADDITIONAL_MEMORY_UNITS = len(MEMORY_VAR_NAMES)


class FillValueResult(Enum):
    Success = 0
    MissingOperand = 1
    ZeroDivisor = 2


class ModBuiltinRunner(SimpleBuiltinRunnerWithLowRatio):
    def __init__(
        self,
        name: str,
        included: bool,
        instance_def: ModInstanceDef,
        op: Callable[[int, int], int],
        k_bound: Optional[int],
    ):
        super().__init__(
            name=name,
            included=included,
            ratio=None if instance_def is None else instance_def.ratio,
            cells_per_instance=INPUT_CELLS,
            n_input_cells=INPUT_CELLS,
            additional_memory_units_per_instance=ADDITIONAL_MEMORY_UNITS,
            ratio_den=instance_def.ratio_den,
        )
        self.instance_def: ModInstanceDef = instance_def
        self.zero_value: Optional[RelocatableValue] = None
        self.zero_segment_size = max(self.instance_def.n_words, self.instance_def.batch_size * 3)
        # Precomputed powers used for reading and writing values that are represented as n_words
        # words of word_bit_len bits each.
        self.shift = 2**self.instance_def.word_bit_len
        self.shift_powers = [self.shift**i for i in range(self.instance_def.n_words)]

        self.int_lim = 2 ** (self.instance_def.n_words * self.instance_def.word_bit_len)

        self.op = op
        # In the case the input for k_bound is None we give self.k_bound the value of self.int_lim,
        # otherwise we give it the value of k_bound.
        self.k_bound = k_bound if k_bound is not None else self.int_lim

    def get_needed_number_allocated_zeros(self) -> int:
        return self.zero_segment_size

    def set_address_allocated_zeros(self, addr: RelocatableValue):
        self.zero_value = addr

    def get_instance_def(self):
        return self.instance_def

    def get_memory_accesses(self, runner):
        """
        Returns memory accesses for the builtin on all segments, including values and offsets
        addresses. Used by the cairo_runner to check for memory holes.
        """
        segment_size = runner.segments.get_segment_size(self.base.segment_index)
        n_instances = ceil(segment_size / self.cells_per_instance)
        res = set()
        for instance in range(n_instances):
            offsets_ptr_addr = (
                self.base + instance * self.n_input_cells + INPUT_NAMES.index("offsets_ptr")
            )
            offsets_addr = runner.vm_memory[offsets_ptr_addr]
            values_ptr_addr = (
                self.base + instance * self.n_input_cells + INPUT_NAMES.index("values_ptr")
            )
            values_addr = runner.vm_memory[values_ptr_addr]
            for i in range(3 * self.instance_def.batch_size):
                offset_addr = offsets_addr + i
                res.add(offset_addr)
                offset = runner.vm_memory[offset_addr]
                for j in range(self.instance_def.n_words):
                    res.add(values_addr + offset + j)
        return super().get_memory_accesses(runner).union(res)

    def initialize_segments(self, runner):
        super().initialize_segments(runner)

    def finalize_segments(self, runner):
        super().finalize_segments(runner)

    # The structure of the values in the returned dictionary is of the form:
    # {keys = INPUT_NAMES, "batch": {index_in_batch: {keys = MEMORY_VAR_NAMES}}}.
    def air_private_input(self, runner) -> Dict[str, Any]:
        assert self.base is not None, "Uninitialized self.base."
        res: Dict[int, Any] = {}
        values_addr_per_instance = {}
        offsets_addr_per_instance = {}
        for addr, val in runner.vm_memory.items():
            if (
                not isinstance(addr, RelocatableValue)
                or addr.segment_index != self.base.segment_index
            ):
                continue
            idx, typ = divmod(addr.offset, INPUT_CELLS)
            typ_name = INPUT_NAMES[typ]
            if isinstance(val, RelocatableValue):
                assert typ_name in ["values_ptr", "offsets_ptr"]
                if typ_name == "values_ptr":
                    values_addr_per_instance[idx] = val
                elif typ_name == "offsets_ptr":
                    offsets_addr_per_instance[idx] = val
                val = runner.relocate_value(val)
            assert isinstance(val, int)
            # p0-p3 are felts, and must be saved in hex. Other values are UInt64.
            if typ < 4:
                val = hex(val)
            res.setdefault(
                idx, {"index": idx, "batch": [{} for _ in range(self.instance_def.batch_size)]}
            )[typ_name] = val

        for idx, offsets_addr in offsets_addr_per_instance.items():
            for index_in_batch in range(self.instance_def.batch_size):
                for i, s in enumerate("abc"):
                    offset = runner.vm_memory[offsets_addr + i + 3 * index_in_batch]
                    res[idx]["batch"][index_in_batch][f"{s}_offset"] = offset
                    assert idx in values_addr_per_instance
                    values_addr = values_addr_per_instance[idx]
                    for d in range(self.instance_def.n_words):
                        value = runner.vm_memory[values_addr + offset + d]
                        res[idx]["batch"][index_in_batch][f"{s}{d}"] = hex(value)

        for index, item in res.items():
            for name in INPUT_NAMES:
                assert name in item, f"Missing input '{name}' of {self.name} instance {index}."
            for index_in_batch in range(self.instance_def.batch_size):
                for name in MEMORY_VAR_NAMES:
                    assert name in item["batch"][index_in_batch], (
                        f"Missing memory variable '{name}' of {self.name} instance {index}, "
                        + f"batch {index_in_batch}."
                    )

        sorted_res = sorted(res.values(), key=lambda item: item["index"])
        assert self.zero_value is not None, "Uninitialized self.zero_value."
        zero_value_address = runner.relocate_value(self.zero_value)
        return {self.name: {"instances": sorted_res, "zero_value_address": zero_value_address}}

    def read_n_words_value(self, memory, addr) -> Tuple[List[int], Optional[int]]:
        """
        Reads self.instance_def.n_words from memory, starting at address=addr.
        Returns the words and the value if all words are in memory.
        Verifies that all words are integers and are bounded by 2**self.instance_def.word_bit_len.
        """
        if addr not in memory:
            return [], None

        words: List[int] = []
        value = 0
        for i in range(self.instance_def.n_words):
            addr_i = addr + i
            if addr_i not in memory:
                return words, None
            word = memory[addr_i]
            assert isinstance(word, int), (
                f"Expected integer at address {addr_i}. " + f"Got: {word}."
            )
            assert word < self.shift, (
                f"Expected integer at address {addr_i} to be smaller than "
                + f"2^{self.instance_def.word_bit_len}. Got: {word}."
            )
            words.append(word)
            value += word * self.shift_powers[i]

        return words, value

    def run_security_checks(self, runner):
        op = self.op
        k_bound = self.k_bound
        super().run_security_checks(runner)
        segment_size = runner.segments.get_segment_used_size(self.base.segment_index)
        n_instances = ceil(segment_size / self.cells_per_instance)

        prev_inputs = None
        for instance in range(n_instances):
            inputs = self.read_inputs(runner.vm_memory, self.base + instance * self.n_input_cells)
            if prev_inputs is not None and prev_inputs["n"] > self.instance_def.batch_size:
                assert all(
                    inputs[f"p{i}"] == prev_inputs[f"p{i}"]
                    for i in range(self.instance_def.n_words)
                )
                assert inputs["values_ptr"] == prev_inputs["values_ptr"]
                assert (
                    inputs["offsets_ptr"]
                    == prev_inputs["offsets_ptr"] + 3 * self.instance_def.batch_size
                )
                assert inputs["n"] == prev_inputs["n"] - self.instance_def.batch_size
            assert isinstance(inputs["p"], int)
            for index_in_batch in range(self.instance_def.batch_size):
                values = self.read_memory_vars(
                    runner.vm_memory, inputs["values_ptr"], inputs["offsets_ptr"], index_in_batch
                )
                assert op(values["a"], values["b"]) % inputs["p"] == values["c"] % inputs["p"], (
                    f"{self.name} builtin: Expected a {op} b == c (mod p). Got: "
                    + f"instance={instance}, batch={index_in_batch}, inputs={inputs}, "
                    + f"values={values}."
                )
                assert (
                    op(values["a"], values["b"]) - values["c"] < k_bound * inputs["p"]
                    and op(values["a"], values["b"]) >= values["c"]
                ), (
                    f"{self.name} builtin: Expected (a {op} b - c)/p to be in "
                    + f"{{0,1,...,{k_bound-1}}} Got: "
                    + f"instance={instance}, batch={index_in_batch}, inputs={inputs}, "
                    + f"values={values}."
                )
            prev_inputs = inputs
        if prev_inputs is not None:
            assert prev_inputs["n"] == self.instance_def.batch_size

    def read_inputs(self, memory, addr, read_n: bool = True) -> Dict[str, MaybeRelocatable]:
        """
        Reads the inputs to the builtin (see INPUT_NAMES) from the memory at address=addr.
        Returns a dictionary from input name to its value. Asserts that it exists in memory.
        Returns also the value of p, not just its words.

        If `read_n` is false, avoids reading and validating the value of 'n'.
        """
        inputs = {}
        inputs["values_ptr"] = memory[addr + INPUT_NAMES.index("values_ptr")]
        assert isinstance(inputs["values_ptr"], RelocatableValue), (
            f"{self.name} builtin: Expected RelocatableValue at address "
            + f"{addr + INPUT_NAMES.index('values_ptr')}. Got: {inputs['values_ptr']}."
        )
        inputs["offsets_ptr"] = memory[addr + INPUT_NAMES.index("offsets_ptr")]
        assert isinstance(inputs["offsets_ptr"], RelocatableValue), (
            f"{self.name} builtin: Expected RelocatableValue at address "
            + f"{addr + INPUT_NAMES.index('offsets_ptr')}. Got: {inputs['offsets_ptr']}."
        )

        if read_n:
            inputs["n"] = memory[addr + INPUT_NAMES.index("n")]
            assert isinstance(inputs["n"], int), (
                f"{self.name} builtin: Expected integer at address "
                + f"{addr + INPUT_NAMES.index('n')}. Got: {inputs['n']}."
            )
            assert inputs["n"] >= 1, f"{self.name} builtin: Expected n >= 1. Got: {inputs['n']}."

        p_addr = addr + INPUT_NAMES.index("p0")
        words, value = self.read_n_words_value(memory, p_addr)
        assert (
            value is not None
        ), f"{self.name} builtin: Missing value at address {p_addr + len(words)}."
        inputs["p"] = value
        for d, w in enumerate(words):
            inputs[f"p{d}"] = w
        return inputs

    def read_memory_vars(self, memory, values_ptr, offsets_ptr, index_in_batch) -> Dict[str, int]:
        """
        Reads the memory variables to the builtin (see MEMORY_VAR_NAMES) from the memory given
        the inputs (specifically, values_ptr and offsets_ptr).
        Returns a dictionary from memory variable name to its value. Asserts if it doesn't exist in
        memory. Returns also the values of a, b, and c, not just their words.
        """
        memory_vars = {}
        for i, s in enumerate("abc"):
            offset = memory[offsets_ptr + i + 3 * index_in_batch]
            assert isinstance(offset, int), (
                f"{self.name} builtin: Expected integer at address "
                + f"{offsets_ptr + i}. Got: {offset}."
            )
            memory_vars[f"{s}_offset"] = offset
            value_addr = values_ptr + offset
            words, value = self.read_n_words_value(memory, value_addr)
            assert (
                value is not None
            ), f"{self.name} builtin: Missing value at address {value_addr + len(words)}."
            memory_vars[s] = value
            for d, w in enumerate(words):
                memory_vars[f"{s}{d}"] = w
        return memory_vars

    @staticmethod
    def fill_memory(
        memory,
        add_mod: Optional[Tuple[RelocatableValue, "AddModBuiltinRunner", int]],
        mul_mod: Optional[Tuple[RelocatableValue, "MulModBuiltinRunner", int]],
    ):
        """
        Fills the memory with inputs to the builtin instances based on the inputs to the
        first instance, pads the offsets table to fit the number of operations written in the
        input to the first instance, and calculates missing values in the values table.

        For each builtin, the given tuple is of the form (builtin_ptr, builtin_runner, n),
        where n is the number of operations in the offsets table (i.e., the length of the
        offsets table is 3*n).

        The number of operations written to the input of the first instance n' should be at
        least n and a multiple of batch_size. Previous offsets are copied to the end of the
        offsets table to make its length 3n'.
        """
        # Check that the instance definitions of the builtins are the same.
        if add_mod and mul_mod:
            assert (
                add_mod[1].instance_def.n_words == mul_mod[1].instance_def.n_words
                and add_mod[1].instance_def.word_bit_len == mul_mod[1].instance_def.word_bit_len
            ), f"add_mod and mul_mod builtins must have the same n_words and word_bit_len."

        if add_mod and add_mod[2] == 0:
            add_mod = None
        if mul_mod and mul_mod[2] == 0:
            mul_mod = None

        # Fill the inputs to the builtins.
        if add_mod:
            assert add_mod[2] <= MAX_N, f"{add_mod[1].name} builtin: n must be <= {MAX_N}"
            add_mod_inputs = add_mod[1].read_inputs(memory, add_mod[0])

            add_mod_instance = ModBuiltinRunner.InstanceData(
                builtin=add_mod[1],
                memory=memory,
                values_ptr=cast(RelocatableValue, add_mod_inputs["values_ptr"]),
                offsets_ptr=cast(RelocatableValue, add_mod_inputs["offsets_ptr"]),
                modulus=cast(int, add_mod_inputs["p"]),
            )
            add_mod[1].fill_inputs(memory, add_mod[0], add_mod_inputs)
            add_mod[1].fill_offsets(
                memory, add_mod_inputs, add_mod[2], add_mod_inputs["n"] - add_mod[2]
            )
        if mul_mod:
            assert mul_mod[2] <= MAX_N, f"{mul_mod[1].name} builtin: n must be <= {MAX_N}"

            # Note that we can't read 'n' here because sierra expects this function to compute it.
            mul_mod_inputs = mul_mod[1].read_inputs(memory, mul_mod[0], read_n=False)
            mul_mod_instance = ModBuiltinRunner.InstanceData(
                builtin=mul_mod[1],
                memory=memory,
                values_ptr=cast(RelocatableValue, mul_mod_inputs["values_ptr"]),
                offsets_ptr=cast(RelocatableValue, mul_mod_inputs["offsets_ptr"]),
                modulus=cast(int, mul_mod_inputs["p"]),
            )

        has_add_mod_runner = has_mul_mod_runner = False
        if add_mod:
            has_add_mod_runner = isinstance(add_mod[1], AddModBuiltinRunner)
        if mul_mod:
            has_mul_mod_runner = isinstance(mul_mod[1], MulModBuiltinRunner)
        assert (
            has_add_mod_runner or has_mul_mod_runner
        ), "At least one of add_mod and mul_mod must be given."

        # Fill the values table.
        add_mod_n = add_mod[2] if add_mod else 0
        mul_mod_n = mul_mod[2] if mul_mod else 0

        add_mod_index = 0
        mul_mod_index = 0

        n_computed_mul_gates = None
        while add_mod_index < add_mod_n or mul_mod_index < mul_mod_n:
            if add_mod_index < add_mod_n and has_add_mod_runner:
                if add_mod_instance.fill_value(index=add_mod_index) == FillValueResult.Success:
                    add_mod_index += 1
                    continue
            if mul_mod_index < mul_mod_n and has_mul_mod_runner:
                gate_res = mul_mod_instance.fill_value(index=mul_mod_index)
                if gate_res == FillValueResult.MissingOperand:
                    raise Exception(
                        f"Could not fill the values table, "
                        + f"add_mod_index={add_mod_index}, mul_mod_index={mul_mod_index}"
                    )
                elif gate_res == FillValueResult.ZeroDivisor and n_computed_mul_gates is None:
                    n_computed_mul_gates = mul_mod_index

                mul_mod_index += 1

        if mul_mod:
            mul_mod_ptr = mul_mod[0]
            n_mul_mods_ptr = mul_mod_ptr + INPUT_NAMES.index("n")
            if n_computed_mul_gates is None:
                n_computed_mul_gates = memory.get(n_mul_mods_ptr)
                if n_computed_mul_gates is None:
                    n_computed_mul_gates = mul_mod_n
                mul_mod_inputs["n"] = n_computed_mul_gates
                mul_mod[1].fill_offsets(
                    memory, mul_mod_inputs, mul_mod_n, n_computed_mul_gates - mul_mod_n
                )
            else:
                assert (
                    mul_mod[1].instance_def.batch_size == 1
                ), "Inverse failure is supported only at batch_size == 1."

            memory[n_mul_mods_ptr] = n_computed_mul_gates
            mul_mod_inputs["n"] = n_computed_mul_gates
            mul_mod[1].fill_inputs(memory, mul_mod_ptr, mul_mod_inputs)

    @abc.abstractmethod
    def calc_operand(self, known, res, p) -> Tuple[FillValueResult, int]:
        """
        Given known, res, p tries to compute the minimal integer operand x which
        satisfies the equation op(x,known) = res + k*p for some k in {0,1,...,self.k_bound-1}.
        If op is operator.mul, and gcd(known, p) != 1, returns
        (FillValueResult.ZeroDivisor, nullifier) s.t. 0 < nullifier < p and
        nullifier * known = 0 (mod p).
        """

    # Fills the inputs to the instances of the builtin given the inputs to the first instance.
    def fill_inputs(self, memory, builtin_ptr, inputs):
        assert inputs["n"] <= MAX_N, f"{self.name} builtin: n must be <= {MAX_N}"
        n_instances = safe_div(inputs["n"], self.instance_def.batch_size)
        for instance in range(1, n_instances):
            instance_ptr = builtin_ptr + instance * len(INPUT_NAMES)
            for i in range(self.instance_def.n_words):
                memory[instance_ptr + INPUT_NAMES.index(f"p{i}")] = inputs[f"p{i}"]
            memory[instance_ptr + INPUT_NAMES.index("values_ptr")] = inputs["values_ptr"]
            memory[instance_ptr + INPUT_NAMES.index("offsets_ptr")] = (
                inputs["offsets_ptr"] + 3 * instance * self.instance_def.batch_size
            )
            memory[instance_ptr + INPUT_NAMES.index("n")] = (
                inputs["n"] - instance * self.instance_def.batch_size
            )

    # Copies the first offsets in the offsets table to its end, n_copies times.
    def fill_offsets(self, memory, inputs, index, n_copies):
        offsets = {}
        for i, s in enumerate("abc"):
            s_offset = memory[inputs["offsets_ptr"] + i]
            offsets[s] = s_offset
        for i in range(n_copies):
            for j, s in enumerate("abc"):
                memory[inputs["offsets_ptr"] + 3 * (index + i) + j] = offsets[s]

    def write_n_words_value(self, memory, addr, value):
        """
        Given a value, writes its n_words to memory, starting at address=addr.
        """
        value_copy = value
        for i in range(self.instance_def.n_words):
            word = value_copy % self.shift
            # The following line will raise InconsistentMemoryError if the address is already in
            # memory and a different value is written.
            memory[addr + i] = word
            value_copy //= self.shift
        assert value_copy == 0

    @dataclass
    class InstanceData:
        builtin: "ModBuiltinRunner"
        memory: MemoryDict
        values_ptr: RelocatableValue
        offsets_ptr: RelocatableValue
        modulus: int

        # Fills a value in the values table, if exactly one value is missing.
        # Returns true on success or if all values are already known.
        def fill_value(self, index) -> FillValueResult:
            memory = self.memory
            builtin = self.builtin
            op = builtin.op
            k_bound = builtin.k_bound
            offsets_ptr = self.offsets_ptr
            values_ptr = self.values_ptr
            addresses = (
                values_ptr + memory[offsets_ptr + 3 * index],
                values_ptr + memory[offsets_ptr + 3 * index + 1],
                values_ptr + memory[offsets_ptr + 3 * index + 2],
            )
            values: List[Optional[int]] = []
            for addr in addresses:
                _words, value = builtin.read_n_words_value(memory, addr)
                values.append(value)

            if None not in values:
                # All values are already known.
                return FillValueResult.Success

            a, b, c = values
            p = self.modulus
            # Deduce c from a and b and write it to memory.
            if c is None and a is not None and b is not None:
                tmp_val = op(a, b)
                # Check if op(a, b) is too big to compensate for with multiples of p.
                assert tmp_val - (k_bound - 1) * p <= builtin.int_lim - 1, (
                    f"{builtin.name} builtin: "
                    + f"Expected a {op} b - {k_bound - 1} * p <= {builtin.int_lim - 1}"
                    + f". Got: values={values}, p={p}."
                )
                value = tmp_val % p if tmp_val < k_bound * p else tmp_val - (k_bound - 1) * p
                builtin.write_n_words_value(memory, addresses[2], value)
                return FillValueResult.Success
            # Deduce b from a and c.
            res, value = None, None
            if b is None and a is not None and c is not None:
                res, value = builtin.calc_operand(known=a, res=c, p=p)
                ind = 1
            # Deduce a from b and c.
            if a is None and b is not None and c is not None:
                res, value = builtin.calc_operand(known=b, res=c, p=p)
                ind = 0
            # Write the deduced operand to memory.
            if res is not None:
                builtin.write_n_words_value(memory, addresses[ind], value)
                return res
            return FillValueResult.MissingOperand


class AddModBuiltinRunner(ModBuiltinRunner):
    def __init__(self, included: bool, instance_def: AddModInstanceDef):
        super().__init__(
            name="add_mod", included=included, instance_def=instance_def, op=operator.add, k_bound=2
        )

    def calc_operand(self, known, res, p):
        # Currently k_bound = 2 is the only option.
        assert (
            known <= res + p
        ), f"add_mod builtin: addend greater than sum + p: {known} > {res} + {p}."
        value = res - known if known <= res else res + p - known
        return (FillValueResult.Success, value)


class MulModBuiltinRunner(ModBuiltinRunner):
    def __init__(self, included: bool, instance_def: MulModInstanceDef):
        super().__init__(
            name="mul_mod",
            included=included,
            instance_def=instance_def,
            op=operator.mul,
            k_bound=None,
        )

    def calc_operand(self, known, res, p):
        x, _, gcd = igcdex(known, p)
        if gcd != 1:
            nullifier = p // gcd
            # Note that gcd divides known, so known * nullifier = known * (p // gcd) =
            # (known // gcd) * p = 0 (mod p)
            return FillValueResult.ZeroDivisor, nullifier

        tmp_val = (res * x) % p
        tmp_k = safe_div((known * tmp_val) - res, p)
        # This cannot happen as long as self.k_bound >= self.int_lim.
        assert tmp_k < self.k_bound, (
            f"mul_mod builtin: (({known} * q) - {res}) / {p} > {self.k_bound} for any "
            + f"q > 0, such that {known} * q = {res} (mod {p})."
        )
        if tmp_k >= 0:
            return FillValueResult.Success, tmp_val

        # This cannot be greater than max(res, p) since
        # tmp_val + p * ((known - 1 - tmp_k) // known) <
        # tmp_val + p * (-tmp_k) / known + p*(known-1)/known =
        # res/known + p * (known-1) / known
        # meaning it is a convex combination of res and p.
        value = tmp_val + p * ((known - 1 - tmp_k) // known)

        return FillValueResult.Success, value
