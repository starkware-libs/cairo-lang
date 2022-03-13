from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple

from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.cairo.lang.vm.utils import MemorySegmentRelocatableAddresses
from starkware.python.math_utils import div_ceil, safe_div


class InsufficientAllocatedCells(Exception):
    pass


class BuiltinRunner(ABC):
    @abstractmethod
    def initialize_segments(self, runner):
        """
        Adds memory segments for the builtin.
        """

    @abstractmethod
    def initial_stack(self) -> List[MaybeRelocatable]:
        """
        Returns the initial stack elements enforced by this builtin.
        """

    @abstractmethod
    def final_stack(self, runner, pointer: MaybeRelocatable) -> MaybeRelocatable:
        """
        Reads values from the end of the stack ([pointer - 1], [pointer - 2], ...), and returns
        the updated pointer (e.g., pointer - 2 if two values were read).
        This function may also do builtin specific validation of said values.
        """

    @abstractmethod
    def get_used_cells(self, runner) -> int:
        """
        Returns the number of used cells.
        """

    @abstractmethod
    def get_used_instances(self, runner) -> int:
        """
        Returns the number of used instances.
        """

    @abstractmethod
    def get_allocated_memory_units(self, runner) -> int:
        """
        Returns the number of memory units used by the builtin.
        """

    @abstractmethod
    def get_used_cells_and_allocated_size(self, runner) -> Tuple[int, int]:
        """
        Returns the number of used cells and the allocated size, and raises
        InsufficientAllocatedCells if there are more used cells than allocated cells.
        """

    @abstractmethod
    def finalize_segments(self, runner):
        """
        Calls runner.segments.finalize for the memory segments added in initialize_segments.
        """

    @abstractmethod
    def get_memory_segment_addresses(self, runner) -> Dict[str, MemorySegmentRelocatableAddresses]:
        """
        Returns a dict from segment name to MemorySegmentRelocatableAddresses
        (begin_addr and stop_ptr of the corresponding segment).
        """

    @abstractmethod
    def run_security_checks(self, runner):
        """
        Runs some security checks to make sure a proof can be generated given the memory.
        """

    def relocate(self, relocate_value: Callable[[MaybeRelocatable], MaybeRelocatable]):
        """
        Relocates the internal values of the builtin using the given function relocate_value.
        """
        return

    def add_auto_deduction_rules(self, runner):
        """
        Adds auto-deduction rules for this builtin (if applicable).
        Auto deduction rules are applied when an unknown memory cell in the builtin segment is
        accessed.
        """
        return

    def add_validation_rules(self, runner):
        """
        Adds validation rules for this builtin (if applicable).
        Validation rules are applied once a builtin instance is written to memory.
        For more details, see 'add_validation_rule' in validated_memory_dict.py.
        """
        return

    def air_private_input(self, runner) -> Dict[str, Any]:
        """
        Returns information about the builtin that should be added to the AIR private input.
        """
        return {}

    def get_range_check_usage(self, runner) -> Optional[Tuple[int, int]]:
        """
        Returns (rc_min, rc_max), i.e., the minimal and maximal range-checked values, if the builtin
        used any range check cells. Otherwise, returns None.
        """
        return None

    def get_used_perm_range_check_units(self, runner) -> int:
        """
        Returns the number of range check units used by the builtin.
        """
        return 0

    def get_used_diluted_check_units(self, diluted_spacing: int, diluted_n_bits: int) -> int:
        """
        Returns the number of diluted check units used by the builtin.
        """
        return 0

    def get_additional_data(self) -> Any:
        """
        Returns additional data that was created in the builtin runner. This data can be loaded
        to another builtin runner of the same type using extend_additional_data().
        This data must be JSON-serializable.
        """
        return

    def extend_additional_data(
        self,
        data: Any,
        relocate_callback: Callable[[MaybeRelocatable], MaybeRelocatable],
        data_is_trusted: bool = True,
    ):
        """
        Adds the additional data created by another instance of the builtin runner.
        relocate_callback is a callback function used to relocate the addresses.
        If data_is_trusted is False, the function does not assume that instances
        that were processed by the other builtin runner were properly validated.
        """
        return

    def get_memory_accesses(self, runner):
        """
        Returns memory addresses that are used by the builtin itself and therefore should not count
        as memory holes.
        """
        return {}


class BuiltinVerifier(ABC):
    @abstractmethod
    def expected_stack(self, public_input) -> Tuple[List[int], List[int]]:
        """
        Returns a pair (initial_stack, final_stack).
        They contain the expected elements of the initial stack or final stack that are associated
        with this builtin.
        """


class SimpleBuiltinRunner(BuiltinRunner):
    """
    A base class for simple builtins that use a single segment.
    """

    def __init__(
        self, name: str, included: bool, ratio: int, cells_per_instance: int, n_input_cells: int
    ):
        """
        Constructs a SimpleBuiltinRunner.
        cells_per_instance is the number of memory cells per invocation.
        n_input_cells is the number of the first memory cells in each invocation that form the
        input. The rest of the cells are considered output.
        """
        self.name = name
        self.included = included
        self.ratio = ratio
        self._base: Optional[RelocatableValue] = None
        self.stop_ptr: Optional[RelocatableValue] = None
        self.cells_per_instance = cells_per_instance
        self.n_input_cells = n_input_cells

    def initialize_segments(self, runner):
        self._base = runner.segments.add()

    @property
    def base(self) -> RelocatableValue:
        assert self._base is not None, "Uninitialized self.base."
        return self._base

    def initial_stack(self) -> List[MaybeRelocatable]:
        return [self.base] if self.included else []

    def final_stack(self, runner, pointer):
        if self.included:
            self.stop_ptr = runner.vm_memory[pointer - 1]
            used = self.get_used_instances(runner=runner) * self.cells_per_instance
            assert self.stop_ptr == self.base + used, (
                f"Invalid stop pointer for {self.name}. "
                + f"Expected: {self.base + used}, found: {self.stop_ptr}"
            )
            return pointer - 1
        else:
            self.stop_ptr = self.base
            return pointer

    def get_used_cells(self, runner):
        used = runner.segments.get_segment_used_size(self.base.segment_index)
        return used

    def get_used_instances(self, runner):
        return div_ceil(self.get_used_cells(runner), self.cells_per_instance)

    def get_allocated_memory_units(self, runner):
        return self.cells_per_instance * safe_div(runner.vm.current_step, self.ratio)

    def get_used_cells_and_allocated_size(self, runner):
        if runner.vm.current_step < self.ratio:
            raise InsufficientAllocatedCells(
                f"Number of steps must be at least {self.ratio} for the {self.name} builtin."
            )
        used = self.get_used_cells(runner)
        size = self.cells_per_instance * safe_div(runner.vm.current_step, self.ratio)
        if used > size:
            raise InsufficientAllocatedCells(
                f"The {self.name} builtin used {used} cells but the capacity is {size}."
            )
        return used, size

    def finalize_segments(self, runner):
        _, size = self.get_used_cells_and_allocated_size(runner)

        runner.segments.finalize(segment_index=self.base.segment_index, size=size)

    def get_memory_segment_addresses(self, runner):
        return {
            self.name: MemorySegmentRelocatableAddresses(
                begin_addr=self.base,
                stop_ptr=self.stop_ptr,
            )
        }

    def run_security_checks(self, runner):
        offsets = {
            addr.offset
            for addr in runner.vm_memory.keys()
            if isinstance(addr, RelocatableValue) and addr.segment_index == self.base.segment_index
        }
        n = (max(offsets) // self.cells_per_instance + 1) if len(offsets) > 0 else 0

        # Verify that n is not too large to make sure the expected_offsets set that is constructed
        # below is not too large.
        assert n <= len(offsets) // self.n_input_cells, f"Missing memory cells for {self.name}."

        # Check that the two inputs (x and y) of each instance are set.
        expected_offsets = {
            self.cells_per_instance * i + j for i in range(n) for j in range(self.n_input_cells)
        }
        if not expected_offsets <= offsets:
            missing_offsets = list(expected_offsets - offsets)
            dots = "..." if len(missing_offsets) > 20 else "."
            missing_offsets_str = ", ".join(map(str, missing_offsets[:20])) + dots
            raise AssertionError(f"Missing memory cells for {self.name}: {missing_offsets_str}")

    def get_memory_accesses(self, runner):
        segment_size = runner.segments.get_segment_size(self.base.segment_index)
        return {self.base + x for x in range(segment_size)}
