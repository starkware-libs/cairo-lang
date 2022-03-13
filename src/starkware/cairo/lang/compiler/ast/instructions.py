import dataclasses
from abc import abstractmethod
from typing import Optional, Sequence

from starkware.cairo.lang.compiler.ast.expr import Expression, ExprIdentifier
from starkware.cairo.lang.compiler.ast.formatting_utils import LocationField
from starkware.cairo.lang.compiler.ast.node import AstNode
from starkware.cairo.lang.compiler.error_handling import Location


class InstructionBody(AstNode):
    """
    Represents the instruction without the flag ap++.
    """

    location: Optional[Location]

    @abstractmethod
    def format(self) -> str:
        """
        Returns a string representing the instruction.
        """


@dataclasses.dataclass
class AssertEqInstruction(InstructionBody):
    """
    Represents the instruction "a = b" for two expressions a, b.
    """

    a: Expression
    b: Expression
    location: Optional[Location] = LocationField

    def format(self):
        return f"{self.a.format()} = {self.b.format()}"

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.a, self.b]


@dataclasses.dataclass
class JumpInstruction(InstructionBody):
    """
    Represents the instruction "jmp rel/abs".
    """

    val: Expression
    relative: bool
    location: Optional[Location] = LocationField

    def format(self):
        return f'jmp {"rel" if self.relative else "abs"} {self.val.format()}'

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.val]


@dataclasses.dataclass
class JumpToLabelInstruction(InstructionBody):
    """
    Represents the instruction "jmp <label>" or "jmp <label> if <condition> != 0".
    """

    label: ExprIdentifier
    condition: Optional[Expression]
    location: Optional[Location] = LocationField

    def format(self):
        condition_str = "" if self.condition is None else f" if {self.condition.format()} != 0"
        return f"jmp {self.label.format()}{condition_str}"

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.label, self.condition]


@dataclasses.dataclass
class JnzInstruction(InstructionBody):
    """
    Represents the instruction "jmp rel <jump_offset> if condition != 0".
    """

    jump_offset: Expression
    condition: Expression
    location: Optional[Location] = LocationField

    def format(self):
        return f"jmp rel {self.jump_offset.format()} if {self.condition.format()} != 0"

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.jump_offset, self.condition]


@dataclasses.dataclass
class CallInstruction(InstructionBody):
    """
    Represents the instruction "call rel/abs".
    """

    val: Expression
    relative: bool
    location: Optional[Location] = LocationField

    def format(self):
        return f'call {"rel" if self.relative else "abs"} {self.val.format()}'

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.val]


@dataclasses.dataclass
class CallLabelInstruction(InstructionBody):
    """
    Represents the instruction "call <label>".
    """

    label: ExprIdentifier
    location: Optional[Location] = LocationField
    # Indicates the 'label' is a fully qualified identifier, rather then a relative one.
    # This field is typically set for compiler-generated calls.
    fully_qualified_label: bool = False

    def format(self):
        return f"call {self.label.format()}"

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.label]


@dataclasses.dataclass
class RetInstruction(InstructionBody):
    """
    Represents the instruction "ret".
    """

    location: Optional[Location] = LocationField

    def format(self):
        return "ret"

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return []


@dataclasses.dataclass
class AddApInstruction(InstructionBody):
    """
    Represents the instruction "ap += expr".
    """

    expr: Expression
    location: Optional[Location] = LocationField

    def format(self):
        return f"ap += {self.expr.format()}"

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.expr]


@dataclasses.dataclass
class DefineWordInstruction(InstructionBody):
    """
    Represents the instruction "dw expr".
    This instruction encodes directly to a field element value in the program bytecode.
    """

    expr: Expression
    location: Optional[Location] = LocationField

    def format(self):
        return f"dw {self.expr.format()}"

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.expr]


@dataclasses.dataclass
class InstructionAst(AstNode):
    """
    Represents an instruction, including the ap++ flag (inc_ap).
    """

    body: InstructionBody
    inc_ap: bool
    location: Optional[Location] = LocationField

    def format(self):
        return self.body.format() + ("; ap++" if self.inc_ap else "")

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.body]
