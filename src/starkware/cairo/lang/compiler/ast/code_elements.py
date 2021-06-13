import dataclasses
from abc import abstractmethod
from typing import Any, Dict, List, Optional, Sequence

from starkware.cairo.lang.compiler.ast.aliased_identifier import AliasedIdentifier
from starkware.cairo.lang.compiler.ast.arguments import IdentifierList
from starkware.cairo.lang.compiler.ast.bool_expr import BoolExpr
from starkware.cairo.lang.compiler.ast.expr import ExprAssignment, Expression, ExprIdentifier
from starkware.cairo.lang.compiler.ast.formatting_utils import (
    INDENTATION, LocationField, ParticleFormattingConfig, create_particle_sublist,
    particles_in_lines)
from starkware.cairo.lang.compiler.ast.instructions import InstructionAst
from starkware.cairo.lang.compiler.ast.node import AstNode
from starkware.cairo.lang.compiler.ast.notes import NoteListField, Notes
from starkware.cairo.lang.compiler.ast.rvalue import Rvalue, RvalueCall, RvalueFuncCall
from starkware.cairo.lang.compiler.ast.types import TypedIdentifier
from starkware.cairo.lang.compiler.error_handling import Location
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.python.utils import indent


class CodeElement(AstNode):
    @abstractmethod
    def format(self, allowed_line_length):
        """
        Formats the code element, without exceeding a line length of `allowed_line_length`.
        """


@dataclasses.dataclass
class CodeElementInstruction(CodeElement):
    instruction: InstructionAst

    def get_particles(self):
        return [self.instruction.format()]

    def format(self, allowed_line_length):
        return self.instruction.format()

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.instruction]


@dataclasses.dataclass
class CodeElementConst(CodeElement):
    identifier: ExprIdentifier
    expr: Expression

    def format(self, allowed_line_length):
        return f'const {self.identifier.format()} = {self.expr.format()}'

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.identifier, self.expr]


@dataclasses.dataclass
class CodeElementMember(CodeElement):
    typed_identifier: TypedIdentifier

    def format(self, allowed_line_length):
        return f'member {self.typed_identifier.format()}'

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.typed_identifier]


@dataclasses.dataclass
class CodeElementReference(CodeElement):
    typed_identifier: TypedIdentifier
    expr: Expression

    def format(self, allowed_line_length):
        return f'let {self.typed_identifier.format()} = {self.expr.format()}'

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.typed_identifier, self.expr]


@dataclasses.dataclass
class CodeElementLocalVariable(CodeElement):
    """
    Represents a statement of the form:
      local x [: expr_type] = [expr]

    Both the expr_type and the initialization expr are optional.
    """
    typed_identifier: TypedIdentifier
    expr: Optional[Expression]
    location: Optional[Location] = LocationField

    def format(self, allowed_line_length):
        assignment = '' if self.expr is None else f' = {self.expr.format()}'
        return f'local {self.typed_identifier.format()}{assignment}'

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.typed_identifier, self.expr]


@dataclasses.dataclass
class CodeElementTemporaryVariable(CodeElement):
    """
    Represents a statement of the form:
      tempvar x = expr.
    """
    typed_identifier: TypedIdentifier
    expr: Expression
    location: Optional[Location] = LocationField

    def format(self, allowed_line_length):
        return f'tempvar {self.typed_identifier.format()} = {self.expr.format()}'

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.typed_identifier, self.expr]


@dataclasses.dataclass
class CodeElementCompoundAssertEq(CodeElement):
    """
    Represents the statement "assert a = b" for two (compound) expressions a, b.
    Unlike AssertEqInstruction, a CodeElementCompoundAssertEq may translate to a few instructions
    to deal with expressions which contain more than one operation.
    """
    a: Expression
    b: Expression
    location: Optional[Location] = LocationField

    def format(self, allowed_line_length):
        return f'assert {self.a.format()} = {self.b.format()}'

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.a, self.b]


@dataclasses.dataclass
class CodeElementStaticAssert(CodeElement):
    a: Expression
    b: Expression
    location: Optional[Location] = LocationField

    def format(self, allowed_line_length):
        return f'static_assert {self.a.format()} == {self.b.format()}'

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.a, self.b]


@dataclasses.dataclass
class CodeElementReturn(CodeElement):
    """
    Represents a statement of the form:
      return ([ident=]expr, ...).
    """
    exprs: List[ExprAssignment]
    location: Optional[Location] = LocationField

    def format(self, allowed_line_length):
        expr_codes = [x.format() for x in self.exprs]
        particles = ['return (', create_particle_sublist(expr_codes, ')')]

        return particles_in_lines(
            particles=particles,
            config=ParticleFormattingConfig(
                allowed_line_length=allowed_line_length,
                line_indent=INDENTATION,
                one_per_line=True))

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return self.exprs


@dataclasses.dataclass
class CodeElementTailCall(CodeElement):
    """
    Represents a statement of the form:
      return func_ident([ident=]expr, ...).
    """
    func_call: RvalueFuncCall
    location: Optional[Location] = LocationField

    def get_particles(self):
        particales = self.func_call.get_particles()
        return ['return ' + particales[0]] + particales[1:]

    def format(self, allowed_line_length):
        return particles_in_lines(
            particles=self.get_particles(),
            config=ParticleFormattingConfig(
                allowed_line_length=allowed_line_length,
                line_indent=INDENTATION,
                one_per_line=True))

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.func_call]


@dataclasses.dataclass
class CodeElementFuncCall(CodeElement):
    """
    Represents a statement of the form:
      func_ident([ident=]expr, ...).
    """
    func_call: RvalueFuncCall

    def get_particles(self):
        return self.func_call.get_particles()

    def format(self, allowed_line_length):
        return self.func_call.format(allowed_line_length)

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.func_call]


@dataclasses.dataclass
class CodeElementReturnValueReference(CodeElement):
    """
    Represents one of the references below.
      let x [: type] = func(...)
      let x [: type] = call func
      let x [: type] = call rel 5
    where:
      'x [: type]' is the 'typed_identifier'
      'func(...)' is the 'func_call'.
    """
    typed_identifier: TypedIdentifier
    func_call: RvalueCall

    def format(self, allowed_line_length):
        call_particles = self.func_call.get_particles()
        first_particle = f'let {self.typed_identifier.format()} = ' + call_particles[0]

        return particles_in_lines(
            particles=[first_particle] + call_particles[1:],
            config=ParticleFormattingConfig(
                allowed_line_length=allowed_line_length,
                line_indent=INDENTATION,
                one_per_line=True))

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.typed_identifier, self.func_call]


@dataclasses.dataclass
class CodeElementUnpackBinding(CodeElement):
    """
    Represents return value unpacking statement of the form:
      let (a, b, c) = func(...)
    where:
      '(a, b, c)' is the 'unpacking_list'
      'func(...)' is the 'rvalue'.
    """
    unpacking_list: IdentifierList
    rvalue: Rvalue

    def format(self, allowed_line_length):
        particles = self.rvalue.get_particles()

        end_particle = ') = ' + particles[0]
        particles = ['let ('] + \
            create_particle_sublist(self.unpacking_list.get_particles(), end_particle) + \
            particles[1:]

        return particles_in_lines(
            particles=particles,
            config=ParticleFormattingConfig(
                allowed_line_length=allowed_line_length,
                line_indent=INDENTATION,
                one_per_line=True))

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.unpacking_list, self.rvalue]


@dataclasses.dataclass
class CodeElementLabel(CodeElement):
    identifier: ExprIdentifier

    def format(self, allowed_line_length):
        return f'{self.identifier.format()}:'

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.identifier]


@dataclasses.dataclass
class CodeElementHint(CodeElement):
    hint_code: str
    # The number of new lines following the "%{" symbol.
    n_prefix_newlines: int
    location: Optional[Location] = LocationField

    def format(self, allowed_line_length):
        if self.hint_code == '':
            return '%{\n%}'
        if '\n' not in self.hint_code:
            # One liner.
            return f'%{{ {self.hint_code} %}}'
        code = indent(self.hint_code, INDENTATION)
        return f'%{{\n{code}\n%}}'

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return []


@dataclasses.dataclass
class CodeElementEmptyLine(CodeElement):
    def format(self, allowed_line_length):
        return ''

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return []


@dataclasses.dataclass
class CommentedCodeElement(AstNode):
    code_elm: CodeElement
    comment: Optional[str]

    def format(self, allowed_line_length):
        elm_str = self.code_elm.format(allowed_line_length=allowed_line_length)
        comment_str = f'#{self.comment}' if self.comment is not None else ''
        separator = '  ' if elm_str != '' and comment_str != '' else ''
        return elm_str + separator + comment_str.rstrip()

    def fix_comment_spaces(self, allow_additional_comment_spaces: bool):
        """
        Comments should start with exactly one space after '#' except for some cases (in which
        allow_additional_comment_spaces=True).
        Returns a copy of this instance with a fixed comment.
        """
        comment = self.comment

        if comment is None:
            return self

        if not allow_additional_comment_spaces:
            comment = comment.strip()
        if not comment.startswith(' '):
            comment = ' ' + comment

        return CommentedCodeElement(code_elm=self.code_elm, comment=comment)

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.code_elm]


@dataclasses.dataclass
class CodeBlock(AstNode):
    code_elements: List[CommentedCodeElement]

    def format(self, allowed_line_length):
        code_elements = remove_redundant_empty_lines(self.code_elements)
        code_elements = add_empty_lines_before_labels(code_elements)
        code_elements = fix_comment_spaces(code_elements)

        return ''.join(f'{code_elm.format(allowed_line_length)}\n' for code_elm in code_elements)

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return self.code_elements


@dataclasses.dataclass
class CodeElementScoped(CodeElement):
    """
    Represents a list of code elements that should be handled inside a scope.
    This class does not appear naturally in the parsed AST.
    """
    scope: ScopedName
    code_elements: List[CodeElement]

    def format(self, allowed_line_length):
        raise NotImplementedError(f'Formatting {type(self).__name__} is not supported.')

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return self.code_elements


@dataclasses.dataclass
class CodeElementFunction(CodeElement):
    """
    Represents either a 'func', 'namespace' or 'struct' statement.
    For example:
      func foo(x, y) -> (z, w):
          return (z=x, w=y)
      end
    """
    # The type of the code element. Either 'func', 'namespace' or 'struct'.
    element_type: str
    identifier: ExprIdentifier
    arguments: IdentifierList
    implicit_arguments: Optional[IdentifierList]
    returns: Optional[IdentifierList]
    code_block: CodeBlock
    decorators: List[ExprIdentifier]
    additional_attributes: Dict[str, Any] = dataclasses.field(default_factory=dict)

    ARGUMENT_SCOPE = ScopedName.from_string('Args')
    IMPLICIT_ARGUMENT_SCOPE = ScopedName.from_string('ImplicitArgs')
    RETURN_SCOPE = ScopedName.from_string('Return')

    @property
    def name(self):
        return self.identifier.name

    def format(self, allowed_line_length):
        code = self.code_block.format(allowed_line_length=allowed_line_length - INDENTATION)
        code = indent(code, INDENTATION)
        if self.element_type in ['struct', 'namespace']:
            particles = [f'{self.element_type} {self.name}:']
        else:
            if self.implicit_arguments is not None:
                first_particle_suffix = '{'
                implicit_args_particles = [
                    create_particle_sublist(self.implicit_arguments.get_particles(), '}(')]
            else:
                first_particle_suffix = '('
                implicit_args_particles = []

            if self.returns is not None:
                particles = [
                    f'{self.element_type} {self.name}{first_particle_suffix}',
                    *implicit_args_particles,
                    create_particle_sublist(self.arguments.get_particles(), ') -> ('),
                    create_particle_sublist(self.returns.get_particles(), '):')]
            else:
                particles = [
                    f'{self.element_type} {self.name}{first_particle_suffix}',
                    *implicit_args_particles,
                    create_particle_sublist(self.arguments.get_particles(), '):')]

        decorators = ''.join(f'@{decorator.format()}\n' for decorator in self.decorators)
        header = particles_in_lines(
            particles=particles,
            config=ParticleFormattingConfig(
                allowed_line_length=allowed_line_length,
                line_indent=INDENTATION * 2))
        return f'{decorators}{header}\n{code}end'

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [
            self.identifier, self.arguments, self.implicit_arguments, self.returns, self.code_block]


@dataclasses.dataclass
class CodeElementWith(CodeElement):
    identifiers: List[AliasedIdentifier]
    code_block: CodeBlock

    def format(self, allowed_line_length):
        identifier_list_str = ', '.join(identifier.format() for identifier in self.identifiers)
        inner_code = self.code_block.format(allowed_line_length=allowed_line_length - INDENTATION)
        inner_code = indent(inner_code, INDENTATION)
        return f'with {identifier_list_str}:\n{inner_code}end'

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [*self.identifiers, self.code_block]


@dataclasses.dataclass
class CodeElementIf(CodeElement):
    condition: BoolExpr
    main_code_block: CodeBlock
    else_code_block: Optional[CodeBlock]
    label_neq: Optional[str] = None
    label_end: Optional[str] = None
    location: Optional[Location] = LocationField

    def format(self, allowed_line_length):
        cond_particles = ['if ', *self.condition.get_particles()]
        cond_particles[-1] = cond_particles[-1] + ':'
        code = particles_in_lines(
            particles=cond_particles,
            config=ParticleFormattingConfig(
                allowed_line_length=allowed_line_length,
                line_indent=INDENTATION))
        main_code = self.main_code_block.format(
            allowed_line_length=allowed_line_length - INDENTATION)
        main_code = indent(main_code, INDENTATION)
        code += f'\n{main_code}'
        if self.else_code_block is not None:
            code += f'else:'
            else_code = self.else_code_block.format(
                allowed_line_length=allowed_line_length - INDENTATION)
            else_code = indent(else_code, INDENTATION)
            code += f'\n{else_code}'
        code += 'end'
        return code

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.condition, self.main_code_block, self.else_code_block]


class Directive(AstNode):
    @abstractmethod
    def format(self):
        pass


@dataclasses.dataclass
class BuiltinsDirective(Directive):
    builtins: List[str]
    location: Optional[Location] = LocationField

    def format(self):
        return f'%builtins {" ".join(self.builtins)}'

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return []


@dataclasses.dataclass
class LangDirective(Directive):
    name: str
    location: Optional[Location] = LocationField

    def format(self):
        return f'%lang {self.name}'

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return []


@dataclasses.dataclass
class CodeElementDirective(CodeElement):
    directive: Directive
    location: Optional[Location] = LocationField

    def format(self, allowed_line_length):
        return self.directive.format()

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.directive]


@dataclasses.dataclass
class CodeElementImport(CodeElement):
    path: ExprIdentifier
    import_items: List[AliasedIdentifier]
    notes: List[Notes] = NoteListField  # type: ignore
    location: Optional[Location] = LocationField

    def format(self, allowed_line_length):
        for note in self.notes:
            note.assert_no_comments()

        items = [item.format() for item in self.import_items]
        prefix = f'from {self.path.format()} import '
        one_liner = prefix + ', '.join(items)

        if len(one_liner) <= allowed_line_length:
            return one_liner

        particles = [f'{prefix}(', create_particle_sublist(items, ')')]
        return particles_in_lines(
            particles=particles,
            config=ParticleFormattingConfig(
                allowed_line_length=allowed_line_length,
                line_indent=INDENTATION,
                one_per_line=False))

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return [self.path, *self.import_items]


@dataclasses.dataclass
class CodeElementAllocLocals(CodeElement):
    """
    Represents a statement of the form "alloc_locals".
    """
    location: Optional[Location] = LocationField

    def format(self, allowed_line_length):
        return 'alloc_locals'

    def get_children(self) -> Sequence[Optional[AstNode]]:
        return []


def is_empty_line(code_element: CommentedCodeElement):
    return isinstance(code_element.code_elm, CodeElementEmptyLine) and code_element.comment is None


def is_comment_line(code_element: CommentedCodeElement):
    return isinstance(code_element.code_elm, CodeElementEmptyLine) and \
        code_element.comment is not None


def remove_redundant_empty_lines(
        code_elements: List[CommentedCodeElement]) -> List[CommentedCodeElement]:
    """
    Returns a new list of code elements where redundant empty lines are removed.
    Redundant empty lines are empty lines which are after:
    1. Empty lines.
    2. Labels.
    or at the end of the list.
    """
    new_code_elements = []
    skip_empty_lines = True
    for code_elm in code_elements:
        if is_empty_line(code_elm):
            # Empty line.
            if skip_empty_lines:
                continue
            skip_empty_lines = True
        elif isinstance(code_elm.code_elm, CodeElementLabel):
            skip_empty_lines = True
        else:
            skip_empty_lines = False
        new_code_elements.append(code_elm)

    while len(new_code_elements) > 0 and is_empty_line(new_code_elements[-1]):
        new_code_elements.pop()

    return new_code_elements


def add_empty_lines_before_labels(
        code_elements: List[CommentedCodeElement]) -> List[CommentedCodeElement]:
    """
    Makes sure there is an empty line before labels.
    The empty line is added before the comment lines preceding the label.
    """
    new_code_elements_reversed = []
    add_empty_line = False
    for code_elm in code_elements[::-1]:
        if add_empty_line:
            if is_empty_line(code_elm):
                add_empty_line = False
            elif not is_comment_line(code_elm):
                new_code_elements_reversed.append(CommentedCodeElement(
                    code_elm=CodeElementEmptyLine(),
                    comment=None))
                add_empty_line = False

        if isinstance(code_elm.code_elm, CodeElementLabel):
            add_empty_line = True

        new_code_elements_reversed.append(code_elm)

    return new_code_elements_reversed[::-1]


def fix_comment_spaces(code_elements: List[CommentedCodeElement]) -> List[CommentedCodeElement]:
    """
    Comments should start with exactly one space after '#'. When a comment is spread across several
    lines, the next lines may start with more than one space.
    Returns a copy of code_elements, where comment prefix spaces are fixed.
    """
    new_code_elements = []
    allow_additional_comment_spaces = False
    for code_elm in code_elements:
        # Additional spaces are never allowed in inline comments.
        if not is_comment_line(code_elm):
            allow_additional_comment_spaces = False

        new_code_elements.append(code_elm.fix_comment_spaces(allow_additional_comment_spaces))

        if is_comment_line(code_elm):
            # Next comment line may have additional spaces.
            allow_additional_comment_spaces = True
    return new_code_elements
