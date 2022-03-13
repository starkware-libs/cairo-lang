import re
import traceback
from typing import List, Optional, Tuple, Union

from starkware.cairo.lang.compiler.debug_info import InstructionLocation
from starkware.cairo.lang.compiler.error_handling import LocationError


class SecurityError(Exception):
    pass


class VmExceptionBase(Exception):
    """
    Base class for exceptions thrown by the Cairo VM.
    """


class VmException(LocationError, VmExceptionBase):
    def __init__(
        self,
        pc,
        inst_location: Optional[InstructionLocation],
        inner_exc,
        error_attr_value: Optional[str] = None,
        traceback: Optional[str] = None,
        notes: Optional[List[str]] = None,
        hint_index: Optional[int] = None,
    ):
        self.pc = pc
        self.inner_exc = inner_exc
        location = None
        if inst_location is not None:
            location = inst_location.inst
            # If the hint location is missing, fall back to the instruction location.
            if hint_index is not None:
                hint_location = inst_location.hints[hint_index]
                if hint_location is not None:
                    location = hint_location.location
        LocationError.__init__(
            self,
            f"Error at pc={self.pc}:\n{inner_exc}",
            error_attr_value=error_attr_value,
            location=location,
            traceback=traceback,
        )
        if notes is not None:
            self.notes += notes


class InconsistentAutoDeductionError(VmExceptionBase):
    def __init__(self, addr, current_value, new_value):
        self.addr = addr
        self.current_value = current_value
        self.new_value = new_value
        super().__init__(
            f"Inconsistent auto deduction rule at address {addr}. {current_value} != {new_value}."
        )


class PureValueError(VmExceptionBase):
    def __init__(self, oper, *values):
        self.oper = oper
        self.values = values
        values_str = f"values: {values}" if len(values) > 1 else f"value: {values[0]}"
        super().__init__(f"Could not complete computation {oper} of non pure {values_str}.")


class HintException(VmExceptionBase):
    def __init__(self, vm, exc_type, exc_value, exc_tb):
        if isinstance(exc_value, (IndentationError, SyntaxError)):
            fix = self.fix_name_and_line(vm, exc_value)
            if fix is not None:
                filename, line_num = fix
                exc_value = IndentationError(
                    exc_value.msg, (filename, line_num, exc_value.offset, exc_value.text)
                )

        tb_exception = traceback.TracebackException(exc_type, exc_value, exc_tb)
        # First item in the traceback is the call to exec, remove it.
        assert tb_exception.stack[0].filename.endswith("virtual_machine_base.py")
        del tb_exception.stack[0]

        # If we have location information, replace '<hint*>' entries with the correct filename
        # and line.
        def replace_stack_item(item: traceback.FrameSummary) -> traceback.FrameSummary:
            fix = self.fix_name_and_line(vm, item)
            if fix is None:
                return item
            filename, line_num = fix
            return traceback.FrameSummary(filename=filename, lineno=line_num, name=item.name)

        tb_exception.stack = traceback.StackSummary.from_list(
            map(replace_stack_item, tb_exception.stack)  # type: ignore
        )
        super().__init__(f"Got an exception while executing a hint.")
        self.exception_str = "".join(tb_exception.format())
        self.inner_exc = exc_value

    ExcType = Union[IndentationError, SyntaxError, traceback.FrameSummary]

    def fix_name_and_line(self, vm, exc_value: ExcType) -> Optional[Tuple[str, int]]:
        m = re.match("^<hint(?P<index>[0-9]+)>$", str(exc_value.filename))
        if m is None:
            return None
        pc, index = vm.hint_pc_and_index[int(m.group("index"))]
        location = vm.get_location(pc)
        if (location is None) or (location.hints[index] is None):
            return None
        hint_location = location.hints[index]
        start_line = hint_location.location.start_line
        prefix_lines = hint_location.n_prefix_newlines
        line_num = exc_value.lineno + start_line + prefix_lines - 1
        filename = hint_location.location.input_file.filename
        return filename, line_num
