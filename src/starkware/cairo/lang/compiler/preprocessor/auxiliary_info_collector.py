from abc import ABC, abstractmethod
from typing import List, Optional

from starkware.cairo.lang.compiler.ast.expr import ExprAssignment, Expression
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.identifier_definition import StructDefinition
from starkware.cairo.lang.compiler.scoped_name import ScopedName


class AuxiliaryInfoCollector(ABC):
    """
    Interface for collecting information made available during the preprocessing step.
    This can be used to collect information linking the high-level Cairo program with
    the low-level assembly.
    """

    @classmethod
    @abstractmethod
    def create(cls, *args, **kwargs):
        pass

    @abstractmethod
    def start_function_info(
        self,
        name: str,
        start_pc: int,
        implicit_args_struct: StructDefinition,
        args_struct: StructDefinition,
    ):
        pass

    @abstractmethod
    def finish_function_info(self, end_pc: int):
        pass

    @abstractmethod
    def add_assert_eq(self, lhs: Expression, rhs: Expression):
        pass

    @abstractmethod
    def start_compound_assert_eq(self, lhs: Expression, rhs: Expression):
        pass

    @abstractmethod
    def finish_compound_assert_eq(self):
        pass

    @abstractmethod
    def add_reference(self, name: ScopedName, expr: Expression, identifier_loc: Optional[Location]):
        pass

    @abstractmethod
    def start_temp_var(
        self, name: ScopedName, expr: Expression, identifier_loc: Optional[Location]
    ):
        pass

    @abstractmethod
    def finish_temp_var(self):
        pass

    @abstractmethod
    def start_func_call(self, name: str, args: List[Expression]):
        pass

    @abstractmethod
    def finish_func_call(self):
        pass

    @abstractmethod
    def start_tail_call(self, args: List[Expression]):
        pass

    @abstractmethod
    def finish_tail_call(self):
        pass

    @abstractmethod
    def add_func_ret_vars(self, ret_vars: List[str]):
        pass

    @abstractmethod
    def start_return(self):
        pass

    @abstractmethod
    def finish_return(self, exprs: List[ExprAssignment]):
        pass

    @abstractmethod
    def record_label(self, label_full_name: str):
        pass

    @abstractmethod
    def record_jump_to_labeled_instruction(
        self,
        label_name: str,
        condition: Optional[Expression],
        current_pc: int,
        pc_dest: Optional[int] = None,
    ):
        pass

    @abstractmethod
    def start_if(self, expr_a: Expression, expr_b: Expression, cond_eq: bool):
        pass

    @abstractmethod
    def end_if(self):
        pass

    @abstractmethod
    def add_add_ap(self, expr: Expression):
        pass

    @abstractmethod
    def add_const(self, name: ScopedName, val: int):
        pass
